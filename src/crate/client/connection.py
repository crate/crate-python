
from .cursor import Cursor


class Connection(object):

    def __init__(self, servers, client):
        self.client = client

    def cursor(self):
        return Cursor(self)

    def close(self):
        pass

    def commit(self):
        pass

    def _connect(self, hosts):
        pass

    def _endpoint(self):
        pass


def connect(servers=None, crate_client=None):
    return Connection(servers, crate_client)

