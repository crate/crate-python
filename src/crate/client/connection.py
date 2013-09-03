
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


def connect(servers=None, client=None):
    return Connection(servers, client)
