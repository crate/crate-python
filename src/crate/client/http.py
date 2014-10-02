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


import heapq
import json
import logging
import os
import io
import sys
import six
import urllib3
import urllib3.exceptions
from time import time
import threading
import re
from six.moves.urllib.parse import urlparse, urlencode
from crate.client.exceptions import (
    ConnectionError,
    DigestNotFoundException,
    ProgrammingError,
    BlobsDisabledException,
)


logger = logging.getLogger(__name__)

if sys.version_info[0] > 2:
    basestring = str

_HTTP_PAT = pat = re.compile('https?://.+', re.I)
SRV_UNAVAILABLE_STATUSES = set((502, 503, 504, 509))


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


class Server(object):

    def __init__(self, server, **kwargs):
        self.pool = urllib3.connection_from_url(server, **kwargs)

    def request(self,
                method,
                path,
                data=None,
                stream=False,
                headers=None,
                **kwargs):
        """Send a request

        Always set the Content-Length header.
        """
        if headers is None:
            headers = {}
        if not 'Content-Length' in headers:
            length = super_len(data)
            if length is not None:
                headers['Content-Length'] = length
        headers['Accept'] = 'application/json'
        kwargs['assert_same_host'] = False
        kwargs['redirect'] = False
        return self.pool.urlopen(
            method,
            path,
            body=data,
            preload_content=not stream,
            headers=headers,
            **kwargs
        )


