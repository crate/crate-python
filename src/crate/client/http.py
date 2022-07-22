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


import calendar
import heapq
import io
import json
import logging
import os
import re
import socket
import ssl
import threading
from urllib.parse import urlparse
from base64 import b64encode
from time import time
from datetime import datetime, date
from decimal import Decimal
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
from crate.client.exceptions import (
    ConnectionError,
    BlobLocationNotFoundException,
    DigestNotFoundException,
    ProgrammingError,
)


logger = logging.getLogger(__name__)


_HTTP_PAT = pat = re.compile('https?://.+', re.I)
SRV_UNAVAILABLE_STATUSES = set((502, 503, 504, 509))
PRESERVE_ACTIVE_SERVER_EXCEPTIONS = set((ConnectionResetError, BrokenPipeError))
SSL_ONLY_ARGS = set(('ca_certs', 'cert_reqs', 'cert_file', 'key_file'))


def super_len(o):
    if hasattr(o, '__len__'):
        return len(o)
    if hasattr(o, 'len'):
        return o.len
    if hasattr(o, 'fileno'):
        try:
            fileno = o.fileno()
        except io.UnsupportedOperation:
            pass
        else:
            return os.fstat(fileno).st_size
    if hasattr(o, 'getvalue'):
        # e.g. BytesIO, cStringIO.StringI
        return len(o.getvalue())


class CrateJsonEncoder(json.JSONEncoder):

    epoch = datetime(1970, 1, 1)

    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime):
            delta = o - self.epoch
            return int(delta.microseconds / 1000.0 +
                       (delta.seconds + delta.days * 24 * 3600) * 1000.0)
        if isinstance(o, date):
            return calendar.timegm(o.timetuple()) * 1000
        return json.JSONEncoder.default(self, o)


class Server(object):

    def __init__(self, server, **pool_kw):
        socket_options = _get_socket_opts(
            pool_kw.pop('socket_keepalive', False),
            pool_kw.pop('socket_tcp_keepidle', None),
            pool_kw.pop('socket_tcp_keepintvl', None),
            pool_kw.pop('socket_tcp_keepcnt', None),
        )
        self.pool = connection_from_url(
            server,
            socket_options=socket_options,
            **pool_kw,
        )

    def request(self,
                method,
                path,
                data=None,
                stream=False,
                headers=None,
                username=None,
                password=None,
                schema=None,
                backoff_factor=0,
                **kwargs):
        """Send a request

        Always set the Content-Length and the Content-Type header.
        """
        if headers is None:
            headers = {}
        if 'Content-Length' not in headers:
            length = super_len(data)
            if length is not None:
                headers['Content-Length'] = length

        # Authentication credentials
        if username is not None:
            if 'Authorization' not in headers and username is not None:
                credentials = username + ':'
                if password is not None:
                    credentials += password
                headers['Authorization'] = 'Basic %s' % b64encode(credentials.encode('utf-8')).decode('utf-8')
            # For backwards compatibility with Crate <= 2.2
            if 'X-User' not in headers:
                headers['X-User'] = username

        if schema is not None:
            headers['Default-Schema'] = schema
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'
        kwargs['assert_same_host'] = False
        kwargs['redirect'] = False
        kwargs['retries'] = Retry(read=0, backoff_factor=backoff_factor)
        return self.pool.urlopen(
            method,
            path,
            body=data,
            preload_content=not stream,
            headers=headers,
            **kwargs
        )

    def close(self):
        self.pool.close()


def _json_from_response(response):
    try:
        return json.loads(response.data.decode('utf-8'))
    except ValueError:
        raise ProgrammingError(
            "Invalid server response of content-type '{}':\n{}"
            .format(response.headers.get("content-type", "unknown"), response.data.decode('utf-8')))


def _blob_path(table, digest):
    return '/_blobs/{table}/{digest}'.format(table=table, digest=digest)


def _ex_to_message(ex):
    return getattr(ex, 'message', None) or str(ex) or repr(ex)


