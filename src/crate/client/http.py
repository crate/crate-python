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


import json
import logging
import os
import io
import sys
import six
import urllib3
import urllib3.exceptions
import time
import functools
from datetime import datetime, date
import calendar
import threading
import re
from six.moves.urllib.parse import urlparse
from crate.client.exceptions import (
    Error,
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


class CrateJsonEncoder(json.JSONEncoder):

    epoch = datetime(1970, 1, 1)

    def default(self, o):
        if isinstance(o, datetime):
            delta = o - self.epoch
            return int(delta.microseconds / 1000.0 +
                       (delta.seconds + delta.days * 24 * 3600) * 1000.0)
        if isinstance(o, date):
            return calendar.timegm(o.timetuple()) * 1000
        return json.JSONEncoder.default(self, o)


def _db_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Error as e:
            raise
        except Exception as e:
            raise ProgrammingError(_ex_to_message(e))
    return wrapper


def _remove_certs_for_non_https(server, kwargs):
    if server.lower().startswith('https'):
        return kwargs
    if 'ca_certs' in kwargs or 'cert_regs' in kwargs:
        kwargs = kwargs.copy()
        kwargs.pop('ca_certs', None)
        kwargs.pop('cert_reqs', None)
    return kwargs


class Server(object):
    RETRY_INTERVAL = 30

    def __init__(self, server, **kwargs):
        kwargs = _remove_certs_for_non_https(server, kwargs)
        self.pool = urllib3.connection_from_url(server, **kwargs)
        self.server = server
        self.inactive = 0

    def is_inactive(self, ts):
        return self.inactive > 0 and self.inactive + self.RETRY_INTERVAL > ts

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
        headers = headers or {}
        if 'Content-Length' not in headers:
            length = super_len(data)
            if length is not None:
                headers['Content-Length'] = length
        headers['Accept'] = 'application/json'
        kwargs['redirect'] = False
        return self.pool.urlopen(
            method,
            path,
            body=data,
            preload_content=not stream,
            headers=headers,
            **kwargs
        )


class RoundRobin(object):
    def __init__(self, hosts):
        self.hosts = hosts
        self.idx = 0

    def __iter__(self):
        idx = self.idx
        hosts = self.hosts
        hosts = hosts[idx:len(hosts)] + hosts[:idx]
        self.idx = idx + 1 if idx + 1 < len(hosts) else 0
        return iter(hosts)


class ServerPool(object):
    SRV_UNAVAILABLE_STATUSES = set((502, 503, 504, 509))
    SRV_UNAVAILABLE_EXCEPTIONS = (
        urllib3.exceptions.MaxRetryError,
        urllib3.exceptions.ReadTimeoutError,
        urllib3.exceptions.SSLError,
        urllib3.exceptions.HTTPError,
        urllib3.exceptions.ProxyError,)

    def __init__(self, servers, pool_kw):
        self.servers = servers = [Server(s, **pool_kw) for s in servers]
        self._rr = RoundRobin(servers)
        self.servers_dict = {s.server: s for s in servers}

    def __iter__(self):
        return iter(self._rr)

    def __getitem__(self, value):
        return self.servers_dict[value]

    @_db_errors
    def _execute_redirect(self, resp, method, path, data, stream, headers, **kw):
        redirect_location = resp.get_redirect_location()
        server = Server(_server_url(redirect_location))
        return server.request(method, path, data, stream, headers, kw)

    @_db_errors
    def execute(self, method, path, data=None, stream=False, headers=None, **kw):
        now = time.time()
        servers = [s for s in self._rr if not s.is_inactive(now)]
        if not servers:
            # retry all if none are active
            servers = sorted(self.servers, key=lambda x: x.inactive)
        last_ex = None
        for server in servers:
            try:
                resp = server.request(method, path, data, stream, headers, **kw)
                if 300 <= resp.status <= 308:
                    return self._execute_redirect(
                        resp, method, path, data, stream, headers, **kw)
                if resp.status in self.SRV_UNAVAILABLE_STATUSES:
                    last_ex = resp.reason
                else:
                    server.inactive = 0
                    return resp
            except self.SRV_UNAVAILABLE_EXCEPTIONS as e:
                last_ex = _ex_to_message(e)

            server.inactive = time.time()
        msg = 'No more Servers available'
        if last_ex:
            msg += ', exception from last server: ' + last_ex
        raise ConnectionError(msg)


def _json_loads_or_error(response):
    try:
        return json.loads(six.text_type(response.data, 'utf-8'))
    except ValueError:
        raise ProgrammingError(
            "Invalid server response of content-type '%s'" %
            response.headers.get("content-type", "unknown"))


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
        data = json.loads(six.text_type(response.data, 'utf-8'))
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
    if isinstance(servers, basestring):
        servers = servers.split()
    return [_server_url(s) for s in servers]


def _pool_kw_args(ca_cert, verify_ssl_cert):
    ca_cert = ca_cert or os.environ.get('REQUESTS_CA_BUNDLE', None)
    if not ca_cert:
        return {}
    return {
        'ca_certs': ca_cert,
        'cert_reqs': 'REQUIRED' if verify_ssl_cert else 'NONE'
    }


def _create_sql_payload(stmt, args, bulk_args):
    if not isinstance(stmt, basestring):
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


class Client(object):
    """
    Crate connection client using crate's HTTP API.
    """

    SQL_PATH = '/_sql'
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
            servers = _to_server_list(servers)
        pool_kw = _pool_kw_args(ca_cert, verify_ssl_cert)
        self.pool = ServerPool(servers, pool_kw)
        self._lock = threading.RLock()

        self.path = self.SQL_PATH
        if error_trace:
            self.path += '?error_trace=1'

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
        try:
            response = self.pool[server].request('GET', '/')
        except ServerPool.SRV_UNAVAILABLE_EXCEPTIONS as e:
            raise ConnectionError(_ex_to_message(e))
        _raise_for_status(response)
        content = _json_loads_or_error(response)
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
        if response.status == 400:
            raise BlobsDisabledException(table, digest)
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

    def _request(self, method, path, **kwargs):
        """Execute a request to the cluster

        A server is selected from the server pool.
        """

        resp = self.pool.execute(method, path, **kwargs)
        return resp

    def _json_request(self, method, path, data):
        """
        Issue request against the crate HTTP API.
        """
        response = self._request(method, path, data=data)
        _raise_for_status(response)
        if len(response.data) > 0:
            return _json_loads_or_error(response)
        return response.data

    @property
    def active_servers(self):
        """get the active servers for this client"""
        now = time.time()
        with self._lock:
            return [s.server for s in self.pool if not s.is_inactive(now)]

    @property
    def inactive_servers(self):
        """get the active servers for this client"""
        now = time.time()
        with self._lock:
            return [s.server for s in self.pool if s.is_inactive(now)]

    def __repr__(self):
        return '<Client {0}>'.format(str(self.active_servers))
