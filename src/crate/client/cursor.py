# -*- coding: utf-8; -*-
#
# Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  Crate licenses
# this file to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
# However, if you have executed another commercial license agreement
# with Crate these terms will supersede the license and you may use the
# software solely pursuant to the terms of the relevant commercial agreement.

from .exceptions import ProgrammingError


class Cursor(object):
    """
    not thread-safe by intention
    should not be shared between different threads
    """
    lastrowid = None  # currently not supported

    def __init__(self, connection):
        self.arraysize = 1
        self.connection = connection
        self._closed = False
        self._result = None

    def execute(self, sql, parameters=None):
        """
        Prepare and execute a database operation (query or command).
        """
        if self.connection._closed:
            raise ProgrammingError("Connection closed")

        if self._closed:
            raise ProgrammingError("Cursor closed")

        self._result = self.connection.client.sql(sql, parameters)
        if "rows" in self._result:
            self.rows = iter(self._result["rows"])

    def executemany(self, sql, seq_of_parameters):
        """
        Prepare a database operation (query or command) and then execute it against all parameter
        sequences or mappings found in the sequence ``seq_of_parameters``.
        """
        row_counts = []
        durations = []
        for params in seq_of_parameters:
            self.execute(sql, parameters=params)
            if self.rowcount > -1:
                row_counts.append(self.rowcount)
            if self.duration > -1:
                durations.append(self.duration)
        self._result = {
            "rowcount": sum(row_counts) if row_counts else -1,
            "duration": sum(durations) if durations else -1,
            "rows": []
        }
        self.rows = iter(self._result["rows"])

    def fetchone(self):
        """
        Fetch the next row of a query result set, returning a single sequence, or None when no
        more data is available.
        Alias for ``next()``.
        """
        return self.next()

    def next(self):
        """
        Fetch the next row of a query result set, returning a single sequence, or None when no
        more data is available.
        """
        try:
            return self._next()
        except StopIteration:
            return None

    def fetchmany(self, count=None):
        """
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
        Close the cursor now
        """
        self._closed = True
        self._result = None

    def setinputsizes(self, sizes):
        """
        Not supported method.
        """
        pass

    def setoutputsize(self, size, column=None):
        """
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
        return self._result.get("rowcount", -1)

    def _next(self):
        """
        Return the next row of a query result set, respecting if cursor was closed.
        """
        if not self._closed:
            return next(self.rows)
        else:
            raise ProgrammingError("Cursor closed")

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

    @property
    def duration(self):
        """
        This read-only attribute specifies the server-side duration of a query in milliseconds.
        """
        if (
                    self._closed
                or not self._result
            or "duration" not in self._result
        ):
            return -1
        return self._result.get("duration", 0)
