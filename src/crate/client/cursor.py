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
from datetime import datetime, timedelta, timezone

from .converter import DataType
import warnings
import typing as t

from .converter import Converter
from .exceptions import ProgrammingError


class Cursor(object):
    """
    not thread-safe by intention
    should not be shared between different threads
    """
    lastrowid = None  # currently not supported

    def __init__(self, connection, converter: Converter, **kwargs):
        self.arraysize = 1
        self.connection = connection
        self._converter = converter
        self._closed = False
        self._result = None
        self.rows = None
        self._time_zone = None
        self.time_zone = kwargs.get("time_zone")

    def execute(self, sql, parameters=None, bulk_parameters=None):
        """
        Prepare and execute a database operation (query or command).
        """
        if self.connection._closed:
            raise ProgrammingError("Connection closed")

        if self._closed:
            raise ProgrammingError("Cursor closed")

        self._result = self.connection.client.sql(sql, parameters,
                                                  bulk_parameters)
        if "rows" in self._result:
            if self._converter is None:
                self.rows = iter(self._result["rows"])
            else:
                self.rows = iter(self._convert_rows())

    def executemany(self, sql, seq_of_parameters):
        """
        Prepare a database operation (query or command) and then execute it
        against all parameter sequences or mappings found in the sequence
        ``seq_of_parameters``.
        """
        row_counts = []
        durations = []
        self.execute(sql, bulk_parameters=seq_of_parameters)

        for result in self._result.get('results', []):
            if result.get('rowcount') > -1:
                row_counts.append(result.get('rowcount'))
        if self.duration > -1:
            durations.append(self.duration)

        self._result = {
            "rowcount": sum(row_counts) if row_counts else -1,
            "duration": sum(durations) if durations else -1,
            "rows": [],
            "cols": self._result.get("cols", []),
            "col_types": self._result.get("col_types", []),
            "results": self._result.get("results")
        }
        if self._converter is None:
            self.rows = iter(self._result["rows"])
        else:
            self.rows = iter(self._convert_rows())
        return self._result["results"]

    def fetchone(self):
        """
        Fetch the next row of a query result set, returning a single sequence,
        or None when no more data is available.
        Alias for ``next()``.
        """
        try:
            return self.next()
        except StopIteration:
            return None

    def __iter__(self):
        """
        support iterator interface:
        http://legacy.python.org/dev/peps/pep-0249/#iter

        This iterator is shared. Advancing this iterator will advance other
        iterators created from this cursor.
        """
        warnings.warn("DB-API extension cursor.__iter__() used")
        return self

    def fetchmany(self, count=None):
        """
        Fetch the next set of rows of a query result, returning a sequence of
        sequences (e.g. a list of tuples). An empty sequence is returned when
        no more rows are available.
        """
        if count is None:
            count = self.arraysize
        if count == 0:
            return self.fetchall()
        result = []
        for i in range(count):
            try:
                result.append(self.next())
            except StopIteration:
                pass
        return result

    def fetchall(self):
        """
        Fetch all (remaining) rows of a query result, returning them as a
        sequence of sequences (e.g. a list of tuples). Note that the cursor's
        arraysize attribute can affect the performance of this operation.
        """
        result = []
        iterate = True
        while iterate:
            try:
                result.append(self.next())
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
        This read-only attribute specifies the number of rows that the last
        .execute*() produced (for DQL statements like ``SELECT``) or affected
        (for DML statements like ``UPDATE`` or ``INSERT``).
        """
        if (self._closed or not self._result or "rows" not in self._result):
            return -1
        return self._result.get("rowcount", -1)

    def next(self):
        """
        Return the next row of a query result set, respecting if cursor was
        closed.
        """
        if self.rows is None:
            raise ProgrammingError(
                "No result available. " +
                "execute() or executemany() must be called first."
            )
        elif not self._closed:
            return next(self.rows)
        else:
            raise ProgrammingError("Cursor closed")

    __next__ = next

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
        This read-only attribute specifies the server-side duration of a query
        in milliseconds.
        """
        if self._closed or \
                not self._result or \
                "duration" not in self._result:
            return -1
        return self._result.get("duration", 0)

    def _convert_rows(self):
        """
        Iterate rows, apply type converters, and generate converted rows.
        """
        assert "col_types" in self._result and self._result["col_types"], \
               "Unable to apply type conversion without `col_types` information"

        # Resolve `col_types` definition to converter functions. Running the lookup
        # redundantly on each row loop iteration would be a huge performance hog.
        types = self._result["col_types"]
        converters = [
            self._converter.get(type) for type in types
        ]

        # Process result rows with conversion.
        for row in self._result["rows"]:
            yield [
                convert(value)
                for convert, value in zip(converters, row)
            ]

    @property
    def time_zone(self):
        """
        Get the current time zone.
        """
        return self._time_zone

    @time_zone.setter
    def time_zone(self, tz):
        """
        Set the time zone.

        Different data types are supported. Available options are:

        - ``datetime.timezone.utc``
        - ``datetime.timezone(datetime.timedelta(hours=7), name="MST")``
        - ``pytz.timezone("Australia/Sydney")``
        - ``zoneinfo.ZoneInfo("Australia/Sydney")``
        - ``+0530`` (UTC offset in string format)

        When `time_zone` is `None`, the returned `datetime` objects are
        "naive", without any `tzinfo`, converted using ``datetime.utcfromtimestamp(...)``.

        When `time_zone` is given, the returned `datetime` objects are "aware",
        with `tzinfo` set, converted using ``datetime.fromtimestamp(..., tz=...)``.
        """

        # Do nothing when time zone is reset.
        if tz is None:
            self._time_zone = None
            return

        # Requesting datetime-aware `datetime` objects needs the data type converter.
        # Implicitly create one, when needed.
        if self._converter is None:
            self._converter = Converter()

        # When the time zone is given as a string, assume UTC offset format, e.g. `+0530`.
        if isinstance(tz, str):
            tz = self._timezone_from_utc_offset(tz)

        self._time_zone = tz

        def _to_datetime_with_tz(value: t.Optional[float]) -> t.Optional[datetime]:
            """
            Convert CrateDB's `TIMESTAMP` value to a native Python `datetime`
            object, with timezone-awareness.
            """
            if value is None:
                return None
            return datetime.fromtimestamp(value / 1e3, tz=self._time_zone)

        # Register converter function for `TIMESTAMP` type.
        self._converter.set(DataType.TIMESTAMP_WITH_TZ, _to_datetime_with_tz)
        self._converter.set(DataType.TIMESTAMP_WITHOUT_TZ, _to_datetime_with_tz)

    @staticmethod
    def _timezone_from_utc_offset(tz) -> timezone:
        """
        Convert UTC offset in string format (e.g. `+0530`) into `datetime.timezone` object.
        """
        assert len(tz) == 5, f"Time zone '{tz}' is given in invalid UTC offset format"
        try:
            hours = int(tz[:3])
            minutes = int(tz[0] + tz[3:])
            return timezone(timedelta(hours=hours, minutes=minutes), name=tz)
        except Exception as ex:
            raise ValueError(f"Time zone '{tz}' is given in invalid UTC offset format: {ex}")
