
from .cursor import Cursor
from .exceptions import ProgrammingError
from .http import Client

class Connection(object):

    def __init__(self, servers=None, timeout=None, client=None):
        if client:
            self.client = client
        else:
            self.client = Client(servers, timeout=timeout)
        self._closed = False

    def cursor(self):
        """
        Return a new Cursor Object using the connection.
        """
        if not self._closed:
            return Cursor(self)
        else:
            raise ProgrammingError

    def close(self):
        """
        Close the connection now
        """
        self._closed = True

    def commit(self):
        """
        Transactions are not supported, so ``commit`` is not implemented.
        """
        if not self._closed:
            pass
        else:
            raise ProgrammingError


def connect(servers=None, timeout=None, client=None):
    return Connection(servers=servers, timeout=timeout, client=client)
