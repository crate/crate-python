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
import logging
import socket
import ssl
import sys
import typing as t
import warnings
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit

import aiohttp
import urllib3
from yarl import URL

from crate.client._options import (
    SQL_PATH,
    credentials_from_url,
    keepalive_socket_options,
    sql_path,
    to_server_list,
    validate_compress,
)
from crate.client._pool import _ServerPool
from crate.client._request import (
    build_headers,
    compress_body,
    create_sql_payload,
)
from crate.client._response import (
    MAX_REDIRECTS,
    SRV_UNAVAILABLE_STATUSES,
    parse_server_infos,
    raise_for_status,
    redirect_target,
)
from crate.client._tls import make_ssl_context
from crate.client.exceptions import ConnectionError, ProgrammingError
from crate.client.http import _ex_to_message, _json_from_response

logger = logging.getLogger("crate.client.aio")

DEFAULT_POOL_SIZE = 20
CONNECT_RETRIES = 10
BACKOFF_MAX = 120.0

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

# Work around the CPython SSL transport leak, as aiohttp recommends.
_ENABLE_CLEANUP_CLOSED = sys.version_info < (3, 12, 7) or sys.version_info[
    :3
] == (3, 13, 0)

_CONNECT_ERRORS = (aiohttp.ClientConnectorError, aiohttp.ConnectionTimeoutError)
_TRANSPORT_ERRORS = (
    aiohttp.ClientError,
    TimeoutError,
    asyncio.TimeoutError,
    ssl.SSLError,
    ConnectionResetError,
    BrokenPipeError,
)


def _is_stale_connection(ex: BaseException) -> bool:
    """
    Whether the server closed a keep-alive connection while it was idle.
    """
    if isinstance(
        ex,
        (
            aiohttp.ServerDisconnectedError,
            ConnectionResetError,
            BrokenPipeError,
        ),
    ):
        return True
    return isinstance(ex, aiohttp.ClientOSError) and ex.errno in (
        errno.ECONNRESET,
        errno.EPIPE,
    )


def backoff_time(backoff_factor: float, errors: int) -> float:
    """
    Seconds to wait before the next attempt after `errors`
    """
    if errors <= 1:
        return 0.0
    return min(BACKOFF_MAX, backoff_factor * (2 ** (errors - 1)))


def client_timeout(timeout: t.Any) -> aiohttp.ClientTimeout:
    """
    Map the `timeout` option to aiohttp

    """
    if isinstance(timeout, urllib3.Timeout):
        raise TypeError(
            "The async client does not support urllib3.Timeout; "
            "pass the timeout in seconds as a number"
        )
    if timeout is None:
        # aiohttp's default is `total=300, sock_connect=30`.
        return aiohttp.ClientTimeout(
            total=None, connect=None, sock_connect=None, sock_read=None
        )
    if isinstance(timeout, str):
        timeout = float(timeout)
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool):
        raise TypeError(f"timeout must be a number of seconds, got {timeout!r}")
    return aiohttp.ClientTimeout(
        total=None, connect=None, sock_connect=timeout, sock_read=timeout
    )


def _socket_factory(
    options: t.List[t.Tuple[int, int, int]],
) -> t.Callable[[t.Any], socket.socket]:
    """
    Create sockets with `TCP_NODELAY` and the keepalive options.
    """

    def factory(addr_info: t.Any) -> socket.socket:
        family, type_, proto, _, _ = addr_info
        sock = socket.socket(family=family, type=type_, proto=proto)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            for level, option, value in options:
                sock.setsockopt(level, option, value)
        except OSError:
            sock.close()
            raise
        return sock

    return factory


@dataclass(frozen=True)
class _Response:
    """
    A fully read response.
    """

    status: int
    reason: t.Optional[str]
    headers: t.Mapping[str, str]
    data: bytes
    location: t.Optional[str]

    async def aclose(self) -> None:
        pass


class _StreamedResponse:
    """
    A response whose body has not been read yet.
    """

    def __init__(
        self,
        response: aiohttp.ClientResponse,
        location: t.Optional[str],
        release: t.Callable[[], None],
    ) -> None:
        self.status = response.status
        self.reason = response.reason
        self.headers = response.headers
        self.location = location
        self._response = response
        self._release = release
        self._closed = False

    async def read(self) -> bytes:
        return await self._response.read()

    def iter_chunked(self, size: int) -> t.AsyncIterator[bytes]:
        return self._response.content.iter_chunked(size)

    def close(self) -> None:
        """
        Close the response without awaiting anything.
        """
        if self._closed:
            return
        self._closed = True
        try:
            self._response.close()
        finally:
            self._release()

    async def aclose(self) -> None:
        self.close()


