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

import asyncio
import gc
import inspect
import json
import warnings

import pytest

pytest.importorskip("aiohttp")

from aiohttp import web  # noqa: E402
from verlib2 import Version  # noqa: E402

import crate.client  # noqa: E402
from crate.client import aio, exceptions  # noqa: E402
from crate.client.aio import (  # noqa: E402
    AsyncClient,
    AsyncConnection,
    AsyncCursor,
)
from crate.client.converter import DefaultTypeConverter  # noqa: E402

from .aio_support import FakeCrate, unused_port  # noqa: E402

pytestmark = [
    pytest.mark.timeout(30, method="thread"),
    pytest.mark.filterwarnings("error::ResourceWarning"),
    pytest.mark.filterwarnings(
        "error::pytest.PytestUnraisableExceptionWarning"
    ),
]


def crate_handler(version="6.1.2", result=None):

    async def handler(request):
        if request.path == "/":
            return web.json_response(
                {"name": "crate-1", "version": {"number": version}}
            )
        return web.json_response(
            result or {"cols": ["name"], "rows": [["a"]], "rowcount": 1}
        )

    return handler


def dead_server():
    return f"http://127.0.0.1:{unused_port()}"


def sync_failure(*args, **kwargs):
    try:
        crate.client.connect(*args, **kwargs).close()
    except exceptions.Error as ex:
        return type(ex), str(ex)
    raise AssertionError("connect() did not fail")


async def async_failure(*args, **kwargs):
    try:
        await (await aio.connect(*args, **kwargs)).close()
    except exceptions.Error as ex:
        return type(ex), str(ex)
    raise AssertionError("connect() did not fail")


def test_exports():
    assert aio.paramstyle == crate.client.paramstyle == "pyformat"
    for name in [
        "Error",
        "Warning",
        "InterfaceError",
        "DatabaseError",
        "InternalError",
        "OperationalError",
        "ProgrammingError",
        "IntegrityError",
        "DataError",
        "NotSupportedError",
        "ConnectionError",
        "BlobLocationNotFoundException",
        "DigestNotFoundException",
    ]:
        assert getattr(aio, name) is getattr(exceptions, name), name
    assert aio.connect is aio.connection.connect
    assert aio.AsyncConnection is AsyncConnection
    assert aio.AsyncCursor is AsyncCursor
    assert aio.AsyncClient is AsyncClient


def test_connect_signature_matches_sync():
    sync = inspect.signature(crate.client.connect).parameters
    actual = inspect.signature(aio.connect).parameters
    assert list(actual) == list(sync)
    for name, parameter in actual.items():
        assert parameter.default == sync[name].default, name
    assert inspect.iscoroutinefunction(aio.connect)


@pytest.mark.asyncio
async def test_connect_sets_lowest_server_version(fake_crate):
    old = await fake_crate(crate_handler(version="5.10.3"))
    new = await fake_crate(crate_handler(version="6.1.2"))
    async with await aio.connect([new.url, old.url]) as conn:
        assert conn.lowest_server_version == Version("5.10.3")
        assert not conn.closed
    assert conn.closed


@pytest.mark.asyncio
async def test_connect_probes_servers_concurrently(fake_crate):
    both_probed = asyncio.Event()
    probes = []

    async def handler(request):
        probes.append(request.url.port)
        if len(probes) == 2:
            both_probed.set()
        await both_probed.wait()
        return web.json_response({"version": {"number": "6.1.2"}})

    first = await fake_crate(handler)
    second = await fake_crate(handler)
    conn = await asyncio.wait_for(aio.connect([first.url, second.url]), 5)
    await conn.close()
    assert sorted(probes) == sorted([first.port, second.port])


@pytest.mark.asyncio
async def test_connect_with_a_dead_server(fake_crate):
    live = await fake_crate(crate_handler(version="5.10.3"))
    async with await aio.connect([dead_server(), live.url]) as conn:
        assert conn.lowest_server_version == Version("5.10.3")


@pytest.mark.asyncio
async def test_connect_with_all_servers_dead():
    servers = [dead_server(), dead_server()]
    expected = await asyncio.to_thread(sync_failure, servers)
    client = AsyncClient(servers)
    actual = await async_failure(client=client)
    assert actual[0] is expected[0] is exceptions.ConnectionError
    assert client.closed


@pytest.mark.asyncio
async def test_connect_with_wrong_password(fake_crate):

    async def unauthorized(request):
        return web.json_response(
            {
                "error": {
                    "message": "AuthenticationException[password "
                    "authentication failed for user me]",
                    "code": 40100,
                }
            },
            status=401,
            reason="Unauthorized",
        )

    crate = await fake_crate(unauthorized)
    kwargs = {"username": "me", "password": "wrong"}
    expected = await asyncio.to_thread(sync_failure, crate.url, **kwargs)
    client = AsyncClient(crate.url, **kwargs)
    actual = await async_failure(client=client)
    assert actual == expected
    assert actual[0] is exceptions.ProgrammingError
    assert client.closed


