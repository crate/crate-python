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

import typing as t

from crate.client._cursor_base import CursorBase

if t.TYPE_CHECKING:
    from crate.client.aio.connection import AsyncConnection


class AsyncCursor(CursorBase):
    """
    Asynchronous cursor. Experimental.
    """

    connection: "AsyncConnection"

    async def execute(
        self,
        sql: str,
        parameters: t.Any = None,
        bulk_parameters: t.Any = None,
    ) -> None:
        """
        Prepare and execute a database operation (query or command).
        """
        self._set_result(
            await self.connection.client.sql(
                *self._prepare(sql, parameters, bulk_parameters)
            )
        )

    async def executemany(
        self, sql: str, seq_of_parameters: t.Sequence[t.Any]
    ) -> t.List[t.Dict[str, t.Any]]:
        """
        Prepare a database operation (query or command) and then execute it
        against all parameter sequences or mappings found in the sequence
        ``seq_of_parameters``.
        """
        sql, bulk_parameters = self._prepare_many(sql, seq_of_parameters)
        await self.execute(sql, bulk_parameters=bulk_parameters)
        return self._bulk_result()

    async def fetchone(self) -> t.Optional[t.List[t.Any]]:
        """
        Fetch the next row of a query result set, returning a single sequence,
        or None when no more data is available.
        """
        return self._fetchone()

    async def fetchmany(
        self, size: t.Optional[int] = None
    ) -> t.List[t.List[t.Any]]:
        """
        Fetch the next set of rows of a query result, returning a sequence of
        sequences (e.g. a list of tuples). An empty sequence is returned when
        no more rows are available.
        """
        return self._fetchmany(size)

    async def fetchall(self) -> t.List[t.List[t.Any]]:
        """
        Fetch all (remaining) rows of a query result, returning them as a
        sequence of sequences (e.g. a list of tuples). Note that the cursor's
        arraysize attribute can affect the performance of this operation.
        """
        return self._fetchall()

    async def close(self) -> None:
        """
        Close the cursor now
        """
        self._close()

    def __aiter__(self) -> "AsyncCursor":
        """
        Iterate the remaining rows with ``async for``.
        """
        return self

    async def __anext__(self) -> t.List[t.Any]:
        try:
            return self._next_row()
        except StopIteration:
            raise StopAsyncIteration from None

    async def __aenter__(self) -> "AsyncCursor":
        return self

    async def __aexit__(self, *excs: object) -> None:
        await self.close()