class AsyncServer:
    """
    One CrateDB server: an aiohttp session with its own connection pool.
    """

    def __init__(
        self,
        server: str,
        *,
        ssl_context: t.Optional[ssl.SSLContext],
        timeout: aiohttp.ClientTimeout,
        pool_size: int,
        socket_options: t.List[t.Tuple[int, int, int]],
    ) -> None:
        self.server = server
        self.path_prefix = ""
        try:
            parsed_url = urlsplit(server)
        except Exception as e:
            parsed_url = SplitResult("", "", "", "", "")
            logger.warning(
                "Unable to extract path prefix from server url: %s", e
            )
        if parsed_url.path:
            self.path_prefix = parsed_url.path.strip("/")
        # Userinfo is sent as headers by `build_headers`. aiohttp would turn
        # it into a second, conflicting `Authorization` header.
        self._origin = str(URL(server).origin())
        # TLS settings are ignored for `http://` servers, as in sync.
        self._ssl = ssl_context if server.lower().startswith("https") else None
        self._timeout = timeout
        self._pool_size = pool_size
        self._socket_options = socket_options
        self._session: t.Optional[aiohttp.ClientSession] = None
        self._loop: t.Optional[asyncio.AbstractEventLoop] = None
        self._slots: t.Optional[asyncio.Semaphore] = None
        self._in_flight = 0
        self._idle: t.Optional[asyncio.Event] = None
        self._closed = False

    def _get_session(self) -> aiohttp.ClientSession:
        loop = asyncio.get_running_loop()
        if self._closed:
            raise ProgrammingError("Client closed")
        if self._session is None:
            connector = aiohttp.TCPConnector(
                limit=self._pool_size,
                limit_per_host=self._pool_size,
                ssl=self._ssl if self._ssl is not None else True,
                enable_cleanup_closed=_ENABLE_CLEANUP_CLOSED,
                socket_factory=(
                    _socket_factory(self._socket_options)
                    if self._socket_options
                    else None
                ),
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self._timeout,
                auto_decompress=True,
                trust_env=False,
                cookie_jar=aiohttp.DummyCookieJar(),
            )
            self._loop = loop
            self._slots = asyncio.Semaphore(self._pool_size)
            self._idle = asyncio.Event()
            self._idle.set()
        elif loop is not self._loop:
            raise ProgrammingError(
                "AsyncConnection used from a different event loop than it "
                "was created in"
            )
        return self._session

    async def _acquire(self) -> None:
        """
        Wait for a free connection, in arrival order.
        """
        if self._slots is None or self._idle is None:
            raise RuntimeError("No session; call _get_session() first")
        self._in_flight += 1
        self._idle.clear()
        try:
            await self._slots.acquire()
        except BaseException:
            self._done()
            raise

    def _release(self) -> None:
        if self._slots is None:
            return
        self._slots.release()
        self._done()

    def _done(self) -> None:
        self._in_flight -= 1
        if not self._in_flight and self._idle is not None:
            self._idle.set()

    def _url(self, path: str) -> URL:
        if self.path_prefix:
            path = "/{path_prefix}/{path}".format(
                path_prefix=self.path_prefix, path=path.strip("/")
            )
        return URL(self._origin + path, encoded=True)

    async def open(
        self,
        method: str,
        path: str,
        data: t.Any = None,
        headers: t.Optional[t.Dict[str, str]] = None,
        username: t.Optional[str] = None,
        password: t.Optional[str] = None,
        schema: t.Optional[str] = None,
        jwt_token: t.Optional[str] = None,
    ) -> _StreamedResponse:
        """
        Send a request and return the response before reading its body.
        """
        headers = build_headers(
            headers,
            data,
            username=username,
            password=password,
            schema=schema,
            jwt_token=jwt_token,
        )
        session = self._get_session()
        await self._acquire()
        try:
            resp = await session.request(
                method,
                self._url(path),
                data=data,
                headers=headers,
                allow_redirects=False,
            )
        except BaseException:
            self._release()
            raise
        location = (
            resp.headers.get("Location")
            if resp.status in _REDIRECT_STATUSES
            else None
        )
        return _StreamedResponse(resp, location, self._release)

    async def request(
        self,
        method: str,
        path: str,
        data: t.Any = None,
        headers: t.Optional[t.Dict[str, str]] = None,
        username: t.Optional[str] = None,
        password: t.Optional[str] = None,
        schema: t.Optional[str] = None,
        jwt_token: t.Optional[str] = None,
    ) -> _Response:
        """
        Send a request and read its body.
        """
        response = await self.open(
            method,
            path,
            data=data,
            headers=headers,
            username=username,
            password=password,
            schema=schema,
            jwt_token=jwt_token,
        )
        try:
            body = await response.read()
        finally:
            response.close()
        return _Response(
            status=response.status,
            reason=response.reason,
            headers=response.headers,
            data=body,
            location=response.location,
        )

    async def close(self) -> None:
        """
        Wait for in-flight requests, then close the connection pool.
        """
        if self._closed:
            return
        self._closed = True
        try:
            if self._idle is not None:
                await self._idle.wait()
            if self._session is not None:
                await self._session.close()
        except BaseException:
            self.terminate()
            raise

    def terminate(self) -> None:
        """
        Close all connections at once, without awaiting anything.
        """
        self._closed = True
        session = self._session
        if session is None or session.closed:
            return
        connector = session.connector
        if connector is not None:
            # The public `close()` returns an awaitable that warns when it
            # is not awaited. `_close()` closes the transports synchronously.
            connector._close(abort_ssl=True)

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def is_open(self) -> bool:
        """
        Whether the server has a session that was not closed yet.
        """
        return (
            self._session is not None
            and not self._closed
            and not self._session.closed
        )


