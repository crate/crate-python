
from .cursor import Cursor
from .exceptions import ProgrammingError
from .http import Client

class Connection(object):

    def __init__(self, servers, timeout=None, client_class=None):
        client_class = client_class and client_class or Client
        self.client = client_class(servers, timeout=timeout)
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


def connect(servers, timeout=None, client_class=None):
    return Connection(servers, timeout, client_class)
