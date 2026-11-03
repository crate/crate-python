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
import errno
import gc
import json
import logging
import socket
import ssl
import time
import warnings

import pytest

pytest.importorskip("aiohttp")

import aiohttp  # noqa: E402
import urllib3  # noqa: E402
from aiohttp import web  # noqa: E402

from crate.client import exceptions  # noqa: E402
from crate.client._options import keepalive_socket_options  # noqa: E402
from crate.client.aio import _http  # noqa: E402
from crate.client.aio._http import (  # noqa: E402
    AsyncClient,
    AsyncServer,
    backoff_time,
    client_timeout,
)
from crate.client.http import Client  # noqa: E402

from .aio_support import (  # noqa: E402
    SQL_RESULT,
    FakeCrate,
    SilentFirstProxy,
    server_ssl_context,
    unused_port,
)
from .settings import assets_path  # noqa: E402

pytestmark = [
    pytest.mark.timeout(30, method="thread"),
    pytest.mark.filterwarnings("error::ResourceWarning"),
    pytest.mark.filterwarnings(
        "error::pytest.PytestUnraisableExceptionWarning"
    ),
]

CA_VALID = assets_path("pki/cacert_valid.pem")
CA_INVALID = assets_path("pki/cacert_invalid.pem")


async def unavailable(request):
    return web.Response(status=503, reason="Service Unavailable")


@pytest.mark.parametrize(
    "errors, expected", [(0, 0), (1, 0), (2, 1.0), (3, 2.0), (12, 120.0)]
)
def test_backoff_time_matches_urllib3(errors, expected):
    assert backoff_time(0.5, errors) == expected
    retry = urllib3.Retry(total=20, backoff_factor=0.5)
    for _ in range(errors):
        retry = retry.increment(
            "POST", "/", error=urllib3.exceptions.ConnectTimeoutError()
        )
    assert retry.get_backoff_time() == expected


@pytest.mark.parametrize(
    "timeout, sock_timeout", [(None, None), (2, 2), (1.5, 1.5), ("7", 7.0)]
)
def test_client_timeout(timeout, sock_timeout):
    result = client_timeout(timeout)
    # aiohttp's defaults would be `total=300, sock_connect=30`.
    assert result.total is None
    assert result.connect is None
    assert result.sock_connect == sock_timeout
    assert result.sock_read == sock_timeout


@pytest.mark.parametrize("timeout", [urllib3.Timeout(connect=1), [1], True])
def test_client_timeout_invalid(timeout):
    with pytest.raises(TypeError):
        client_timeout(timeout)
    with pytest.raises(TypeError):
        AsyncClient(timeout=timeout)


def test_creates_no_aiohttp_objects():
    client = AsyncClient(servers=["localhost:4200", "localhost:4201"])
    assert all(s._session is None for s in client.server_pool.values())
    assert client.active_servers == [
        "http://localhost:4200",
        "http://localhost:4201",
    ]


def test_tls_context_only_for_https():
    client = AsyncClient(servers=["http://localhost:4200", "https://h:4200"])
    assert client.server_pool["http://localhost:4200"]._ssl is None
    assert client.server_pool["https://h:4200"]._ssl is client._ssl_context


@pytest.mark.asyncio
async def test_sql(fake_crate):
    crate = await fake_crate()
    client = AsyncClient(
        servers=crate.url, username="crate", password="s3cr3t", schema="doc"
    )
    try:
        assert await client.sql("SELECT name FROM sys.cluster") == SQL_RESULT
        assert await client.sql(None) is None
    finally:
        await client.close()

    assert len(crate.requests) == 1
    request, body = crate.requests[0]
    assert request.method == "POST"
    assert request.path_qs == "/_sql?types=true"
    assert json.loads(body) == {"stmt": "SELECT name FROM sys.cluster"}
    assert request.headers["Authorization"] == "Basic Y3JhdGU6czNjcjN0"
    assert request.headers["X-User"] == "crate"
    assert request.headers["Default-Schema"] == "doc"
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["Accept"] == "application/json"
    assert request.headers["Accept-Encoding"] == "gzip, deflate"
    assert "Content-Encoding" not in request.headers
    assert "Cookie" not in request.headers