class AsyncClient(_ServerPool):
    """
    Asynchronous CrateDB HTTP client. Experimental.

    It takes the same arguments as `crate.client.http.Client`, except that
    `timeout` must be a number of seconds.
    """

    SQL_PATH = SQL_PATH
    """Crate URI path for issuing SQL statements."""

    default_server = "http://127.0.0.1:4200"
    """Default server to use if no servers are given on instantiation."""

    connect_retries = CONNECT_RETRIES
    """Connection attempts per server and request after the first one."""

    _logger = logger

    def __init__(
        self,
        servers: t.Union[str, t.Iterable[str], None] = None,
        timeout: t.Union[int, float, str, None] = None,
        backoff_factor: float = 0,
        verify_ssl_cert: bool = True,
        ca_cert: t.Optional[str] = None,
        error_trace: bool = False,
        cert_file: t.Optional[str] = None,
        key_file: t.Optional[str] = None,
        ssl_relax_minimum_version: bool = False,
        username: t.Optional[str] = None,
        password: t.Optional[str] = None,
        schema: t.Optional[str] = None,
        pool_size: t.Optional[int] = None,
        socket_keepalive: bool = True,
        socket_tcp_keepidle: t.Optional[int] = None,
        socket_tcp_keepintvl: t.Optional[int] = None,
        socket_tcp_keepcnt: t.Optional[int] = None,
        jwt_token: t.Optional[str] = None,
        compress: t.Union[int, bool] = 8192,
    ) -> None:
        server_list = (
            to_server_list(servers) if servers else [self.default_server]
        )

        if server_list and not username:
            try:
                username, password = credentials_from_url(
                    server_list[0], username, password
                )
            except Exception as ex:
                logger.warning(
                    "Unable to decode credentials from database "
                    "URI, so connecting to CrateDB without "
                    "authentication: {ex}".format(ex=ex)
                )

        super().__init__(server_list)
        self._timeout = client_timeout(timeout)
        self._ssl_context = make_ssl_context(
            verify_ssl_cert,
            ca_cert,
            cert_file,
            key_file,
            ssl_relax_minimum_version,
        )
        self._pool_size = (
            int(pool_size) if pool_size is not None else DEFAULT_POOL_SIZE
        )
        self._socket_options = keepalive_socket_options(
            socket_keepalive,
            socket_tcp_keepidle,
            socket_tcp_keepintvl,
            socket_tcp_keepcnt,
        )
        self.backoff_factor = backoff_factor
        self.server_pool: t.Dict[str, AsyncServer] = {}
        for server in server_list:
            self._create_server(server)
        self.username = username
        self.password = password
        self.jwt_token = jwt_token
        self.schema = schema
        self.compress = validate_compress(compress)
        self.path = sql_path(error_trace, self.SQL_PATH)

    def _create_server(self, server: str) -> None:
        self.server_pool[server] = AsyncServer(
            server,
            ssl_context=self._ssl_context,
            timeout=self._timeout,
            pool_size=self._pool_size,
            socket_options=self._socket_options,
        )

    def _add_server(self, server: str) -> None:
        with self._lock:
            if server not in self.server_pool:
                self._create_server(server)

    async def close(self) -> None:
        """
        Wait for in-flight requests, then close all connections.
        """
        await asyncio.gather(
            *(server.close() for server in self.server_pool.values())
        )

    def terminate(self) -> None:
        """
        Close all connections at once, without awaiting anything. Safe to
        call from `__del__`.
        """
        for server in list(self.server_pool.values()):
            server.terminate()

    @property
    def closed(self) -> bool:
        return all(server.closed for server in self.server_pool.values())

    async def sql(
        self,
        stmt: t.Optional[str],
        parameters: t.Any = None,
        bulk_parameters: t.Any = None,
    ) -> t.Any:
        """
        Execute SQL stmt against the crate server.
        """
        if stmt is None:
            return None

        data = create_sql_payload(stmt, parameters, bulk_parameters)
        logger.debug("Sending request to %s with payload: %s", self.path, data)
        content = await self._json_request("POST", self.path, data=data)
        logger.debug("JSON response for stmt(%s): %s", stmt, content)
        return content

    async def server_infos(self, server: str) -> t.Tuple[str, t.Any, str]:
        response = await self._request("GET", "/", server=server)
        raise_for_status(
            response.status, response.reason, response.headers, response.data
        )
        return parse_server_infos(server, _json_from_response(response))

    async def _json_request(self, method: str, path: str, data: bytes) -> t.Any:
        """
        Issue request against the crate HTTP API.
        """
        headers = {"Accept-Encoding": "gzip, deflate"}
        data, compressed = compress_body(data, self.compress)
        if compressed:
            headers["Content-Encoding"] = "gzip"

        response = await self._request(method, path, data=data, headers=headers)
        raise_for_status(
            response.status, response.reason, response.headers, response.data
        )
        if len(response.data) > 0:
            return _json_from_response(response)
        return response.data

    async def _send(
        self,
        server: str,
        method: str,
        path: str,
        stream: bool = False,
        **kwargs: t.Any,
    ) -> t.Union[_Response, _StreamedResponse]:
        """
        Send one request to `server`.
        """
        target = self.server_pool[server]
        send = target.open if stream else target.request
        errors = 0
        stale_retried = False
        while True:
            try:
                return await send(
                    method,
                    path,
                    username=self.username,
                    password=self.password,
                    schema=self.schema,
                    jwt_token=self.jwt_token,
                    **kwargs,
                )
            except _CONNECT_ERRORS:
                errors += 1
                if errors > self.connect_retries:
                    raise
                await asyncio.sleep(backoff_time(self.backoff_factor, errors))
            except _TRANSPORT_ERRORS as ex:
                if stale_retried or not _is_stale_connection(ex):
                    raise
                stale_retried = True

    async def _request(
        self,
        method: str,
        path: str,
        server: t.Optional[str] = None,
        _redirects: int = 0,
        **kwargs: t.Any,
    ) -> t.Any:
        """Execute a request to the cluster

        A server is selected from the server pool.
        """
        while True:
            next_server = server or self._get_server()
            try:
                response = await self._send(next_server, method, path, **kwargs)
                redirect_server = redirect_target(
                    response.status, response.location
                )
                if redirect_server is not None:
                    await response.aclose()
                    if _redirects >= MAX_REDIRECTS:
                        raise ProgrammingError(
                            f"Exceeded {MAX_REDIRECTS} redirects, last "
                            f"redirect to {redirect_server}"
                        )
                    self._add_server(redirect_server)
                    return await self._request(
                        method,
                        path,
                        server=redirect_server,
                        _redirects=_redirects + 1,
                        **kwargs,
                    )
                if not server and response.status in SRV_UNAVAILABLE_STATUSES:
                    await response.aclose()
                    with self._lock:
                        # drop server from active ones
                        self._drop_server(next_server, response.reason or "")
                else:
                    return response
            except _TRANSPORT_ERRORS as ex:
                ex_message = _ex_to_message(ex)
                if server:
                    raise ConnectionError(
                        "Server not available, exception: %s" % ex_message
                    ) from ex
                with self._lock:
                    # drop server from active ones
                    self._drop_server(next_server, ex_message)
            except Exception as e:
                raise ProgrammingError(_ex_to_message(e)) from e

    def __repr__(self) -> str:
        return "<AsyncClient {0}>".format(str(self._active_servers))

    def __del__(self) -> None:
        servers = getattr(self, "server_pool", None)
        if not servers or not any(s.is_open for s in servers.values()):
            return
        warnings.warn(
            f"unclosed {self!r}; close it with `await client.close()`",
            ResourceWarning,
            stacklevel=2,
            source=self,
        )
        self.terminate()
