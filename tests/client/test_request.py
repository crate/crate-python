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

import gzip

import orjson
import pytest

from crate.client._request import (
    build_headers,
    compress_body,
    create_sql_payload,
)

STMT = b'{"stmt":"SELECT name FROM sys.cluster"}'
JWT = "eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJjcmF0ZWRiIn0.c2lnbmF0dXJl"


def test_build_headers_without_credentials():
    assert build_headers(None, STMT) == {
        "Content-Length": str(len(STMT)),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def test_build_headers_keeps_content_length():
    headers = build_headers({"Content-Length": "1024"}, STMT)
    assert headers["Content-Length"] == "1024"


def test_build_headers_without_body_length():
    assert "Content-Length" not in build_headers(None, None)


def test_build_headers_updates_given_dict():
    headers = {"Accept-Encoding": "gzip, deflate"}
    assert build_headers(headers, STMT) is headers
    assert headers["Accept-Encoding"] == "gzip, deflate"


@pytest.mark.parametrize(
    "password, authorization",
    [
        # base64 of "crate:"
        (None, "Basic Y3JhdGU6"),
        # base64 of "crate:s3cr3t"
        ("s3cr3t", "Basic Y3JhdGU6czNjcjN0"),
    ],
)
def test_build_headers_basic_auth(password, authorization):
    headers = build_headers(None, STMT, username="crate", password=password)
    assert headers["Authorization"] == authorization
    assert headers["X-User"] == "crate"


def test_build_headers_password_without_username():
    headers = build_headers(None, STMT, password="s3cr3t")
    assert "Authorization" not in headers
    assert "X-User" not in headers


def test_build_headers_jwt():
    headers = build_headers(None, STMT, jwt_token=JWT)
    assert headers["Authorization"] == f"Bearer {JWT}"
    assert "X-User" not in headers


def test_build_headers_jwt_and_username():
    with pytest.raises(ValueError, match="Either JWT tokens are accepted"):
        build_headers(None, STMT, username="crate", jwt_token=JWT)


@pytest.mark.parametrize(
    "credentials",
    [
        {"username": "crate", "password": "s3cr3t"},
        {"jwt_token": JWT},
    ],
)
def test_build_headers_existing_authorization_wins(credentials):
    headers = build_headers(
        {"Authorization": "Bearer from-caller"}, STMT, **credentials
    )
    assert headers["Authorization"] == "Bearer from-caller"


def test_build_headers_existing_x_user_wins():
    headers = build_headers({"X-User": "admin"}, STMT, username="crate")
    assert headers["X-User"] == "admin"


def test_build_headers_default_schema():
    headers = build_headers(None, STMT, schema="doc")
    assert headers["Default-Schema"] == "doc"


def test_build_headers_overrides_content_type():
    headers = build_headers(
        {"Accept": "text/plain", "Content-Type": "text/plain"}, STMT
    )
    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"


@pytest.mark.parametrize(
    "compress, compressed",
    [
        (True, True),
        (False, False),
        (len(STMT), True),
        (len(STMT) + 1, False),
        (0, True),
    ],
)
def test_compress_body(compress, compressed):
    data, is_compressed = compress_body(STMT, compress)
    assert is_compressed is compressed
    if compressed:
        assert gzip.decompress(data) == STMT
    else:
        assert data is STMT


@pytest.mark.parametrize(
    "args, bulk_args, expected",
    [
        (None, None, {"stmt": "INSERT INTO doc.t (x) VALUES (?)"}),
        (
            [1],
            None,
            {"stmt": "INSERT INTO doc.t (x) VALUES (?)", "args": [1]},
        ),
        (
            None,
            [[1], [2]],
            {
                "stmt": "INSERT INTO doc.t (x) VALUES (?)",
                "bulk_args": [[1], [2]],
            },
        ),
        ([], [], {"stmt": "INSERT INTO doc.t (x) VALUES (?)"}),
    ],
)
def test_create_sql_payload(args, bulk_args, expected):
    payload = create_sql_payload(
        "INSERT INTO doc.t (x) VALUES (?)", args, bulk_args
    )
    assert orjson.loads(payload) == expected


def test_create_sql_payload_stmt_not_a_string():
    with pytest.raises(ValueError, match="stmt is not a string"):
        create_sql_payload(b"SELECT 1", None, None)


def test_create_sql_payload_args_and_bulk_args():
    with pytest.raises(ValueError, match="Cannot provide both"):
        create_sql_payload("INSERT INTO doc.t (x) VALUES (?)", [1], [[1], [2]])