@pytest.mark.asyncio
async def test_sql_compressed_and_error_trace(fake_crate):
    crate = await fake_crate()
    client = AsyncClient(servers=crate.url, compress=True, error_trace=True)
    try:
        await client.sql("SELECT 1")
    finally:
        await client.close()
    request, body = crate.requests[0]
    assert request.path_qs == "/_sql?types=true&error_trace=true"
    assert request.headers["Content-Encoding"] == "gzip"
    assert json.loads(body) == {"stmt": "SELECT 1"}


@pytest.mark.asyncio
async def test_gzip_response(fake_crate):
    async def compressed(request):
        response = web.json_response(SQL_RESULT)
        response.enable_compression(web.ContentCoding.gzip)
        return response

    crate = await fake_crate(compressed)
    client = AsyncClient(servers=crate.url)
    try:
        assert await client.sql("SELECT 1") == SQL_RESULT
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_userinfo_and_path_prefix(fake_crate):
    """
    Credentials in the server URL become headers, and a path in the URL
    prefixes every request path.
    """
    crate = await fake_crate()
    url = crate.url.replace("http://", "http://crate:s3cr3t@") + "/crate/"
    client = AsyncClient(servers=url)
    try:
        await client.sql("SELECT 1")
    finally:
        await client.close()
    request, _ = crate.requests[0]
    assert request.path_qs == "/crate/_sql?types=true"
    assert request.headers.getall("Authorization") == ["Basic Y3JhdGU6czNjcjN0"]


@pytest.mark.asyncio
async def test_proxy_environment_ignored(fake_crate, monkeypatch):
    """
    As in sync, the proxy environment variables are ignored.
    """
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    dead_proxy = f"http://127.0.0.1:{unused_port()}"
    monkeypatch.setenv("HTTP_PROXY", dead_proxy)
    monkeypatch.setenv("http_proxy", dead_proxy)
    crate = await fake_crate()
    client = AsyncClient(servers=crate.url)
    client.connect_retries = 0
    try:
        assert await client.sql("SELECT 1") == SQL_RESULT
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_server_infos(fake_crate):
    crate = await fake_crate()
    client = AsyncClient(servers=crate.url)
    try:
        assert await client.server_infos(crate.url) == (
            crate.url,
            "crate-1",
            "6.1.2",
        )
    finally:
        await client.close()
    request, _ = crate.requests[0]
    assert request.method == "GET"
    assert request.path == "/"


async def relation_unknown(request):
    return web.json_response(
        {
            "error": {
                "message": "RelationUnknown[Relation 'foo' unknown]",
                "code": 4041,
            }
        },
        status=404,
    )


async def slow(request):
    await asyncio.sleep(2)
    return web.json_response(SQL_RESULT)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "handler, options, exception, match",
    [
        (relation_unknown, {}, exceptions.ProgrammingError, "RelationUnknown"),
        (unavailable, {}, exceptions.ProgrammingError, "No more Servers"),
        (slow, {"timeout": 0.2}, exceptions.ConnectionError, "No more Servers"),
        (None, {}, exceptions.ConnectionError, "No more Servers"),
    ],
    ids=["error-response", "503-on-all-servers", "read-timeout", "refused"],
)
async def test_same_exception_as_sync(
    fake_crate, handler, options, exception, match
):
    crate = None
    if handler is None:
        url = f"http://127.0.0.1:{unused_port()}"
    else:
        crate = await fake_crate(handler)
        url = crate.url

    def sync_sql():
        client = Client(servers=url, **options)
        try:
            client.sql("SELECT 1")
        finally:
            client.close()

    with pytest.raises(exception, match=match):
        await asyncio.to_thread(sync_sql)

    sent = len(crate.requests) if crate else 0
    client = AsyncClient(servers=url, **options)
    try:
        with pytest.raises(exception, match=match):
            await client.sql("SELECT 1")
    finally:
        await client.close()
    if crate:
        # Error responses, 503 and read timeouts are not retried.
        assert len(crate.requests) - sent == 1


@pytest.mark.asyncio
async def test_unavailable_fails_over(fake_crate, caplog):
    down = await fake_crate(unavailable)
    up = await fake_crate()
    client = AsyncClient(servers=[down.url, up.url])
    try:
        with caplog.at_level(logging.WARNING, logger="crate.client.aio"):
            assert await client.sql("SELECT 1") == SQL_RESULT
        assert client.active_servers == [up.url]
    finally:
        await client.close()
    assert len(down.requests) == 1
    assert [r.name for r in caplog.records] == ["crate.client.aio"]
    assert f"Removed server {down.url}" in caplog.text


