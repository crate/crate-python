from datetime import datetime
import json
import requests
import logging
import types

log = logging.getLogger(__name__)

class Client(object):
    """
    Crate connection client using crate's HTTP API.
    """

    sql_path = '_sql'

    def __init__(self, servers):
        if isinstance(servers, types.StringTypes):
            servers = [servers]
        self.servers = servers

    def sql(self, stmt):
        """
        Execute SQL stmt against the crate server.

        :param stmt: str or unicode
        :returns: dict
        """
        if stmt is None:
            return None

        if not isinstance(stmt, types.StringTypes):
            raise ValueError("stmt is not a string type")

        content = self._request('POST', self.sql_path, dict(stmt=stmt))

        log.debug("JSON response for stmt(%s): %s", stmt, content)

        return content

    def _request(self, method, path, data):
        """
        Issue request against the crate HTTP API.

        :param method: HTTP method to use
        :param path: URI path
        :param data: HTTP body payload
        :returns: dict
        """
        for idx, server in enumerate(self.servers):
            try:
                # build uri and send http request
                uri = "http://{server}/{path}".format(server=server, path=path)
                response = requests.request(method, uri, data=json.dumps(data))
            except requests.RequestException, exc:
                # if this is the last server raise exception, otherwise try next
                # TODO: discuss this behaviour
                if idx == len(self.servers)-1:
                    raise exc
            else:
                break

        # round-robin the server list
        self._roundrobin()

        # raise error if occurred, otherwise nothing is raised
        response.raise_for_status()

        # return parsed json response
        return response.json(cls=DateTimeDecoder)


    def _roundrobin(self):
        """
        Very simple round-robin implementation
        """
        self.servers.insert(len(self.servers), self.servers.pop(0))


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