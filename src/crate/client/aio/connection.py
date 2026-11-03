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
import typing as t
import warnings

from verlib2 import Version

from crate.client._connection_base import ConnectionBase
from crate.client.aio._http import AsyncClient
from crate.client.aio.cursor import AsyncCursor


class AsyncConnection(ConnectionBase[AsyncCursor]):
    """
    Asynchronous connection. Experimental.
    """

    client: AsyncClient
    lowest_server_version: t.Optional[Version]

    @property
    def _cursor_class(self) -> t.Type[AsyncCursor]:
        return AsyncCursor

    def __init__(
        self,
        client: AsyncClient,
        converter: t.Any = None,
        time_zone: t.Any = None,
    ) -> None:
        super().__init__(converter=converter, time_zone=time_zone)
        self.client = client
        self.lowest_server_version = None

    @property
    def closed(self) -> bool:
        return self._closed

    async def commit(self) -> None:
        """
        Transactions are not supported, so ``commit`` is not implemented.
        """
        self._check_open()

    async def rollback(self) -> None:
        """
        Transactions are not supported, so ``rollback`` does nothing.
        """

    async def close(self) -> None:
        """
        Wait for in-flight requests, then close all connections.
        """
        if self._closed:
            return
        self._closed = True
        await self.client.close()

    def terminate(self) -> None:
        """
        Close all connections at once, without awaiting anything.
        """
        self._closed = True
        self.client.terminate()

    async def _lowest_server_version(self) -> Version:
        results = await asyncio.gather(
            *(
                self.client.server_infos(server)
                for server in self.client.active_servers
            ),
            return_exceptions=True,
        )
        return self._lowest_version(
            result if isinstance(result, BaseException) else result[2]
            for result in results
        )

    async def __aenter__(self) -> "AsyncConnection":
        return self

    async def __aexit__(self, *excs: object) -> None:
        await self.close()

    def __del__(self) -> None:
        if getattr(self, "_closed", True):
            return
        warnings.warn(
            f"unclosed {self!r}; close it with `await connection.close()`",
            ResourceWarning,
            stacklevel=2,
            source=self,
        )
        # Also keeps the client from warning a second time.
        self.terminate()


async def connect(
    servers: t.Union[str, t.Iterable[str], None] = None,
    timeout: t.Union[int, float, str, None] = None,
    backoff_factor: float = 0,
    client: t.Optional[AsyncClient] = None,
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
    converter: t.Any = None,
    time_zone: t.Any = None,
    jwt_token: t.Optional[str] = None,
    compress: t.Union[int, bool] = 8192,
) -> AsyncConnection:
    """
    Connect to CrateDB and ask every server for its version.
    """
    if client is None:
        client = AsyncClient(
            servers,
            timeout=timeout,
            backoff_factor=backoff_factor,
            verify_ssl_cert=verify_ssl_cert,
            ca_cert=ca_cert,
            error_trace=error_trace,
            cert_file=cert_file,
            key_file=key_file,
            ssl_relax_minimum_version=ssl_relax_minimum_version,
            username=username,
            password=password,
            schema=schema,
            pool_size=pool_size,
            socket_keepalive=socket_keepalive,
            socket_tcp_keepidle=socket_tcp_keepidle,
            socket_tcp_keepintvl=socket_tcp_keepintvl,
            socket_tcp_keepcnt=socket_tcp_keepcnt,
            jwt_token=jwt_token,
            compress=compress,
        )
    connection = AsyncConnection(
        client, converter=converter, time_zone=time_zone
    )
    try:
        connection.lowest_server_version = (
            await connection._lowest_server_version()
        )
    except BaseException:
        connection.terminate()
        raise
    return connection