def _raise_for_status(response):
    """ make sure that only crate.exceptions are raised that are defined in
    the DB-API specification """
    message = ''
    if 400 <= response.status < 500:
        message = '%s Client Error: %s' % (response.status, response.reason)
    elif 500 <= response.status < 600:
        message = '%s Server Error: %s' % (response.status, response.reason)
    else:
        return
    if response.status == 503:
        raise ConnectionError(message)
    if response.headers.get("content-type", "").startswith("application/json"):
        data = json.loads(response.data.decode('utf-8'))
        error = data.get('error', {})
        error_trace = data.get('error_trace', None)
        if "results" in data:
            errors = [res["error_message"] for res in data["results"]
                      if res.get("error_message")]
            if errors:
                raise ProgrammingError("\n".join(errors))
        if isinstance(error, dict):
            raise ProgrammingError(error.get('message', ''),
                                   error_trace=error_trace)
        raise ProgrammingError(error, error_trace=error_trace)
    raise ProgrammingError(message)


def _server_url(server):
    """
    Normalizes a given server string to an url

    >>> print(_server_url('a'))
    http://a
    >>> print(_server_url('a:9345'))
    http://a:9345
    >>> print(_server_url('https://a:9345'))
    https://a:9345
    >>> print(_server_url('https://a'))
    https://a
    >>> print(_server_url('demo.crate.io'))
    http://demo.crate.io
    """
    if not _HTTP_PAT.match(server):
        server = 'http://%s' % server
    parsed = urlparse(server)
    url = '%s://%s' % (parsed.scheme, parsed.netloc)
    return url


def _to_server_list(servers):
    if isinstance(servers, str):
        servers = servers.split()
    return [_server_url(s) for s in servers]


def _pool_kw_args(verify_ssl_cert, ca_cert, client_cert, client_key,
                  timeout=None, pool_size=None):
    ca_cert = ca_cert or os.environ.get('REQUESTS_CA_BUNDLE', None)
    if ca_cert and not os.path.exists(ca_cert):
        # Sanity check
        raise IOError('CA bundle file "{}" does not exist.'.format(ca_cert))

    kw = {
        'ca_certs': ca_cert,
        'cert_reqs': ssl.CERT_REQUIRED if verify_ssl_cert else ssl.CERT_NONE,
        'cert_file': client_cert,
        'key_file': client_key,
        'timeout': timeout,
    }
    if pool_size is not None:
        kw['maxsize'] = pool_size
    return kw


def _remove_certs_for_non_https(server, kwargs):
    if server.lower().startswith('https'):
        return kwargs
    used_ssl_args = SSL_ONLY_ARGS & set(kwargs.keys())
    if used_ssl_args:
        kwargs = kwargs.copy()
        for arg in used_ssl_args:
            kwargs.pop(arg)
    return kwargs


def _create_sql_payload(stmt, args, bulk_args):
    if not isinstance(stmt, str):
        raise ValueError('stmt is not a string')
    if args and bulk_args:
        raise ValueError('Cannot provide both: args and bulk_args')

    data = {
        'stmt': stmt
    }
    if args:
        data['args'] = args
    if bulk_args:
        data['bulk_args'] = bulk_args
    return json.dumps(data, cls=CrateJsonEncoder)


def _get_socket_opts(keepalive=True,
                     tcp_keepidle=None,
                     tcp_keepintvl=None,
                     tcp_keepcnt=None):
    """
    Return an optional list of socket options for urllib3's HTTPConnection
    constructor.
    """
    if not keepalive:
        return None

    # always use TCP keepalive
    opts = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]

    # hasattr check because some of the options depend on system capabilities
    # see https://docs.python.org/3/library/socket.html#socket.SOMAXCONN
    if hasattr(socket, 'TCP_KEEPIDLE') and tcp_keepidle is not None:
        opts.append((socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, tcp_keepidle))
    if hasattr(socket, 'TCP_KEEPINTVL') and tcp_keepintvl is not None:
        opts.append((socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, tcp_keepintvl))
    if hasattr(socket, 'TCP_KEEPCNT') and tcp_keepcnt is not None:
        opts.append((socket.IPPROTO_TCP, socket.TCP_KEEPCNT, tcp_keepcnt))

    # additionally use urllib3's default socket options
    return HTTPConnection.default_socket_options + opts


