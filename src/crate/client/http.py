# -*- coding: utf-8; -*-
#
# Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  Crate licenses
# this file to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
# However, if you have executed another commercial license agreement
# with Crate these terms will supersede the license and you may use the
# software solely pursuant to the terms of the relevant commercial agreement.


import logging
import os
import ssl
import threading
import typing as t
from urllib.parse import SplitResult, urlparse

import orjson
import urllib3
from urllib3 import connection_from_url
from urllib3.connection import HTTPConnection
from urllib3.exceptions import (
    HTTPError,
    MaxRetryError,
    ProtocolError,
    ProxyError,
    ReadTimeoutError,
    SSLError,
)
from urllib3.util.retry import Retry
from verlib2 import Version

from crate.client._codec import (  # noqa: F401
    epoch_aware,
    epoch_naive,
    json_dumps,
    json_encoder,
)
from crate.client._options import (  # noqa: F401
    _HTTP_PAT,
    SQL_PATH,
    credentials_from_url,
    keepalive_socket_options,
    server_url,
    sql_path,
    to_server_list,
    validate_compress,
)
from crate.client._pool import _ServerPool
from crate.client._request import (  # noqa: F401
    build_headers,
    compress_body,
    create_sql_payload,
    super_len,
)
from crate.client._response import (  # noqa: F401
    PRESERVE_ACTIVE_SERVER_EXCEPTIONS,
    SRV_UNAVAILABLE_STATUSES,
    blob_del_result,
    blob_exists_result,
    blob_put_result,
    parse_server_infos,
    raise_for_status,
    redirect_target,
    should_preserve_server,
)
from crate.client.exceptions import (
    ConnectionError,
    DigestNotFoundException,
    ProgrammingError,
)

logger = logging.getLogger(__name__)

# Private names that other code imports from this module.
_create_sql_payload = create_sql_payload
_server_url = server_url
_to_server_list = to_server_list
pat = _HTTP_PAT

SSL_ONLY_ARGS = {"ca_certs", "cert_reqs", "cert_file", "key_file"}


class Server:
    def __init__(self, server, **pool_kw):
        socket_options = _get_socket_opts(
            pool_kw.pop("socket_keepalive", False),
            pool_kw.pop("socket_tcp_keepidle", None),
            pool_kw.pop("socket_tcp_keepintvl", None),
            pool_kw.pop("socket_tcp_keepcnt", None),
        )
        self.path_prefix = ""
        try:
            parsed_url = urlparse(server)
        except Exception as e:
            parsed_url = SplitResult("", "", "", "", "")
            logger.warning(
                "Unable to extract path prefix from server url: {ex}".format(
                    ex=e
                )
            )
        if parsed_url.path:
            self.path_prefix = parsed_url.path.strip("/")
        self.pool = connection_from_url(
            server,
            socket_options=socket_options,
            **pool_kw,
        )

    def request(
        self,
        method,
        path,
        data=None,
        stream=False,
        headers=None,
        username=None,
        password=None,
        schema=None,
        backoff_factor=0,
        jwt_token=None,
        **kwargs,
    ):
        """Send a request

        Always set the Content-Length and the Content-Type header.
        """
        if self.path_prefix:
            path = "/{path_prefix}/{path}".format(
                path_prefix=self.path_prefix, path=path.strip("/")
            )
        headers = build_headers(
            headers,
            data,
            username=username,
            password=password,
            schema=schema,
            jwt_token=jwt_token,
        )
        kwargs["assert_same_host"] = False
        kwargs["redirect"] = False
        kwargs["retries"] = Retry(read=0, backoff_factor=backoff_factor)
        return self.pool.urlopen(
            method,
            path,
            body=data,
            preload_content=not stream,
            headers=headers,
            **kwargs,
        )

    def close(self):
        self.pool.close()


def _json_from_response(response):
    try:
        return orjson.loads(response.data)
    except ValueError as ex:
        raise ProgrammingError(
            "Invalid server response of content-type '{}':\n{}".format(
                response.headers.get("content-type", "unknown"),
                response.data.decode("utf-8"),
            )
        ) from ex


def _blob_path(table, digest):
    return "/_blobs/{table}/{digest}".format(table=table, digest=digest)


def _ex_to_message(ex):
    return getattr(ex, "message", None) or str(ex) or repr(ex)


def _raise_for_status(response):
    # Read the body of error responses only, so that a successful streamed
    # response is not loaded into memory.
    if 400 <= response.status < 600:
        raise_for_status(
            response.status, response.reason, response.headers, response.data
        )