class Client(object):
    """
    Crate connection client using crate's HTTP API.
    """

    SQL_PATH = '_sql'
    """Crate URI path for issuing SQL statements."""

    retry_interval = 30
    """Retry interval for failed servers in seconds."""

    default_server = "http://127.0.0.1:4200"
    """Default server to use if no servers are given on instantiation."""

    def __init__(self, servers=None, timeout=None, ca_cert=None,
                 verify_ssl_cert=False, error_trace=False):
        if not servers:
            servers = [self.default_server]
        else:
            if isinstance(servers, basestring):
                servers = servers.split()
            servers = [self._server_url(s) for s in servers]
        self._active_servers = servers
        self._inactive_servers = []
        self._http_timeout = timeout
        pool_kw = {}
        if ca_cert is None:
            ca_cert = os.environ.get("REQUESTS_CA_BUNDLE", None)
        if ca_cert is not None:
            pool_kw['ca_certs'] = ca_cert
            pool_kw['cert_reqs'] = verify_ssl_cert and 'REQUIRED' or 'NONE'
        self.server_pool = {}
        self._update_server_pool(servers,
                                 timeout=timeout,
                                 **pool_kw
                                )
        self._pool_kw = pool_kw
        self._lock = threading.RLock()
        self._local = threading.local()

        url_params = {}
        if error_trace:
            url_params["error_trace"] = 1
        self.path = self._get_sql_path(**url_params)

    def _get_sql_path(self, **url_params):
        """
        create the HTTP path to send SQL Requests to
        """
        if url_params:
            return "{0}?{1}".format(self.SQL_PATH, urlencode(url_params))
        else:
            return self.SQL_PATH

    def _update_server_pool(self, servers, **kwargs):
        for server in servers:
            if not server in self.server_pool:
                self.server_pool[server] = Server(server, **kwargs)

    @staticmethod
    def _server_url(server):
        """
        Normalizes a given server string to an url

        >>> print(Client._server_url('a'))
        http://a
        >>> print(Client._server_url('a:9345'))
        http://a:9345
        >>> print(Client._server_url('https://a:9345'))
        https://a:9345
        >>> print(Client._server_url('https://a'))
        https://a
        >>> print(Client._server_url('demo.crate.io'))
        http://demo.crate.io
        """
        if not _HTTP_PAT.match(server):
            server = 'http://%s' % server
        parsed = urlparse(server)
        url = '%s://%s' % (parsed.scheme, parsed.netloc)
        return url

    def sql(self, stmt, parameters=None, bulk_parameters=None):
        """
        Execute SQL stmt against the crate server.
        """
        if stmt is None:
            return None

        if not isinstance(stmt, basestring):
            raise ValueError("stmt is not a string type")

        data = {
            'stmt': stmt
        }
        if parameters:
            data['args'] = parameters
        if bulk_parameters:
            data['bulk_args'] = bulk_parameters
        logger.debug(
            'Sending request to %s with payload: %s', self.path, data)
        content = self._json_request('POST', self.path, data=data)
        logger.debug("JSON response for stmt(%s): %s", stmt, content)

        return content

    def server_infos(self, server):
        response = self._request('GET', '', server=server)
        self._raise_for_status(response)
        try:
            content = json.loads(six.text_type(response.data, 'utf-8'))
        except ValueError:
            raise ProgrammingError(
                "Invalid server response of content-type '%s'" %
                response.headers.get("content-type", "unknown"))
        node_name = content.get("name")
        return server, node_name, content.get('version', {}).get('number', '0.0.0')

    def _blob_path(self, table, digest):
        return '_blobs/{table}/{digest}'.format(table=table, digest=digest)

    def blob_put(self, table, digest, data):
        """
        Stores the contents of the file like @data object in a blob under the
        given table and digest.
        """
        response = self._request('PUT', self._blob_path(table, digest), data=data)
        if response.status == 201:
            # blob created
            return True
        if response.status == 409:
            # blob exists
            return False
        if response.status == 400:
            raise BlobsDisabledException(table, digest)
        self._raise_for_status(response)

    def blob_del(self, table, digest):
        """
        Deletes the blob with given digest under the given table.
        """
        response = self._request('DELETE', self._blob_path(table, digest))
        if response.status == 204:
            return True
        if response.status == 404:
            return False
        self._raise_for_status(response)

    def blob_get(self, table, digest, chunk_size=1024 * 128):
        """
        Returns a file like object representing the contents of the blob with the given
        digest.
        """
        response = self._request('GET', self._blob_path(table, digest), stream=True)
        if response.status == 404:
            raise DigestNotFoundException(table, digest)
        self._raise_for_status(response)
        return response.stream(amt=chunk_size)

    def blob_exists(self, table, digest):
        """
        Returns true if the blob with the given digest exists under the given table.
        """
        response = self._request('HEAD', self._blob_path(table, digest))
        if response.status == 200:
            return True
        elif response.status == 404:
            return False
        self._raise_for_status(response)

    def _add_server(self, server):
        with self._lock:
            if server not in self.server_pool:
                self.server_pool[server] = Server(server, **self._pool_kw)

    def _request(self, method, path, server=None, **kwargs):
        """Execute a request to the cluster

        A server is selected from the server pool.
        """
        while True:
            next_server = server or self._get_server()
            try:
                response = self._do_request(next_server, method, path, **kwargs)
                redirect_location = response.get_redirect_location()
                if redirect_location and 300 <= response.status <= 308:
                    redirect_server = self._server_url(redirect_location)
                    self._add_server(redirect_server)
                    return self._request(
                        method, path, server=redirect_server, **kwargs)
                if not server and response.status in SRV_UNAVAILABLE_STATUSES:
                    with self._lock:
                        # drop server from active ones
                        self._drop_server(next_server, response.reason)
                else:
                    return response
            except (urllib3.exceptions.MaxRetryError,
                    urllib3.exceptions.ReadTimeoutError,
                    urllib3.exceptions.SSLError,
                    urllib3.exceptions.HTTPError,
                    urllib3.exceptions.ProxyError,
                   ) as ex:
                ex_message = hasattr(ex, 'message') and ex.message or str(ex)
                if server:
                    raise ConnectionError(
                        "Server not available, exception: %s" % ex_message
                    )
                with self._lock:
                    # drop server from active ones
                    self._drop_server(next_server, ex_message)
            except Exception as e:
                ex_message = hasattr(e, 'message') and e.message or str(e)
                raise ProgrammingError(ex_message)

    def _do_request(self, server, method, path, **kwargs):
        """do the actual request to a chosen server"""
        if not path.startswith('/'):
            path = '/' + path
        return self.server_pool[server].request(
                    method,
                    path,
                    **kwargs)

    def _raise_for_status(self, response):
        """ make sure that only crate.exceptions are raised that are defined in
        the DB-API specification """
        http_error_msg = ''
        if 400 <= response.status < 500:
            http_error_msg = '%s Client Error: %s' % (
                                response.status, response.reason)
        elif 500 <= response.status < 600:
            http_error_msg = '%s Server Error: %s' % (
                                response.status, response.reason)
        else:
            return
        if response.status == 503:
            raise ConnectionError(http_error_msg)
        if response.headers.get("content-type", ""
                                ).startswith("application/json"):
            data = json.loads(six.text_type(response.data, 'utf-8'))
            error = data.get('error', {})
            error_trace = data.get('error_trace', None)
            if "results" in data:
                errors = [res["error_message"] for res in data["results"] if res.get("error_message")]
                if errors:
                    raise ProgrammingError("\n".join(errors))
            if isinstance(error, dict):
                raise ProgrammingError(error.get('message', ''), error_trace=error_trace)
            raise ProgrammingError(error, error_trace=error_trace)
        raise ProgrammingError(http_error_msg)

    def _json_request(self, method, path, data=None):
        """
        Issue request against the crate HTTP API.
        """

        if data:
            data = json.dumps(data)
        response = self._request(method, path, data=data)

        # raise error if occurred, otherwise nothing is raised
        self._raise_for_status(response)
        # return parsed json response
        if len(response.data) > 0:
            try:
                return json.loads(six.text_type(response.data, 'utf-8'))
            except ValueError:
                raise ProgrammingError(
                    "Invalid server response of content-type '%s'" %
                    response.headers.get("content-type", ""))
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
                    if (ts + self.retry_interval) > time():  # Not yet, put it back
                        heapq.heappush(self._inactive_servers, (ts, server, message))
                    else:
                        self._active_servers.append(server)
                        logger.warn("Restored server %s into active pool", server)

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
