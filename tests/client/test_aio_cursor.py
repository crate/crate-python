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


import datetime
import inspect
import types
from unittest.mock import MagicMock

import pytest

pytest.importorskip("aiohttp")

from crate.client.aio._http import AsyncClient  # noqa: E402
from crate.client.aio.cursor import AsyncCursor  # noqa: E402
from crate.client.converter import Converter, DefaultTypeConverter  # noqa: E402
from crate.client.cursor import Cursor  # noqa: E402
from crate.client.exceptions import ProgrammingError  # noqa: E402
from crate.client.http import Client  # noqa: E402

SELECT = {
    "cols": ["name", "address"],
    "col_types": [4, 5],
    "rows": [
        ["foo", "10.10.10.1"],
        ["bar", "10.10.10.2"],
        ["baz", "10.10.10.3"],
    ],
    "rowcount": 3,
    "duration": 123,
}

# CrateDB answers DML and `SET` with one empty row.
DML = {"cols": [], "col_types": [], "rows": [[]], "rowcount": 1, "duration": 5}

BULK = {
    "cols": [],
    "duration": 7,
    "results": [{"rowcount": 1}, {"rowcount": -2}, {"rowcount": 1}],
}

TIMESTAMPS = {
    "cols": ["name", "ts"],
    "col_types": [4, 11],
    "rows": [["foo", 1658167836758], [None, None]],
    "rowcount": 2,
}

MST = datetime.timezone(datetime.timedelta(hours=7), name="MST")


def custom_converter():
    converter = Converter()
    converter.set(5, lambda value: f"ip:{value}")
    return converter


# (id, response, cursor arguments, steps).
SCENARIOS = [
    (
        "fetch",
        SELECT,
        {},
        [
            ("execute", "SELECT name, address FROM t"),
            ("fetchone",),
            ("fetchmany",),
            ("fetchmany", 5),
            ("fetchone",),
            ("fetchall",),
        ],
    ),
    (
        "fetchmany-zero-fetches-all",
        SELECT,
        {},
        [("execute", "SELECT 1"), ("fetchmany", 0)],
    ),
    (
        "fetchmany-arraysize",
        SELECT,
        {},
        [("execute", "SELECT 1"), ("set", "arraysize", 2), ("fetchmany",)],
    ),
    (
        "qmark",
        SELECT,
        {},
        [("execute", "SELECT ? FROM t WHERE a = ?", [1, "a"]), ("fetchall",)],
    ),
    (
        "numeric",
        SELECT,
        {},
        [("execute", "SELECT $1, $2, $1", [1, 2])],
    ),
    (
        "pyformat",
        SELECT,
        {},
        [("execute", "SELECT %(a)s, %(b)s", {"b": 2, "a": 1})],
    ),
    (
        "pyformat-repeated",
        SELECT,
        {},
        [("execute", "SELECT %(x)s, %(x)s", {"x": 42})],
    ),
    (
        "pyformat-missing",
        SELECT,
        {},
        [("execute", "SELECT %(z)s", {"a": 1}), ("fetchone",)],
    ),
    (
        "pyformat-non-identifier-keys",
        DML,
        {},
        [
            (
                "execute",
                "UPDATE t SET data['x'] = %(data['x'])s WHERE n = %(n)s",
                {"data['x']": 42, "n": "Berlin"},
            )
        ],
    ),
    (
        "bulk",
        BULK,
        {},
        [("execute", "INSERT INTO t VALUES (?)", None, [[1], [2], [3]])],
    ),
    (
        "bulk-pyformat-lists",
        BULK,
        {},
        [("execute", "INSERT INTO t VALUES (%s, %(a)s)", None, [[1, 2]])],
    ),
    (
        "bulk-pyformat-dicts",
        BULK,
        {},
        [
            (
                "execute",
                "INSERT INTO t VALUES (%(a)s, %(b)s)",
                None,
                [{"a": 1, "b": 2}, {"b": 4, "a": 3}],
            )
        ],
    ),
    (
        "bulk-pyformat-mixed-rows",
        BULK,
        {},
        [
            (
                "execute",
                "INSERT INTO t VALUES (%(a)s)",
                None,
                [{"a": 1}, [2]],
            )
        ],
    ),
    (
        "executemany",
        BULK,
        {},
        [
            ("executemany", "INSERT INTO t VALUES (?)", [[1], [2], [3]]),
            ("fetchall",),
        ],
    ),
    (
        "executemany-pyformat",
        BULK,
        {},
        [
            (
                "executemany",
                "INSERT INTO t VALUES (%(a)s)",
                [{"a": 1}, {"a": 2}],
            )
        ],
    ),
    (
        "executemany-pyformat-missing",
        BULK,
        {},
        [("executemany", "INSERT INTO t VALUES (%(a)s)", [{"b": 1}])],
    ),
    (
        "executemany-empty",
        BULK,
        {},
        [("executemany", "INSERT INTO t VALUES (?)", [])],
    ),
    (
        "executemany-with-converter",
        SELECT,
        {"converter": DefaultTypeConverter},
        [("executemany", "", []), ("fetchall",)],
    ),
    (
        "dml",
        DML,
        {},
        [("execute", "INSERT INTO t VALUES (1)"), ("fetchall",)],
    ),
    (
        "dml-with-converter",
        DML,
        {"converter": DefaultTypeConverter},
        [("execute", "INSERT INTO t VALUES (1)"), ("fetchall",)],
    ),
    (
        "default-converter",
        SELECT,
        {"converter": DefaultTypeConverter},
        [("execute", "SELECT 1"), ("fetchall",)],
    ),
    (
        "custom-converter",
        SELECT,
        {"converter": custom_converter},
        [("execute", "SELECT 1"), ("fetchall",)],
    ),
    (
        "time-zone-utc-offset",
        TIMESTAMPS,
        {"time_zone": "+0530"},
        [("execute", "SELECT 1"), ("fetchall",)],
    ),
    (
        "time-zone-change",
        TIMESTAMPS,
        {"time_zone": MST},
        [
            ("execute", "SELECT 1"),
            ("fetchall",),
            ("set", "time_zone", datetime.timezone.utc),
            ("execute", "SELECT 1"),
            ("fetchall",),
            ("set", "time_zone", None),
            ("execute", "SELECT 1"),
            ("fetchall",),
        ],
    ),
    (
        "time-zone-invalid",
        TIMESTAMPS,
        {},
        [("set", "time_zone", "+05:30"), ("set", "time_zone", "foo")],
    ),
    (
        "server-error",
        ProgrammingError("SQLParseException[line 1:1: mismatched input]"),
        {},
        [("execute", "SELEKT 1"), ("fetchone",)],
    ),
    (
        "before-execute",
        SELECT,
        {},
        [("fetchone",), ("fetchmany",), ("fetchall",)],
    ),
    (
        "closed-cursor",
        SELECT,
        {},
        [
            ("execute", "SELECT 1"),
            ("close",),
            ("fetchone",),
            ("execute", "SELECT 1"),
            ("executemany", "SELECT 1", [[1]]),
            ("close",),
        ],
    ),
    (
        "closed-connection",
        SELECT,
        {"connection_closed": True},
        [("execute", "SELECT 1"), ("executemany", "SELECT 1", [[1]])],
    ),
    (
        "unsupported-methods",
        SELECT,
        {},
        [("setinputsizes", [1]), ("setoutputsize", 1, 0)],
    ),
]


