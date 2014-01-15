from .cursor import Cursor
from .exceptions import ProgrammingError
from .http import Client
from .blob import BlobContainer


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
            raise ProgrammingError("Connection closed")

    def close(self):
        """
        Close the connection now
        """
        self._closed = True

    def commit(self):
        """
        Transactions are not supported, so ``commit`` is not implemented.
        """
        if self._closed:
            raise ProgrammingError("Connection closed")

    def get_blob_container(self, container_name):
        """ Retrieve a BlobContainer for `container_name`

        :param container_name: the name of the BLOB container.
        :returns: a :class:ContainerObject
        """
        return BlobContainer(container_name, self)

    def __repr__(self):
        return '<Connection {0}>'.format(repr(self.client))


def connect(servers=None, timeout=None, client=None):
    """ Create a :class:Connection object

    :param servers:
        either a string in the form of '<hostname>:<port>'
        or a list of servers in the form of ['<hostname>:<port>', '...']
    :param timeout:
        (optional)
        define the retry timeout for unreachable servers in seconds
    :param client:
        (optional - for testing)
        client used to communicate with crate.

    >>> connect(['host1:4200', 'host2:4200'])
    <Connection <Client ['http://host1:4200', 'http://host2:4200']>>
    """
    return Connection(servers=servers, timeout=timeout, client=client)