@pytest.mark.asyncio
async def test_cancelled_connect_closes_the_client(fake_crate):
    probing = asyncio.Event()

    async def slow(request):
        probing.set()
        await asyncio.sleep(10)
        return web.json_response({})

    crate = await fake_crate(slow)
    client = AsyncClient(servers=crate.url)
    task = asyncio.ensure_future(aio.connect(client=client))
    await probing.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert client.closed
    assert not any(server.is_open for server in client.server_pool.values())
    assert client.active_servers == [crate.url]


@pytest.mark.asyncio
async def test_cursor(fake_crate):
    crate = await fake_crate(
        crate_handler(
            result={
                "cols": ["name"],
                "col_types": [4],
                "rows": [["a"], ["b"], ["c"]],
                "rowcount": 3,
            }
        )
    )
    async with await aio.connect(crate.url) as conn:
        cursor = conn.cursor()
        assert isinstance(cursor, AsyncCursor)
        assert cursor.connection is conn
        await cursor.execute("SELECT name FROM t WHERE id = %(id)s", {"id": 1})
        assert await cursor.fetchone() == ["a"]
        assert [row async for row in cursor] == [["b"], ["c"]]
        await cursor.executemany("SELECT name FROM t WHERE id = ?", [[1], [2]])
    _, body = crate.requests[-2]
    assert json.loads(body) == {
        "stmt": "SELECT name FROM t WHERE id = $1",
        "args": [1],
    }
    _, body = crate.requests[-1]
    assert json.loads(body) == {
        "stmt": "SELECT name FROM t WHERE id = ?",
        "bulk_args": [[1], [2]],
    }


@pytest.mark.asyncio
async def test_cursor_inherits_converter_and_time_zone(fake_crate):
    """
    As in sync, an omitted `converter` or `time_zone` is taken from the
    connection, and an explicit `None` means none.
    """
    crate = await fake_crate(crate_handler())
    converter = DefaultTypeConverter()
    async with await aio.connect(
        crate.url, converter=converter, time_zone="+0530"
    ) as conn:
        inherited = conn.cursor()
        assert inherited._converter is converter
        assert str(inherited.time_zone) == "+0530"
        explicit = conn.cursor(converter=None, time_zone=None)
        assert explicit._converter is None
        assert explicit.time_zone is None


@pytest.mark.asyncio
async def test_lifecycle(fake_crate):
    crate = await fake_crate(crate_handler())
    conn = await aio.connect(crate.url)
    cursor = conn.cursor()
    assert inspect.iscoroutinefunction(conn.commit)
    await conn.commit()
    await conn.rollback()
    await conn.close()
    assert conn.closed
    assert conn.client.closed
    await conn.close()
    with pytest.raises(exceptions.ProgrammingError, match="Connection closed"):
        await conn.commit()
    with pytest.raises(exceptions.ProgrammingError, match="Connection closed"):
        conn.cursor()
    with pytest.raises(exceptions.ProgrammingError, match="Connection closed"):
        await cursor.execute("SELECT 1")
    await conn.rollback()


@pytest.mark.asyncio
async def test_close_waits_for_in_flight_requests(fake_crate):
    executing = asyncio.Event()
    release = asyncio.Event()

    async def handler(request):
        if request.path == "/":
            return web.json_response({"version": {"number": "6.1.2"}})
        executing.set()
        await release.wait()
        return web.json_response({"cols": [], "rows": [[]], "rowcount": 1})

    crate = await fake_crate(handler)
    conn = await aio.connect(crate.url)
    cursor = conn.cursor()
    execute = asyncio.ensure_future(cursor.execute("INSERT INTO t VALUES (1)"))
    await executing.wait()
    close = asyncio.ensure_future(conn.close())
    await asyncio.sleep(0.1)
    assert not close.done()
    release.set()
    await asyncio.wait_for(asyncio.gather(execute, close), 5)
    assert cursor.rowcount == 1


@pytest.mark.asyncio
async def test_terminate(fake_crate):
    crate = await fake_crate(crate_handler())
    conn = await aio.connect(crate.url)
    assert not inspect.iscoroutinefunction(conn.terminate)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        conn.terminate()
        assert conn.closed
        assert conn.client.closed
        del conn
        gc.collect()
        await asyncio.sleep(0)
    assert [str(w.message) for w in caught] == []


@pytest.mark.asyncio
async def test_unclosed_connection_warns_once(fake_crate):
    crate = await fake_crate(crate_handler())
    conn = await aio.connect(crate.url)
    client = conn.client
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        del conn
        gc.collect()
        await asyncio.sleep(0)
    assert [w.category for w in caught] == [ResourceWarning]
    assert "unclosed <AsyncConnection <AsyncClient" in str(caught[0].message)
    assert client.closed
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        del client
        gc.collect()
        await asyncio.sleep(0)
    assert caught == []


def test_different_event_loop():

    async def start():
        crate = await FakeCrate(crate_handler()).start()
        return crate, await aio.connect(crate.url)

    loop = asyncio.new_event_loop()
    try:
        crate, conn = loop.run_until_complete(start())

        async def use():
            await conn.cursor().execute("SELECT 1")

        with pytest.raises(
            exceptions.ProgrammingError, match="different event loop"
        ):
            asyncio.run(use())
        loop.run_until_complete(conn.close())
        loop.run_until_complete(crate.stop())
    finally:
        loop.close()
