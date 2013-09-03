# -*- encoding: utf-8 -*-

from .exceptions import ProgrammingError


class Cursor():

    def __init__(self, connection):
        self.arraysize = 1
        self.connection = connection
        self._closed = True

    def execute(self, sql):
        self._result = self.connection.client.sql(sql)
        self.rows = iter(self._result["rows"])
        self._closed = False

    def executemany(self, sql):
        raise NotImplementedError

    def fetchone(self):
        return self.next()

    def next(self):
        try:
            return self._next()
        except StopIteration:
            return None

    def fetchmany(self, count=None):
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
        result = []
        iterate = True
        while iterate:
            try:
                result.append(self._next())
            except StopIteration:
                iterate = False
        return result

    def close(self):
        self._closed = True
        self._result = None

    def commit(self):
        """
        Transactions are not supported, so 'commit' is not implemented yet.
        """
        pass

    def setinputsizes(self, sizes):
        """
        'setinputsizes' is not supported.
        """
        pass

    def setoutputsize(self, size, column=None):
        """
        'setoutputsize' is not supported.
        """
        pass

    @property
    def rowcount(self):
        if not self._closed:
            return len(self._result["rows"])
        return -1

    def _next(self):
        if not self._closed:
            return self.rows.next()
        else:
            raise ProgrammingError

    @property
    def description(self):
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