def _pool_kw_args(
    verify_ssl_cert,
    ca_cert,
    client_cert,
    client_key,
    timeout=None,
    pool_size=None,
):
    ca_cert = ca_cert or os.environ.get("REQUESTS_CA_BUNDLE", None)
    if ca_cert and not os.path.exists(ca_cert):
        # Sanity check
        raise IOError('CA bundle file "{}" does not exist.'.format(ca_cert))

    kw = {
        "ca_certs": ca_cert,
        "cert_reqs": ssl.CERT_REQUIRED if verify_ssl_cert else ssl.CERT_NONE,
        "cert_file": client_cert,
        "key_file": client_key,
    }
    if timeout is not None:
        if isinstance(timeout, str):
            timeout = float(timeout)
        kw["timeout"] = timeout
    if pool_size is not None:
        kw["maxsize"] = int(pool_size)
    return kw


def _remove_certs_for_non_https(server: str, kwargs: dict) -> dict:
    """
    Removes certificates for http requests.
    """
    if server.lower().startswith("https"):
        return kwargs
    used_ssl_args = SSL_ONLY_ARGS & set(kwargs.keys())
    if used_ssl_args:
        kwargs = kwargs.copy()
        for arg in used_ssl_args:
            kwargs.pop(arg)
    return kwargs


def _update_pool_kwargs_for_ssl_minimum_version(server, kwargs):
    """
    On urllib3 v2, re-add support for TLS 1.0 and TLS 1.1.

    https://urllib3.readthedocs.io/en/latest/v2-migration-guide.html#https-requires-tls-1-2
    """
    if Version(urllib3.__version__) >= Version("2"):
        from urllib3.util import parse_url

        scheme, _, host, port, *_ = parse_url(server)
        if scheme == "https":
            kwargs["ssl_minimum_version"] = ssl.TLSVersion.MINIMUM_SUPPORTED


def _get_socket_opts(
    keepalive=True, tcp_keepidle=None, tcp_keepintvl=None, tcp_keepcnt=None
):
    """
    Return an optional list of socket options for urllib3's HTTPConnection
    constructor.
    """
    if not keepalive:
        return None

    # additionally use urllib3's default socket options
    return list(HTTPConnection.default_socket_options) + (
        keepalive_socket_options(
            keepalive, tcp_keepidle, tcp_keepintvl, tcp_keepcnt
        )
    )


