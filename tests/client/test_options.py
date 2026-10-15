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

import socket

import pytest

from crate.client._options import (
    credentials_from_url,
    keepalive_socket_options,
    server_url,
    sql_path,
    to_server_list,
    validate_compress,
)


@pytest.mark.parametrize(
    "server, expected",
    [
        ("a", "http://a"),
        ("a/path", "http://a/path"),
        ("a:9345", "http://a:9345"),
        ("a:9345/path", "http://a:9345/path"),
        ("https://a:9345", "https://a:9345"),
        ("https://a:9345/path", "https://a:9345/path"),
        ("https://a", "https://a"),
        ("https://a/path", "https://a/path"),
        ("HTTPS://a", "https://a"),
        ("demo.crate.io", "http://demo.crate.io"),
    ],
)
def test_server_url(server, expected):
    assert server_url(server) == expected


@pytest.mark.parametrize(
    "servers",
    [
        "localhost:4200 https://localhost:4201",
        ["localhost:4200", "https://localhost:4201"],
        ("localhost:4200", "https://localhost:4201"),
    ],
)
def test_to_server_list(servers):
    assert to_server_list(servers) == [
        "http://localhost:4200",
        "https://localhost:4201",
    ]


@pytest.mark.parametrize(
    "url, username, password, expected",
    [
        ("http://localhost:4200", None, None, (None, None)),
        ("http://crate@localhost:4200", None, None, ("crate", None)),
        (
            "http://crate:s3cr3t@localhost:4200",
            None,
            None,
            ("crate", "s3cr3t"),
        ),
        ("http://localhost:4200", None, "s3cr3t", (None, "s3cr3t")),
        ("http://crate@localhost:4200", None, "s3cr3t", ("crate", "s3cr3t")),
        (
            "http://crate:from-url@localhost:4200",
            None,
            "s3cr3t",
            ("crate", "from-url"),
        ),
        ("http://localhost:4200", "", None, ("", None)),
    ],
)
def test_credentials_from_url(url, username, password, expected):
    assert credentials_from_url(url, username, password) == expected


@pytest.mark.parametrize("compress", [True, False, 0, 8192])
def test_validate_compress(compress):
    assert validate_compress(compress) is compress


@pytest.mark.parametrize(
    "compress, type_name", [("8192", "'str'"), (None, "'NoneType'")]
)
def test_validate_compress_invalid(compress, type_name):
    with pytest.raises(
        TypeError, match=f"compress must be bool or int, got {type_name}"
    ):
        validate_compress(compress)


@pytest.mark.parametrize(
    "error_trace, expected",
    [
        (False, "/_sql?types=true"),
        (True, "/_sql?types=true&error_trace=true"),
    ],
)
def test_sql_path(error_trace, expected):
    assert sql_path(error_trace) == expected


def test_sql_path_with_given_path():
    assert sql_path(True, "/_sql") == "/_sql&error_trace=true"


def test_keepalive_socket_options_off():
    assert keepalive_socket_options(False, 30, 10, 5) == []


def test_keepalive_socket_options_defaults():
    assert keepalive_socket_options() == [
        (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    ]


@pytest.mark.skipif(
    not all(
        hasattr(socket, name)
        for name in ("TCP_KEEPIDLE", "TCP_KEEPINTVL", "TCP_KEEPCNT")
    ),
    reason="Platform does not support all TCP keepalive options",
)
def test_keepalive_socket_options_tcp():
    assert keepalive_socket_options(True, 30, 10, 5) == [
        (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
        (socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30),
        (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10),
        (socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5),
    ]
