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

import re
import socket
import typing as t
from urllib.parse import urlparse

SQL_PATH = "/_sql?types=true"

_HTTP_PAT = re.compile("https?://.+", re.I)


def server_url(server: str) -> str:
    """
    Normalizes a given server string to an url

    >>> print(server_url('a'))
    http://a
    >>> print(server_url('a/path'))
    http://a/path
    >>> print(server_url('a:9345'))
    http://a:9345
    >>> print(server_url('a:9345/path'))
    http://a:9345/path
    >>> print(server_url('https://a:9345'))
    https://a:9345
    >>> print(server_url('https://a:9345/path'))
    https://a:9345/path
    >>> print(server_url('https://a'))
    https://a
    >>> print(server_url('https://a/path'))
    https://a/path
    >>> print(server_url('demo.crate.io'))
    http://demo.crate.io
    """
    if not _HTTP_PAT.match(server):
        server = "http://%s" % server
    parsed = urlparse(server)
    return parsed.geturl()


def to_server_list(servers: t.Union[str, t.Iterable[str]]) -> t.List[str]:
    if isinstance(servers, str):
        servers = servers.split()
    return [server_url(s) for s in servers]


def credentials_from_url(
    url: str, username: t.Optional[str], password: t.Optional[str]
) -> t.Tuple[t.Optional[str], t.Optional[str]]:
    """
    Return the user name and password from the userinfo of `url`, falling
    back to the given ones for the parts the URL does not contain.
    """
    parsed = urlparse(url)
    if parsed.username is not None:
        username = parsed.username
    if parsed.password is not None:
        password = parsed.password
    return username, password


def validate_compress(compress: t.Any) -> t.Union[int, bool]:
    if not isinstance(compress, (bool, int)):
        raise TypeError(
            f"compress must be bool or int, got {type(compress).__name__!r}"
        )
    return compress


def sql_path(error_trace: bool, path: str = SQL_PATH) -> str:
    if error_trace:
        path += "&error_trace=true"
    return path


def keepalive_socket_options(
    keepalive: bool = True,
    tcp_keepidle: t.Optional[int] = None,
    tcp_keepintvl: t.Optional[int] = None,
    tcp_keepcnt: t.Optional[int] = None,
) -> t.List[t.Tuple[int, int, int]]:
    """
    Return the `setsockopt` arguments for TCP keepalive, or an empty list
    when `keepalive` is off.
    """
    if not keepalive:
        return []

    # always use TCP keepalive
    opts = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]

    # hasattr check because some options depend on system capabilities
    # see https://docs.python.org/3/library/socket.html#socket.SOMAXCONN
    if hasattr(socket, "TCP_KEEPIDLE") and tcp_keepidle is not None:
        opts.append((socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, tcp_keepidle))
    if hasattr(socket, "TCP_KEEPINTVL") and tcp_keepintvl is not None:
        opts.append((socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, tcp_keepintvl))
    if hasattr(socket, "TCP_KEEPCNT") and tcp_keepcnt is not None:
        opts.append((socket.IPPROTO_TCP, socket.TCP_KEEPCNT, tcp_keepcnt))
    return opts