class Client(_ServerPool):
    """
    Crate connection client using CrateDB's HTTP API.
    """

    SQL_PATH = SQL_PATH
    """Crate URI path for issuing SQL statements."""

    default_server = "http://127.0.0.1:4200"
    """Default server to use if no servers are given on instantiation."""

    _logger = logger

    def __init__(
        self,
        servers=None,
        timeout=None,
        backoff_factor=0,
        verify_ssl_cert=True,
        ca_cert=None,
        error_trace=False,
        cert_file=None,
        key_file=None,
        ssl_relax_minimum_version=False,
        username=None,
        password=None,
        schema=None,
        pool_size=None,
        socket_keepalive=True,
        socket_tcp_keepidle=None,
        socket_tcp_keepintvl=None,
        socket_tcp_keepcnt=None,
        jwt_token=None,
        compress: t.Union[int, bool] = 8192,
    ):
        if not servers:
            servers = [self.default_server]
        else:
            servers = to_server_list(servers)

        # Try to derive credentials from first server argument if not
        # explicitly given.
        if servers and not username:
            try:
                username, password = credentials_from_url(
                    servers[0], username, password
                )
            except Exception as ex:
                logger.warning(
                    "Unable to decode credentials from database "
                    "URI, so connecting to CrateDB without "
                    "authentication: {ex}".format(ex=ex)
                )

        super().__init__(servers)
        pool_kw = _pool_kw_args(
            verify_ssl_cert,
            ca_cert,
            cert_file,
            key_file,
            timeout,
            pool_size,
        )
        pool_kw.update(
            {
                "socket_keepalive": socket_keepalive,
                "socket_tcp_keepidle": socket_tcp_keepidle,
                "socket_tcp_keepintvl": socket_tcp_keepintvl,
                "socket_tcp_keepcnt": socket_tcp_keepcnt,
            }
        )
        self.ssl_relax_minimum_version = ssl_relax_minimum_version
        self.backoff_factor = backoff_factor
        self.server_pool: t.Dict[str, Server] = {}
        self._update_server_pool(servers, **pool_kw)
        self._pool_kw = pool_kw
        self._local = threading.local()
        self.username = username
        self.password = password
        self.jwt_token = jwt_token
        self.schema = schema

        self.compress = validate_compress(compress)

        self.path = sql_path(error_trace, self.SQL_PATH)

    def close(self):
        for server in self.server_pool.values():
            server.close()

    def _create_server(self, server, **pool_kw):
        kwargs = _remove_certs_for_non_https(server, pool_kw)
        # After updating to urllib3 v2, optionally retain support
        # for TLS 1.0 and TLS 1.1, in order to support connectivity
        # to older versions of CrateDB.
        if self.ssl_relax_minimum_version:
            _update_pool_kwargs_for_ssl_minimum_version(server, kwargs)
        self.server_pool[server] = Server(server, **kwargs)

    def _update_server_pool(self, servers, **pool_kw):
        for server in servers:
            self._create_server(server, **pool_kw)

    def sql(self, stmt, parameters=None, bulk_parameters=None):
        """
        Execute SQL stmt against the crate server.
        """
        if stmt is None:
            return None

        data = create_sql_payload(stmt, parameters, bulk_parameters)
        logger.debug("Sending request to %s with payload: %s", self.path, data)
        content = self._json_request("POST", self.path, data=data)
        logger.debug("JSON response for stmt(%s): %s", stmt, content)

        return content

    def server_infos(self, server):
        response = self._request("GET", "/", server=server)
        _raise_for_status(response)
        return parse_server_infos(server, _json_from_response(response))

    def blob_put(self, table, digest, data) -> bool:
        """
        Stores the contents of the file like @data object in a blob under the
        given table and digest.
        """
        response = self._request("PUT", _blob_path(table, digest), data=data)
        return blob_put_result(
            response.status,
            response.reason,
            response.headers,
            response.data,
            table,
            digest,
        )

    def blob_del(self, table, digest) -> bool:
        """
        Deletes the blob with given digest under the given table.
        """
        response = self._request("DELETE", _blob_path(table, digest))
        return blob_del_result(
            response.status, response.reason, response.headers, response.data
        )

    def blob_get(self, table, digest, chunk_size=1024 * 128):
        """
        Returns a file like object representing the contents of the blob
        with the given digest.
        """
        response = self._request("GET", _blob_path(table, digest), stream=True)
        if response.status == 404:
            raise DigestNotFoundException(table, digest)
        _raise_for_status(response)
        return response.stream(amt=chunk_size)

    def blob_exists(self, table, digest) -> bool:
        """
        Returns true if the blob with the given digest exists
        under the given table.
        """
        response = self._request("HEAD", _blob_path(table, digest))
        return blob_exists_result(
            response.status, response.reason, response.headers, response.data
        )

    def _add_server(self, server):
        with self._lock:
            if server not in self.server_pool:
                self._create_server(server, **self._pool_kw)

    def _request(self, method, path, server=None, **kwargs):
        """Execute a request to the cluster

        A server is selected from the server pool.
        """
        while True:
            next_server = server or self._get_server()
            try:
                response = self.server_pool[next_server].request(
                    method,
                    path,
                    username=self.username,
                    password=self.password,
                    backoff_factor=self.backoff_factor,
                    schema=self.schema,
                    jwt_token=self.jwt_token,
                    **kwargs,
                )
                redirect_server = redirect_target(
                    response.status, response.get_redirect_location()
                )
                if redirect_server is not None:
                    self._add_server(redirect_server)
                    return self._request(
                        method, path, server=redirect_server, **kwargs
                    )
                if not server and response.status in SRV_UNAVAILABLE_STATUSES:
                    with self._lock:
                        # drop server from active ones
                        self._drop_server(next_server, response.reason)
                else:
                    return response
            except (
                MaxRetryError,
                ReadTimeoutError,
                SSLError,
                HTTPError,
                ProxyError,
            ) as ex:
                ex_message = _ex_to_message(ex)
                if server:
                    raise ConnectionError(
                        "Server not available, exception: %s" % ex_message
                    ) from ex
                preserve_server = False
                if isinstance(ex, ProtocolError):
                    preserve_server = should_preserve_server(ex)
                if not preserve_server:
                    with self._lock:
                        # drop server from active ones
                        self._drop_server(next_server, ex_message)
            except Exception as e:
                raise ProgrammingError(_ex_to_message(e)) from e

    def _json_request(self, method, path, data):
        """
        Issue request against the crate HTTP API.
        """
        headers = {"Accept-Encoding": "gzip, deflate"}

        data, compressed = compress_body(data, self.compress)
        if compressed:
            headers["Content-Encoding"] = "gzip"

        response = self._request(method, path, data=data, headers=headers)
        _raise_for_status(response)
        if len(response.data) > 0:
            return _json_from_response(response)
        return response.data

    def __repr__(self):
        return "<Client {0}>".format(str(self._active_servers))
