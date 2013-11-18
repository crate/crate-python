
from .compat import StandardError


class Error(StandardError):

    def __init__(self, msg=None):
        # for py33 compat.
        # The Exception base class doesn't set the message attribute
        if msg:
            self.message = msg
        super(Error, self).__init__(msg)


class Warning(StandardError):
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class InternalError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class DataError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass


# exceptions not in db api

class ConnectionError(OperationalError):
    pass


class BlobException(Exception):
    def __init__(self, table, digest):
        self.table = table
        self.digest = digest

    def __str__(self):
        return "{table}/{digest}".format(table=self.table, digest=self.digest)


class DigestNotFoundException(BlobException):
    pass

class BlobsDisabledException(BlobException):
    pass

class TimezoneUnawareException(Error):
    pass
