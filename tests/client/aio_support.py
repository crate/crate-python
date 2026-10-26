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
import socket
import ssl
import typing as t

import pytest

pytest.importorskip("aiohttp")

import pytest_asyncio  # noqa: E402
from aiohttp import web  # noqa: E402

from .settings import assets_path  # noqa: E402

SQL_RESULT = {"cols": ["name"], "rows": [["crate"]], "rowcount": 1}

Handler = t.Callable[[web.Request], t.Awaitable[web.StreamResponse]]


def server_ssl_context() -> ssl.SSLContext:
    """
    The TLS context of the test server certificate.
    """
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(assets_path("pki/server_valid.pem"))
    return context


class FakeCrate:
    """
    An in-process HTTP server.
    """

    def __init__(
        self,
        handler: t.Optional[Handler] = None,
        ssl_context: t.Optional[ssl.SSLContext] = None,
    ):
        self.handler = handler or self.ok
        self.ssl_context = ssl_context
        self.requests: t.List[t.Tuple[web.Request, bytes]] = []
        self.runner: t.Optional[web.AppRunner] = None
        self.port = 0
        self.url = ""

    @staticmethod
    async def ok(request: web.Request) -> web.StreamResponse:
        if request.path == "/":
            return web.json_response(
                {"name": "crate-1", "version": {"number": "6.1.2"}}
            )
        return web.json_response(SQL_RESULT)

    async def _dispatch(self, request: web.Request) -> web.StreamResponse:
        body = await request.read()
        self.requests.append((request, body))
        return await self.handler(request)

    async def start(self) -> "FakeCrate":
        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", self._dispatch)
        self.runner = web.AppRunner(
            app, handle_signals=False, shutdown_timeout=0.1
        )
        await self.runner.setup()
        site = web.TCPSite(
            self.runner, "127.0.0.1", 0, ssl_context=self.ssl_context
        )
        await site.start()
        self.port = site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
        if self.ssl_context:
            self.url = f"https://localhost:{self.port}"
        else:
            self.url = f"http://127.0.0.1:{self.port}"
        return self

    async def stop(self) -> None:
        if self.runner is not None:
            await self.runner.cleanup()


class SilentFirstProxy:
    """
    A TCP proxy that accepts the first connection and never answers it.
    """

    def __init__(self, target_port: int):
        self.target_port = target_port
        self.connections = 0
        self.port = 0
        self._server: t.Optional[asyncio.Server] = None
        self._writers: t.List[asyncio.StreamWriter] = []
        self._tasks: t.Set[asyncio.Task] = set()

    async def start(self) -> "SilentFirstProxy":
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]
        return self

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self.connections += 1
        self._writers.append(writer)
        if self.connections == 1:
            return
        upstream_reader, upstream_writer = await asyncio.open_connection(
            "127.0.0.1", self.target_port
        )
        self._writers.append(upstream_writer)
        for src, dst in ((reader, upstream_writer), (upstream_reader, writer)):
            task = asyncio.ensure_future(self._pipe(src, dst))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    @staticmethod
    async def _pipe(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while data := await reader.read(65536):
                writer.write(data)
                await writer.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            writer.close()

    async def stop(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        for writer in self._writers:
            writer.close()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()


@pytest_asyncio.fixture
async def fake_crate():
    """
    Start in-process CrateDB stand-ins.
    """
    servers: t.List[FakeCrate] = []

    async def start(
        handler: t.Optional[Handler] = None,
        ssl_context: t.Optional[ssl.SSLContext] = None,
    ) -> FakeCrate:
        server = await FakeCrate(handler, ssl_context).start()
        servers.append(server)
        return server

    yield start
    for server in servers:
        await server.stop()


def unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