@pytest.mark.asyncio
async def test_unavailable_on_given_server(fake_crate):
    crate = await fake_crate(unavailable)
    client = AsyncClient(servers=crate.url)
    try:
        with pytest.raises(exceptions.ConnectionError, match="503 Server"):
            await client.server_infos(crate.url)
        assert client.active_servers == [crate.url]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_read_timeout_fails_over(fake_crate):
    slow_server = await fake_crate(slow)
    fast_server = await fake_crate()
    client = AsyncClient(
        servers=[slow_server.url, fast_server.url], timeout=0.2
    )
    try:
        assert await client.sql("SELECT 1") == SQL_RESULT
        assert client.active_servers == [fast_server.url]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_no_timeout_waits(fake_crate):
    async def handler(request):
        await asyncio.sleep(0.3)
        return web.json_response(SQL_RESULT)

    crate = await fake_crate(handler)
    client = AsyncClient(servers=crate.url, timeout=None)
    try:
        assert await client.sql("SELECT 1") == SQL_RESULT
        session = client.server_pool[crate.url]._session
        # Not aiohttp's default of `total=300, sock_connect=30`.
        assert session.timeout == aiohttp.ClientTimeout(
            total=None, connect=None, sock_connect=None, sock_read=None
        )
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_connection_refused_fails_over(fake_crate):
    up = await fake_crate()
    down = f"http://127.0.0.1:{unused_port()}"
    client = AsyncClient(servers=[down, up.url])
    try:
        assert await client.sql("SELECT 1") == SQL_RESULT
        assert client.active_servers == [up.url]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_server_infos_unreachable():
    url = f"http://127.0.0.1:{unused_port()}"
    client = AsyncClient(servers=url)
    client.connect_retries = 0
    try:
        with pytest.raises(
            exceptions.ConnectionError, match="Server not available"
        ):
            await client.server_infos(url)
        assert client.active_servers == [url]
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        asyncio.TimeoutError(),
        ssl.SSLError(1, "[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC]"),
    ],
    ids=["asyncio-timeout", "ssl-error"],
)
async def test_unwrapped_transport_error_fails_over(
    fake_crate, monkeypatch, error
):
    """
    Errors that aiohttp does not wrap still fail over with
    `ConnectionError`, instead of surfacing as `ProgrammingError`.
    """
    first = await fake_crate()
    second = await fake_crate()
    original = AsyncServer.request

    async def fail_first(self, *args, **kwargs):
        if self.server == first.url:
            raise error
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(AsyncServer, "request", fail_first)
    client = AsyncClient(servers=[first.url, second.url])
    try:
        assert await client.sql("SELECT 1") == SQL_RESULT
        assert client.active_servers == [second.url]
        with pytest.raises(exceptions.ConnectionError):
            await client.server_infos(first.url)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_connect_retries_with_backoff(fake_crate, monkeypatch):
    """
    A connection failure is retried `connect_retries` times on the same
    server, with urllib3's backoff, before failing over.
    """
    crate = await fake_crate()
    attempts = []
    sleeps = []

    async def refuse(self, *args, **kwargs):
        attempts.append(self.server)
        raise aiohttp.ConnectionTimeoutError("connect timed out")

    async def record_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(AsyncServer, "request", refuse)
    monkeypatch.setattr(_http.asyncio, "sleep", record_sleep)
    client = AsyncClient(servers=crate.url, backoff_factor=0.1)
    try:
        with pytest.raises(exceptions.ConnectionError):
            await client.sql("SELECT 1")
    finally:
        await client.close()
    # urllib3's default is `Retry(total=10)`: 11 attempts in all.
    assert attempts == [crate.url] * 11
    assert sleeps == [backoff_time(0.1, n) for n in range(1, 11)]
    assert sleeps[:4] == [0.0, 0.2, 0.4, 0.8]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        aiohttp.ServerDisconnectedError(),
        aiohttp.ClientOSError(errno.ECONNRESET, "Connection reset by peer"),
        ConnectionResetError(errno.ECONNRESET, "Connection reset by peer"),
    ],
    ids=["disconnected", "oserror", "reset"],
)
async def test_stale_connection_retried_once(fake_crate, monkeypatch, error):
    crate = await fake_crate()
    original = AsyncServer.request
    calls = []

    async def flaky(self, *args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise error
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(AsyncServer, "request", flaky)
    client = AsyncClient(servers=crate.url)
    try:
        assert await client.sql("SELECT 1") == SQL_RESULT
        assert client.active_servers == [crate.url]
    finally:
        await client.close()
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_stale_connection_twice_fails_over(fake_crate, monkeypatch):
    """
    A second reset in the same request counts as a read failure. (The sync
    client keeps retrying a server that resets every connection.)
    """
    first = await fake_crate()
    second = await fake_crate()
    original = AsyncServer.request
    calls = []

    async def reset_first(self, *args, **kwargs):
        if self.server == first.url:
            calls.append(1)
            raise aiohttp.ServerDisconnectedError()
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(AsyncServer, "request", reset_first)
    client = AsyncClient(servers=[first.url, second.url])
    try:
        assert await client.sql("SELECT 1") == SQL_RESULT
        assert client.active_servers == [second.url]
    finally:
        await client.close()
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_reset_by_server(fake_crate):
    """
    A server that closes every connection without answering ends with
    `ConnectionError` instead of a retry loop.
    """

    async def reset(request):
        request.transport.close()
        await asyncio.sleep(1)
        return web.Response()

    crate = await fake_crate(reset)
    client = AsyncClient(servers=crate.url)
    try:
        with pytest.raises(exceptions.ConnectionError):
            await client.sql("SELECT 1")
    finally:
        await client.close()
    assert len(crate.requests) == 2


@pytest.mark.asyncio
async def test_redirect(fake_crate):
    target = await fake_crate()

    async def redirect(request):
        raise web.HTTPTemporaryRedirect(target.url + request.path_qs)

    origin = await fake_crate(redirect)
    client = AsyncClient(servers=origin.url)
    try:
        assert await client.sql("SELECT 1") == SQL_RESULT
        assert target.url in client.server_pool
        assert client.active_servers == [origin.url]
    finally:
        await client.close()
    assert json.loads(target.requests[0][1]) == {"stmt": "SELECT 1"}


@pytest.mark.asyncio
async def test_location_ignored_without_redirect_status(fake_crate):

    target = await fake_crate()

    async def multiple_choices(request):
        return web.json_response(
            SQL_RESULT, status=300, headers={"Location": target.url + "/x"}
        )

    origin = await fake_crate(multiple_choices)

    def sync_sql():
        client = Client(servers=origin.url)
        try:
            return client.sql("SELECT 1")
        finally:
            client.close()

    assert await asyncio.to_thread(sync_sql) == SQL_RESULT
    client = AsyncClient(servers=origin.url)
    try:
        assert await client.sql("SELECT 1") == SQL_RESULT
    finally:
        await client.close()
    assert target.requests == []


@pytest.mark.asyncio
async def test_redirect_hop_limit(fake_crate):
    loop_server = None

    async def redirect_to_self(request):
        raise web.HTTPTemporaryRedirect(loop_server.url + request.path_qs)

    loop_server = await fake_crate(redirect_to_self)
    client = AsyncClient(servers=loop_server.url)
    try:
        with pytest.raises(exceptions.ProgrammingError, match="10 redirects"):
            await client.sql("SELECT 1")
    finally:
        await client.close()
    assert len(loop_server.requests) == 11


@pytest.mark.asyncio
async def test_tls_handshake(https_server):

    url = "https://localhost:{}".format(https_server.server_address[1])

    client = AsyncClient(servers=url, ca_cert=CA_VALID)
    try:
        assert (await client.server_infos(url))[1] == "test"
    finally:
        await client.close()

    client = AsyncClient(servers=url, ca_cert=CA_INVALID)
    client.connect_retries = 0
    try:
        with pytest.raises(
            exceptions.ConnectionError, match="certificate verify failed"
        ):
            await client.server_infos(url)
    finally:
        await client.close()

    client = AsyncClient(servers=url, verify_ssl_cert=False)
    try:
        assert (await client.server_infos(url))[1] == "test"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_pool_size(fake_crate):
    running = 0
    most = 0

    async def handler(request):
        nonlocal running, most
        running += 1
        most = max(most, running)
        await asyncio.sleep(0.05)
        running -= 1
        return web.json_response(SQL_RESULT)

    crate = await fake_crate(handler)
    client = AsyncClient(servers=crate.url, pool_size=3)
    try:
        await asyncio.gather(*(client.sql("SELECT 1") for _ in range(12)))
    finally:
        await client.close()
    assert most == 3
    assert client.server_pool[crate.url]._pool_size == 3
    assert AsyncClient()._pool_size == 20


@pytest.mark.asyncio
async def test_fair_queuing(fake_crate):

    async def handler(request):
        await asyncio.sleep(0.001)
        return web.json_response(SQL_RESULT)

    crate = await fake_crate(handler)
    client = AsyncClient(servers=crate.url, pool_size=5)
    run_for = 1.0
    stop = time.monotonic() + run_for
    waits = []

    async def worker():
        while time.monotonic() < stop:
            start = time.monotonic()
            await client.sql("SELECT 1")
            waits.append(time.monotonic() - start)

    try:
        await asyncio.gather(*(worker() for _ in range(50)))
    finally:
        await client.close()
    # Fair queuing keeps the longest wait at a few tens of milliseconds
    assert max(waits) < run_for / 2


async def _cancel_after(coro, delay):
    task = asyncio.ensure_future(coro)
    await asyncio.sleep(delay)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_cancelled_waiter_frees_its_place(fake_crate):
    release = asyncio.Event()

    async def blocked(request):
        await release.wait()
        return web.json_response(SQL_RESULT)

    crate = await fake_crate(blocked)
    client = AsyncClient(servers=crate.url, pool_size=1)
    try:
        busy = asyncio.ensure_future(client.sql("SELECT 1"))
        await asyncio.sleep(0.05)
        await _cancel_after(client.sql("SELECT 2"), 0.05)
        release.set()
        assert await busy == SQL_RESULT
        assert await asyncio.wait_for(client.sql("SELECT 3"), 5) == SQL_RESULT
        server = client.server_pool[crate.url]
        assert server._in_flight == 0
    finally:
        await client.close()
    assert len(crate.requests) == 2


@pytest.mark.asyncio
async def test_cancel_during_tls_handshake(fake_crate):
    """
    The first connection hangs in the TLS handshake, which is part of
    connecting. The next request opens a new connection.
    """
    crate = await fake_crate(ssl_context=server_ssl_context())
    proxy = await SilentFirstProxy(crate.port).start()
    url = f"https://localhost:{proxy.port}"
    client = AsyncClient(servers=url, ca_cert=CA_VALID)
    try:
        await _cancel_after(client.sql("SELECT 1"), 0.2)
        assert crate.requests == []
        assert client.active_servers == [url]
        assert await client.sql("SELECT 2") == SQL_RESULT
        assert client.active_servers == [url]
    finally:
        await client.close()
        await proxy.stop()
    assert proxy.connections >= 2


@pytest.mark.asyncio
async def test_cancel_during_send(fake_crate):
    calls = []

    async def slow_first(request):
        calls.append(1)
        if len(calls) == 1:
            await asyncio.sleep(5)
        return web.json_response(SQL_RESULT)

    crate = await fake_crate(slow_first)
    client = AsyncClient(servers=crate.url)
    try:
        await _cancel_after(client.sql("SELECT 1"), 0.1)
        assert client.active_servers == [crate.url]
        assert await client.sql("SELECT 2") == SQL_RESULT
        assert client.server_pool[crate.url]._in_flight == 0
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_cancel_mid_body(fake_crate):
    calls = []

    async def stream_slowly(request):
        calls.append(1)
        if len(calls) > 1:
            return web.json_response(SQL_RESULT)
        response = web.StreamResponse()
        response.content_type = "application/json"
        await response.prepare(request)
        await response.write(b'{"cols": ["name"], "rows": [')
        await asyncio.sleep(5)
        return response

    crate = await fake_crate(stream_slowly)
    client = AsyncClient(servers=crate.url, pool_size=1)
    try:
        await _cancel_after(client.sql("SELECT 1"), 0.1)
        assert client.active_servers == [crate.url]
        # With a pool of one, this only works if the slot was released.
        assert await client.sql("SELECT 2") == SQL_RESULT
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_cancel_during_backoff(fake_crate, monkeypatch):
    crate = await fake_crate()

    async def refuse(self, *args, **kwargs):
        raise aiohttp.ConnectionTimeoutError("connect timed out")

    monkeypatch.setattr(AsyncServer, "request", refuse)
    client = AsyncClient(servers=crate.url, backoff_factor=10)
    try:
        await _cancel_after(client.sql("SELECT 1"), 0.1)
        assert client.active_servers == [crate.url]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_close_waits_for_in_flight_requests(fake_crate):
    async def handler(request):
        await asyncio.sleep(0.2)
        return web.json_response(SQL_RESULT)

    crate = await fake_crate(handler)
    client = AsyncClient(servers=crate.url, pool_size=1)
    running = asyncio.ensure_future(client.sql("SELECT 1"))
    queued = asyncio.ensure_future(client.sql("SELECT 2"))
    await asyncio.sleep(0.05)
    await client.close()
    assert running.done() and running.result() == SQL_RESULT
    assert queued.done() and queued.result() == SQL_RESULT
    assert client.closed
    with pytest.raises(exceptions.ProgrammingError, match="Client closed"):
        await client.sql("SELECT 3")
    # Idempotent.
    await client.close()


@pytest.mark.asyncio
async def test_cancelled_close_terminates(fake_crate):
    async def blocked(request):
        await asyncio.sleep(5)
        return web.json_response(SQL_RESULT)

    crate = await fake_crate(blocked)
    client = AsyncClient(servers=crate.url)
    request = asyncio.ensure_future(client.sql("SELECT 1"))
    await asyncio.sleep(0.05)
    await _cancel_after(client.close(), 0.05)
    session = client.server_pool[crate.url]._session
    assert session is not None and session.closed
    with pytest.raises(exceptions.Error):
        await request


@pytest.mark.asyncio
async def test_terminate(fake_crate):
    """
    `terminate()` relies on aiohttp's private `BaseConnector._close()`; this
    fails if an aiohttp release changes it.
    """
    crate = await fake_crate()
    client = AsyncClient(servers=crate.url)
    await client.sql("SELECT 1")
    session = client.server_pool[crate.url]._session
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client.terminate()
        assert session.closed
        assert client.closed
        del client, session
        gc.collect()
        await asyncio.sleep(0)
    assert [str(w.message) for w in caught] == []


@pytest.mark.asyncio
async def test_unclosed_client_warns(fake_crate):
    """
    Only a client that opened connections warns.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        unused = AsyncClient()
        del unused
        gc.collect()
    assert caught == []

    crate = await fake_crate()
    client = AsyncClient(servers=crate.url)
    await client.sql("SELECT 1")
    session = client.server_pool[crate.url]._session
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        del client
        gc.collect()
        await asyncio.sleep(0)
    assert [w.category for w in caught] == [ResourceWarning]
    assert "unclosed <AsyncClient" in str(caught[0].message)
    # The connections were closed, so aiohttp has nothing to warn about.
    assert session.closed


def test_different_event_loop():
    async def start():
        crate = await FakeCrate().start()
        client = AsyncClient(servers=crate.url)
        await client.sql("SELECT 1")
        return crate, client

    async def reuse(client):
        await client.sql("SELECT 1")

    loop = asyncio.new_event_loop()
    try:
        crate, client = loop.run_until_complete(start())
        with pytest.raises(
            exceptions.ProgrammingError, match="different event loop"
        ):
            asyncio.run(reuse(client))
        assert client.active_servers == [crate.url]
        loop.run_until_complete(client.close())
        loop.run_until_complete(crate.stop())
    finally:
        loop.close()


def _pooled_socket(client, url):
    connector = client.server_pool[url]._session.connector
    (protocol,) = [p for conns in connector._conns.values() for p, _ in conns]
    return protocol.transport.get_extra_info("socket")


@pytest.mark.asyncio
async def test_connections_are_reused(fake_crate):
    """
    A fully read response returns its connection to the pool.
    """
    peers = []

    async def handler(request):
        peers.append(request.transport.get_extra_info("peername"))
        return web.json_response(SQL_RESULT)

    crate = await fake_crate(handler)
    client = AsyncClient(servers=crate.url)
    try:
        for _ in range(5):
            await client.sql("SELECT 1")
        await asyncio.gather(*(client.sql("SELECT 1") for _ in range(3)))
        for _ in range(5):
            await client.sql("SELECT 1")
    finally:
        await client.close()
    assert len(peers) == 13
    assert len(set(peers)) == 3


@pytest.mark.asyncio
async def test_socket_keepalive(fake_crate):
    crate = await fake_crate()
    client = AsyncClient(
        servers=crate.url,
        socket_tcp_keepidle=33,
        socket_tcp_keepintvl=7,
        socket_tcp_keepcnt=4,
    )
    try:
        await client.sql("SELECT 1")
        sock = _pooled_socket(client, crate.url)
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
        assert sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
        options = keepalive_socket_options(True, 33, 7, 4)
        for level, option, value in options[1:]:
            assert sock.getsockopt(level, option) == value
    finally:
        await client.close()