def _connection(client_class, response, connection_closed=False):
    client = MagicMock(spec=client_class)
    if isinstance(response, BaseException):
        client.sql.side_effect = response
    else:
        client.sql.return_value = response
    return types.SimpleNamespace(client=client, _closed=connection_closed)


def _cursor(cursor_class, connection, converter=None, time_zone=None):
    return cursor_class(
        connection,
        converter=converter() if converter else None,
        time_zone=time_zone,
    )


def _state(cursor):
    """
    The cursor attributes after a step. Attributes that raise record the
    exception instead.
    """
    state = {}
    for name in ("rowcount", "description", "duration", "time_zone"):
        try:
            state[name] = getattr(cursor, name)
        except Exception as ex:
            state[name] = (type(ex), str(ex))
    return state


def _outcome(call):
    try:
        return ("returned", call())
    except Exception as ex:
        return ("raised", type(ex), str(ex))


async def _async_outcome(call):
    try:
        return ("returned", await call())
    except Exception as ex:
        return ("raised", type(ex), str(ex))


def run_sync(response, cursor_args, steps):
    cursor_args = dict(cursor_args)
    connection = _connection(
        Client, response, cursor_args.pop("connection_closed", False)
    )
    cursor = _cursor(Cursor, connection, **cursor_args)
    outcomes = []
    for name, *args in steps:
        if name == "set":
            outcome = _outcome(lambda args=args: setattr(cursor, *args))
        else:
            method = getattr(cursor, name)
            outcome = _outcome(lambda method=method, args=args: method(*args))
        outcomes.append((outcome, _state(cursor)))
    return outcomes, connection.client.sql.call_args_list


