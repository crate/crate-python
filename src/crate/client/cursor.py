# -*- encoding: utf-8 -*-
from functools import wraps

from .exceptions import ProgrammingError

def check_connection(f):
    """
    Method decorator for checking if the ``Connection`` was closed.
    If so raise a ``ProgrammingError``.
    """
    @wraps(f)
    def wrapper(*args):
        cursor = args[0]
        # special case for __init__
        if not hasattr(cursor, 'connection'):
            if args[1]._closed:
                raise ProgrammingError
        elif cursor.connection._closed:
            raise ProgrammingError
        return f(*args)
    return wrapper

def for_all_methods(decorator, exclude=()):
    """
    Class decorator for applying a method decorator to all method except those
    passed by ``exclude`` argument.
    """
    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)) and attr not in exclude:
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls
    return decorate

@for_all_methods(check_connection)
class Cursor(object):

    def __init__(self, connection):
        self.arraysize = 1
        self.connection = connection
        self._closed = True
        self._result = None

    def execute(self, sql):
        """
        execute(self, sql)

        Prepare and execute a database operation (query or command).
        """
        self._result = self.connection.client.sql(sql)
        if "rows" in self._result:
            self.rows = iter(self._result["rows"])
            self._closed = False

    def executemany(self, sql, seq_of_parameters):
        """
        executemany(self, sql, seq_of_parameters)

        Prepare a database operation (query or command) and then execute it against all parameter
        sequences or mappings found in the sequence ``seq_of_parameters``.
        """
        # TODO: implement ``executemany()``
        raise NotImplementedError

    def fetchone(self):
        """
        fetchone(self)

        Fetch the next row of a query result set, returning a single sequence, or None when no
        more data is available.
        Alias for ``next()``.
        """
        return self.next()

    def next(self):
        """
        next(self)

        Fetch the next row of a query result set, returning a single sequence, or None when no
        more data is available.
        """
        try:
            return self._next()
        except StopIteration:
            return None

    def fetchmany(self, count=None):
        """
        fetchmany(self, count=None)

        Fetch the next set of rows of a query result, returning a sequence of sequences
        (e.g. a list of tuples). An empty sequence is returned when no more rows are available.
        """
        if count is None:
            count = self.arraysize
        if count == 0:
            return self.fetchall()
        result = []
        for i in range(count):
            try:
                result.append(self._next())
            except StopIteration:
                pass
        return result

    def fetchall(self):
        """
        fetchall(self)

        Fetch all (remaining) rows of a query result, returning them as a sequence of sequences
        (e.g. a list of tuples). Note that the cursor's arraysize attribute can affect the
        performance of this operation.
        """
        result = []
        iterate = True
        while iterate:
            try:
                result.append(self._next())
            except StopIteration:
                iterate = False
        return result

    def close(self):
        """
        close(self)

        Close the cursor now
        """
        self._closed = True
        self._result = None

    def setinputsizes(self, sizes):
        """
        setinputsizes(self, sizes)

        Not supported method.
        """
        pass

    def setoutputsize(self, size, column=None):
        """
        setoutputsize(self, size, column=None)

        Not supported method.
        """
        pass

    @property
    def rowcount(self):
        """
        This read-only attribute specifies the number of rows that the last .execute*() produced
        (for DQL statements like ``SELECT``) or affected (for DML statements like ``UPDATE``
        or ``INSERT``).
        """
        if (
            self._closed
            or not self._result
            or "rows" not in self._result
        ):
            return -1
        return len(self._result["rows"])

    def _next(self):
        """
        Return the next row of a query result set, respecting if cursor was closed.
        """
        if not self._closed:
            return self.rows.next()
        else:
            raise ProgrammingError

    @property
    def description(self):
        """
        This read-only attribute is a sequence of 7-item sequences.
        """
        if self._closed:
            return

        description = []
        for col in self._result["cols"]:
            description.append((col,
                                None,
                                None,
                                None,
                                None,
                                None,
                                None))
        return tuple(description)