class Client(object):
    """
    Crate connection client using CrateDB's HTTP API.
    """

    SQL_PATH = '/_sql?types=true'
    """Crate URI path for issuing SQL statements."""

    retry_interval = 30
    """Retry interval for failed servers in seconds."""

    default_server = "http://127.0.0.1:4200"
    """Default server to use if no servers are given on instantiation."""

    def __init__(self,
                 servers=None,
                 timeout=None,
                 backoff_factor=0,
                 verify_ssl_cert=True,
                 ca_cert=None,
                 error_trace=False,
                 cert_file=None,
                 key_file=None,
                 username=None,
                 password=None,
                 schema=None,
                 pool_size=None,
                 socket_keepalive=True,
                 socket_tcp_keepidle=None,
                 socket_tcp_keepintvl=None,
                 socket_tcp_keepcnt=None,
                 ):
        if not servers:
            servers = [self.default_server]
        else:
            servers = _to_server_list(servers)

        # Try to derive credentials from first server argument if not
        # explicitly given.
        if servers and not username:
            try:
                url = urlparse(servers[0])
                if url.username is not None:
                    username = url.username
                if url.password is not None:
                    password = url.password
            except Exception as ex:
                logger.warning("Unable to decode credentials from database "
                               "URI, so connecting to CrateDB without "
                               "authentication: {ex}"
                               .format(ex=ex))

        self._active_servers = servers
        self._inactive_servers = []
        pool_kw = _pool_kw_args(
            verify_ssl_cert, ca_cert, cert_file, key_file, timeout, pool_size,
        )
        pool_kw.update({
            'socket_keepalive': socket_keepalive,
            'socket_tcp_keepidle': socket_tcp_keepidle,
            'socket_tcp_keepintvl': socket_tcp_keepintvl,
            'socket_tcp_keepcnt': socket_tcp_keepcnt,
        })
        self.backoff_factor = backoff_factor
        self.server_pool = {}
        self._update_server_pool(servers, **pool_kw)
        self._pool_kw = pool_kw
        self._lock = threading.RLock()
        self._local = threading.local()
        self.username = username
        self.password = password
        self.schema = schema

        self.path = self.SQL_PATH
        if error_trace:
            self.path += '&error_trace=true'

    def close(self):
        for server in self.server_pool.values():
            server.close()

    def _create_server(self, server, **pool_kw):
        kwargs = _remove_certs_for_non_https(server, pool_kw)
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

        data = _create_sql_payload(stmt, parameters, bulk_parameters)
        logger.debug(
            'Sending request to %s with payload: %s', self.path, data)
        content = self._json_request('POST', self.path, data=data)
        logger.debug("JSON response for stmt(%s): %s", stmt, content)

        return content

    def server_infos(self, server):
        response = self._request('GET', '/', server=server)
        _raise_for_status(response)
        content = _json_from_response(response)
        node_name = content.get("name")
        node_version = content.get('version', {}).get('number', '0.0.0')
        return server, node_name, node_version

    def blob_put(self, table, digest, data):
        """
        Stores the contents of the file like @data object in a blob under the
        given table and digest.
        """
        response = self._request('PUT', _blob_path(table, digest),
                                 data=data)
        if response.status == 201:
            # blob created
            return True
        if response.status == 409:
            # blob exists
            return False
        if response.status in (400, 404):
            raise BlobLocationNotFoundException(table, digest)
        _raise_for_status(response)

    def blob_del(self, table, digest):
        """
        Deletes the blob with given digest under the given table.
        """
        response = self._request('DELETE', _blob_path(table, digest))
        if response.status == 204:
            return True
        if response.status == 404:
            return False
        _raise_for_status(response)

    def blob_get(self, table, digest, chunk_size=1024 * 128):
        """
        Returns a file like object representing the contents of the blob
        with the given digest.
        """
        response = self._request('GET', _blob_path(table, digest), stream=True)
        if response.status == 404:
            raise DigestNotFoundException(table, digest)
        _raise_for_status(response)
        return response.stream(amt=chunk_size)

    def blob_exists(self, table, digest):
        """
        Returns true if the blob with the given digest exists
        under the given table.
        """
        response = self._request('HEAD', _blob_path(table, digest))
        if response.status == 200:
            return True
        elif response.status == 404:
            return False
        _raise_for_status(response)

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
                    **kwargs
                )
                redirect_location = response.get_redirect_location()
                if redirect_location and 300 <= response.status <= 308:
                    redirect_server = _server_url(redirect_location)
                    self._add_server(redirect_server)
                    return self._request(
                        method, path, server=redirect_server, **kwargs)
                if not server and response.status in SRV_UNAVAILABLE_STATUSES:
                    with self._lock:
                        # drop server from active ones
                        self._drop_server(next_server, response.reason)
                else:
                    return response
            except (MaxRetryError,
                    ReadTimeoutError,
                    SSLError,
                    HTTPError,
                    ProxyError,) as ex:
                ex_message = _ex_to_message(ex)
                if server:
                    raise ConnectionError(
                        "Server not available, exception: %s" % ex_message
                    )
                preserve_server = False
                if isinstance(ex, ProtocolError):
                    preserve_server = any(
                        t in [type(arg) for arg in ex.args]
                        for t in PRESERVE_ACTIVE_SERVER_EXCEPTIONS
                    )
                if (not preserve_server):
                    with self._lock:
                        # drop server from active ones
                        self._drop_server(next_server, ex_message)
            except Exception as e:
                raise ProgrammingError(_ex_to_message(e))

    def _json_request(self, method, path, data):
        """
        Issue request against the crate HTTP API.
        """

        response = self._request(method, path, data=data)
        _raise_for_status(response)
        if len(response.data) > 0:
            return _json_from_response(response)
        return response.data

    def _get_server(self):
        """
        Get server to use for request.
        Also process inactive server list, re-add them after given interval.
        """
        with self._lock:
            inactive_server_count = len(self._inactive_servers)
            for i in range(inactive_server_count):
                try:
                    ts, server, message = heapq.heappop(self._inactive_servers)
                except IndexError:
                    pass
                else:
                    if (ts + self.retry_interval) > time():
                        # Not yet, put it back
                        heapq.heappush(self._inactive_servers,
                                       (ts, server, message))
                    else:
                        self._active_servers.append(server)
                        logger.warning("Restored server %s into active pool",
                                       server)

            # if none is old enough, use oldest
            if not self._active_servers:
                ts, server, message = heapq.heappop(self._inactive_servers)
                self._active_servers.append(server)
                logger.info("Restored server %s into active pool", server)

            server = self._active_servers[0]
            self._roundrobin()

            return server

    @property
    def active_servers(self):
        """get the active servers for this client"""
        with self._lock:
            return list(self._active_servers)

    def _drop_server(self, server, message):
        """
        Drop server from active list and adds it to the inactive ones.
        """
        try:
            self._active_servers.remove(server)
        except ValueError:
            pass
        else:
            heapq.heappush(self._inactive_servers, (time(), server, message))
            logger.warning("Removed server %s from active pool", server)

        # if this is the last server raise exception, otherwise try next
        if not self._active_servers:
            raise ConnectionError(
                ("No more Servers available, "
                 "exception from last server: %s") % message)

    def _roundrobin(self):
        """
        Very simple round-robin implementation
        """
        self._active_servers.append(self._active_servers.pop(0))

    def __repr__(self):
        return '<Client {0}>'.format(str(self._active_servers))