async def run_async(response, cursor_args, steps):
    cursor_args = dict(cursor_args)
    connection = _connection(
        AsyncClient, response, cursor_args.pop("connection_closed", False)
    )
    cursor = _cursor(AsyncCursor, connection, **cursor_args)
    outcomes = []
    for name, *args in steps:
        if name == "set":
            outcome = _outcome(lambda args=args: setattr(cursor, *args))
        elif inspect.iscoroutinefunction(getattr(AsyncCursor, name)):
            method = getattr(cursor, name)
            outcome = await _async_outcome(
                lambda method=method, args=args: method(*args)
            )
        else:
            method = getattr(cursor, name)
            outcome = _outcome(lambda method=method, args=args: method(*args))
        outcomes.append((outcome, _state(cursor)))
    return outcomes, connection.client.sql.await_args_list


@pytest.mark.parametrize(
    "response, cursor_args, steps",
    [scenario[1:] for scenario in SCENARIOS],
    ids=[scenario[0] for scenario in SCENARIOS],
)
@pytest.mark.asyncio
async def test_same_as_sync_cursor(response, cursor_args, steps):
    expected, expected_calls = run_sync(response, cursor_args, steps)
    actual, actual_calls = await run_async(response, cursor_args, steps)
    assert actual_calls == expected_calls
    for step, actual_step, expected_step in zip(
        steps, actual, expected, strict=True
    ):
        assert actual_step == expected_step, step


@pytest.mark.asyncio
async def test_fetch():
    """
    Pins the values the parity scenarios compare.
    """
    connection = _connection(AsyncClient, SELECT)
    cursor = AsyncCursor(connection, converter=None)
    await cursor.execute("SELECT %(a)s", {"a": 1})
    connection.client.sql.assert_awaited_once_with("SELECT $1", [1], None)
    assert cursor.rowcount == 3
    assert cursor.duration == 123
    assert cursor.description == (
        ("name", None, None, None, None, None, None),
        ("address", None, None, None, None, None, None),
    )
    assert await cursor.fetchone() == ["foo", "10.10.10.1"]
    assert await cursor.fetchmany(size=1) == [["bar", "10.10.10.2"]]
    assert await cursor.fetchall() == [["baz", "10.10.10.3"]]
    assert await cursor.fetchone() is None


@pytest.mark.asyncio
async def test_executemany_results():
    connection = _connection(AsyncClient, BULK)
    cursor = AsyncCursor(connection, converter=None)
    results = await cursor.executemany(
        "INSERT INTO t VALUES (%(a)s)", [{"a": 1}, {"a": 2}, {"a": 3}]
    )
    connection.client.sql.assert_awaited_once_with(
        "INSERT INTO t VALUES ($1)", None, [[1], [2], [3]]
    )
    assert results == BULK["results"]
    assert cursor.rowcount == 2
    assert cursor.duration == 7


@pytest.mark.asyncio
async def test_async_iteration():
    cursor = AsyncCursor(_connection(AsyncClient, SELECT), converter=None)
    await cursor.execute("SELECT 1")
    assert await cursor.fetchone() == ["foo", "10.10.10.1"]
    assert [row async for row in cursor] == [
        ["bar", "10.10.10.2"],
        ["baz", "10.10.10.3"],
    ]
    assert [row async for row in cursor] == []


@pytest.mark.asyncio
async def test_async_iteration_before_execute_and_after_close():
    cursor = AsyncCursor(_connection(AsyncClient, SELECT), converter=None)
    with pytest.raises(ProgrammingError, match="No result available"):
        async for _ in cursor:
            pass
    await cursor.execute("SELECT 1")
    await cursor.close()
    with pytest.raises(ProgrammingError, match="Cursor closed"):
        async for _ in cursor:
            pass


@pytest.mark.asyncio
async def test_async_with_closes_cursor():
    async with AsyncCursor(
        _connection(AsyncClient, SELECT), converter=None
    ) as cursor:
        await cursor.execute("SELECT 1")
        assert cursor.rowcount == 3
    assert cursor.rowcount == -1
    with pytest.raises(ProgrammingError, match="Cursor closed"):
        await cursor.execute("SELECT 1")


def test_contract():
    """
    The methods that may block in the DB API are coroutines; the others are
    plain methods.
    """
    for name in (
        "execute",
        "executemany",
        "fetchone",
        "fetchmany",
        "fetchall",
        "close",
        "__anext__",
        "__aenter__",
        "__aexit__",
    ):
        assert inspect.iscoroutinefunction(getattr(AsyncCursor, name)), name
    for name in ("setinputsizes", "setoutputsize", "__aiter__"):
        assert not inspect.iscoroutinefunction(getattr(AsyncCursor, name))

    assert "size" in inspect.signature(AsyncCursor.fetchmany).parameters
    cursor = AsyncCursor(_connection(AsyncClient, SELECT), converter=None)
    assert cursor.arraysize == 1
    assert cursor.lastrowid is None
