
from .cursor import Cursor
from .exceptions import ProgrammingError


class Connection(object):

    def __init__(self, servers, client):
        self.client = client
        self._closed = False
        self._cursor = Cursor(self)

    def cursor(self):
        if not self._closed:
            return self._cursor
        else:
            raise ProgrammingError

    def close(self):
        self._cursor.close()
        self._closed = True

    def commit(self):
        """
        Transactions are not supported, so ``commit`` is not implemented.
        """
        if not self._closed:
            pass
        else:
            raise ProgrammingError


def connect(servers=None, client=None):
    return Connection(servers, client)
