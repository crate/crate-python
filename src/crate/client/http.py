import json
import logging
import requests
import sys
from datetime import datetime
from operator import itemgetter

from crate.client.exceptions import ConnectionError

logger = logging.getLogger(__name__)

if sys.version_info[0] > 2:
    basestring = str


class Client(object):
    """
    Crate connection client using crate's HTTP API.
    """

    sql_path = '_sql'
    """Crate URI path for issuing SQL statements."""

    retry_interval = 30
    """Retry interval for failed servers in seconds."""

    default_server = "127.0.0.1:9200"
    """Default server to use if no servers are given on instantiation."""

    def __init__(self, servers=None, timeout=None):
        if not servers:
            servers = self.default_server
        if isinstance(servers, basestring):
            servers = [servers]
        self._active_servers = servers
        self._http_timeout = timeout
        self._inactive_servers = []

    def sql(self, stmt):
        """
        Execute SQL stmt against the crate server.
        """
        if stmt is None:
            return None

        if not isinstance(stmt, basestring):
            raise ValueError("stmt is not a string type")

        content = self._request('POST', self.sql_path, dict(stmt=stmt))

        logger.debug("JSON response for stmt(%s): %s", stmt, content)

        return content

    def _request(self, method, path, data=None):
        """
        Issue request against the crate HTTP API.
        """

        while True:
            server = self._get_server()
            try:
                # build uri and send http request
                uri = "http://{server}/{path}".format(server=server, path=path)
                if data:
                    data = json.dumps(data)
                response = requests.request(method, uri, data=data,
                                            timeout=self._http_timeout)
            except (requests.ConnectionError, requests.Timeout,
                    requests.TooManyRedirects) as ex:
                # drop server from active ones
                ex_message = hasattr(ex, 'message') and ex.message or str(ex)
                self._drop_server(server, ex_message)
                # if this is the last server raise exception, otherwise try next
                if not self._active_servers:
                    raise ConnectionError(
                        ("No more Servers available, "
                         "exception from last server: %s") % ex_message)
            else:
                # raise error if occurred, otherwise nothing is raised
                response.raise_for_status()

                # return parsed json response
                return response.json(cls=DateTimeDecoder)


    def _get_server(self):
        """
        Get server to use for request.
        Also process inactive server list, re-add them after given interval.
        """
        if self._inactive_servers:
            sorted_inactive_servers = sorted(self._inactive_servers, key=itemgetter('timestamp'))

            # first, check for failed servers older than ``interval``
            for server_data in sorted_inactive_servers:
                delta = datetime.now() - server_data.get('timestamp')
                if delta.seconds >= self.retry_interval:
                    self._active_servers.append(server_data.get('server'))
                    logger.info("Restored server %s into active pool", server_data.get('server'))

            # if no one is old enough, use oldest
            if not self._active_servers:
                server_to_add = sorted_inactive_servers.pop(0).get('server')
                self._active_servers.append(server_to_add)
                logger.info("Restored server %s into active pool", server_to_add)

        server = self._active_servers[0]
        self._roundrobin()

        return server

    def _drop_server(self, server, message):
        """
        Drop server from active list and adds it to the inactive ones.
        """
        try:
            self._active_servers.remove(server)
        except ValueError:
            pass
        else:
            self._inactive_servers.append({
                    'server': server,
                    'message': message,
                    'timestamp': datetime.now()
                })
            logger.warning("Removed server %s from active pool", server)

    def _roundrobin(self):
        """
        Very simple round-robin implementation
        """
        self._active_servers.append(self._active_servers.pop(0))



class DateTimeDecoder(json.JSONDecoder):
    """
    JSON decoder which is trying to convert datetime strings to datetime objects

    taken from: https://gist.github.com/abhinav-upadhyay/5300137
    """

    def __init__(self, *args, **kargs):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object,
                             *args, **kargs)

    def dict_to_object(self, d):
        if '__type__' not in d:
            return d

        type = d.pop('__type__')
        try:
            dateobj = datetime(**d)
            return dateobj
        except:
            d['__type__'] = type
