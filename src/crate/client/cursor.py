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
import warnings

from ._cursor_base import (  # noqa: F401
    _NAMED_PARAM_RE,
    CursorBase,
    _convert_named_bulk_params,
    _convert_named_to_positional,
    _rewrite_pyformat_sql,
)


class Cursor(CursorBase):
    """
    not thread-safe by intention
    should not be shared between different threads
    """

    def execute(self, sql, parameters=None, bulk_parameters=None):
        """
        Prepare and execute a database operation (query or command).
        """
        self._set_result(
            self.connection.client.sql(
                *self._prepare(sql, parameters, bulk_parameters)
            )
        )

    def executemany(self, sql, seq_of_parameters):
        """
        Prepare a database operation (query or command) and then execute it
        against all parameter sequences or mappings found in the sequence
        ``seq_of_parameters``.
        """
        sql, bulk_parameters = self._prepare_many(sql, seq_of_parameters)
        self.execute(sql, bulk_parameters=bulk_parameters)
        return self._bulk_result()

    def fetchone(self):
        """
        Fetch the next row of a query result set, returning a single sequence,
        or None when no more data is available.
        Alias for ``next()``.
        """
        return self._fetchone()

    def __iter__(self):
        """
        support iterator interface:
        http://legacy.python.org/dev/peps/pep-0249/#iter

        This iterator is shared. Advancing this iterator will advance other
        iterators created from this cursor.
        """
        warnings.warn("DB-API extension cursor.__iter__() used", stacklevel=2)
        return self

    def fetchmany(self, count=None):
        """
        Fetch the next set of rows of a query result, returning a sequence of
        sequences (e.g. a list of tuples). An empty sequence is returned when
        no more rows are available.
        """
        return self._fetchmany(count)

    def fetchall(self):
        """
        Fetch all (remaining) rows of a query result, returning them as a
        sequence of sequences (e.g. a list of tuples). Note that the cursor's
        arraysize attribute can affect the performance of this operation.
        """
        return self._fetchall()

    def close(self):
        """
        Close the cursor now
        """
        self._close()

    def next(self):
        """
        Return the next row of a query result set, respecting if cursor was
        closed.
        """
        return self._next_row()

    def __next__(self):
        return self.next()
