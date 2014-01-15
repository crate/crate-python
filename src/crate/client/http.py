from _socket import gaierror
import heapq
import json
import logging
import sys
from time import time
import threading
from six.moves.urllib.parse import urlparse
import requests
import re
from crate.client.exceptions import (
    ConnectionError, DigestNotFoundException, ProgrammingError, BlobsDisabledException)


logger = logging.getLogger(__name__)

if sys.version_info[0] > 2:
    basestring = str

_HTTP_PAT=pat = re.compile('https?://.+',re.I)

class Client(object):
    """
    Crate connection client using crate's HTTP API.
    """

    sql_path = '_sql'
    """Crate URI path for issuing SQL statements."""

    retry_interval = 30
    """Retry interval for failed servers in seconds."""

    default_server = "http://127.0.0.1:4200"
    """Default server to use if no servers are given on instantiation."""

    def __init__(self, servers=None, timeout=None):
        if not servers:
            servers = [self.default_server]
        else:
            if isinstance(servers, basestring):
                servers = servers.split()
            servers = [self._server_url(s) for s in servers]
        self._active_servers = servers
        self._http_timeout = timeout
        self._inactive_servers = []
        self._lock = threading.RLock()
        self._local = threading.local()
        self._session = requests.session()

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


    def sql(self, stmt, parameters=None):
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
        logger.debug(
            'Sending request to %s with payload: %s', self.sql_path, data)
        content = self._json_request('POST', self.sql_path, data=data)
        logger.debug("JSON response for stmt(%s): %s", stmt, content)

        return content

    def server_infos(self, server):
        try:
            response = self._do_request(server, 'GET', '/')
            content = response.json()
        except requests.ConnectionError as e:
            if isinstance(e.args[0].reason, gaierror):
                raise ConnectionError("Hostname could no be resolved.")
            else:
                raise ConnectionError(e.args[0].reason.strerror)
        node_name = content.get("name")
        return server, node_name

    def _blob_path(self, table, digest=None):
        path = table + '/_blobs/'
        if digest:
            path += digest
        return path

    def blob_put(self, table, digest, data):
        """
        Stores the contents of the file like @data object in a blob under the
        given table and digest.
        """
        response = self._request('PUT', self._blob_path(table, digest), data=data)
        if response.status_code == 201:
            return True
        elif response.status_code == 409:
            return False
        elif response.status_code == 400:
            raise BlobsDisabledException(table, digest)
        self._raise_for_status(response)

    def blob_del(self, table, digest):
        """
        Deletes the blob with given digest under the given table.
        """
        response = self._request('DELETE', self._blob_path(table, digest))
        if response.status_code == 204:
            return True
        elif response.status_code == 404:
            return False
        self._raise_for_status(response)

    def blob_get(self, table, digest, chunk_size=1024 * 128):
        """
        Returns a file like object representing the contents of the blob with the given
        digest.
        """
        response = self._request('GET', self._blob_path(table, digest), stream=True)

        if response.status_code == 404:
            raise DigestNotFoundException(table, digest)
        self._raise_for_status(response)
        return response.iter_content(chunk_size=chunk_size)

    def blob_exists(self, table, digest):
        """
        Returns true if the blob with the given digest exists under the given table.
        """
        response = self._request('HEAD', self._blob_path(table, digest))
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        self._raise_for_status(response)

    def _request(self, method, path, **kwargs):
        server = getattr(self._local, "server", None)
        while True:
            if not server:
                self._local.server = server = self._get_server()
            try:
                response = self._do_request(server, method, path, **kwargs)
                # reset local server, so next request will use new one
                self._local.server = server = None
                return response
            except (requests.ConnectionError, requests.Timeout,
                    requests.TooManyRedirects) as ex:
                # drop server from active ones
                ex_message = hasattr(ex, 'message') and ex.message or str(ex)
                self._drop_server(server, ex_message)
                self._local.server = server = None
                # if this is the last server raise exception, otherwise try next
                if not self._active_servers:
                    raise ConnectionError(
                        ("No more Servers available, "
                         "exception from last server: %s") % ex_message)
            except requests.HTTPError as e:
                if hasattr(e, 'response') and e.response:
                    raise ProgrammingError(e.response.content)
                raise ProgrammingError()

    def _do_request(self, url, method, path, **kwargs):
        """do the actual request to a chosen server"""
        uri = "{url}/{path}".format(url=url, path=path)
        return self._session.request(method, uri, timeout=self._http_timeout, **kwargs)

    def _raise_for_status(self, response):
        """ make sure that only crate.exceptions are raised that are defined in
        the DB-API specification """

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response'):
                raise ProgrammingError(
                    e.response.json().get('error', {}).get('message', ''))
            raise ProgrammingError(str(e))

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
        if len(response.content) > 0:
            return response.json()
        return response.content

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
        with self._lock:
            try:
                self._active_servers.remove(server)
            except ValueError:
                pass
            else:
                heapq.heappush(self._inactive_servers, (time(), server,
                                                        message))
                logger.warning("Removed server %s from active pool", server)

    def _roundrobin(self):
        """
        Very simple round-robin implementation
        """
        self._active_servers.append(self._active_servers.pop(0))

    def __repr__(self):
        return '<Client {0}>'.format(str(self._active_servers))
