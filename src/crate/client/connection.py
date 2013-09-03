
from .cursor import Cursor
from .exceptions import ProgrammingError
from .http import Client

class Connection(object):

    _client_impl = Client

    def __init__(self, servers, timeout):
        self.client = self._client_impl(servers, timeout=timeout)
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


def connect(servers, timeout=None):
    return Connection(servers, timeout)
