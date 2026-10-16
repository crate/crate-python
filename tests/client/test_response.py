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

import orjson
import pytest

from crate.client import exceptions
from crate.client._response import (
    blob_del_result,
    blob_exists_result,
    blob_put_result,
    parse_server_infos,
    raise_for_status,
    redirect_target,
    should_preserve_server,
)

JSON = {"content-type": "application/json"}
TEXT = {"content-type": "text/plain"}
DIGEST = "c520e6109835c876fd98636efec43dd61634b7d3"


def sql_error(message, code=4000, error_trace=None):
    data = {"error": {"message": message, "code": code}}
    if error_trace is not None:
        data["error_trace"] = error_trace
    return orjson.dumps(data)


@pytest.mark.parametrize("status", [100, 200, 201, 204, 301, 307, 600])
def test_raise_for_status_no_error(status):
    assert raise_for_status(status, "", JSON, b"") is None


@pytest.mark.parametrize(
    "status, reason, message",
    [
        (400, "Bad Request", "400 Client Error: Bad Request"),
        (404, "Not Found", "404 Client Error: Not Found"),
        (500, "Internal Server Error", "500 Server Error: Internal Server"),
        (502, "Bad Gateway", "502 Server Error: Bad Gateway"),
    ],
)
def test_raise_for_status_without_json_body(status, reason, message):
    with pytest.raises(exceptions.ProgrammingError, match=message):
        raise_for_status(status, reason, TEXT, b"<html></html>")


@pytest.mark.parametrize("headers", [JSON, TEXT])
def test_raise_for_status_503(headers):
    with pytest.raises(
        exceptions.ConnectionError,
        match="503 Server Error: Service Unavailable",
    ):
        raise_for_status(503, "Service Unavailable", headers, b"")


def test_raise_for_status_sql_error():
    body = sql_error(
        "SQLParseException[line 1:1: mismatched input 'SELCT']",
        error_trace="io.crate.exceptions.SQLParseException: ...",
    )
    with pytest.raises(exceptions.ProgrammingError) as excinfo:
        raise_for_status(400, "Bad Request", JSON, body)
    assert type(excinfo.value) is exceptions.ProgrammingError
    assert excinfo.value.message == (
        "SQLParseException[line 1:1: mismatched input 'SELCT']"
    )
    assert excinfo.value.error_trace == (
        "io.crate.exceptions.SQLParseException: ..."
    )


def test_raise_for_status_error_as_string():
    body = orjson.dumps({"error": "No handler found for uri [/_sq]"})
    with pytest.raises(
        exceptions.ProgrammingError, match=r"No handler found for uri \[/_sq\]"
    ):
        raise_for_status(400, "Bad Request", JSON, body)


def test_raise_for_status_duplicate_key():
    body = sql_error(
        "DuplicateKeyException[A document with the same primary key "
        "exists already]",
        code=4091,
        error_trace="trace",
    )
    with pytest.raises(exceptions.IntegrityError) as excinfo:
        raise_for_status(409, "Conflict", JSON, body)
    assert excinfo.value.message.startswith("DuplicateKeyException[")
    assert excinfo.value.error_trace == "trace"


def test_raise_for_status_bulk_errors_are_joined():
    body = orjson.dumps(
        {
            "results": [
                {"rowcount": 1},
                {"rowcount": -2, "error_message": "first failed"},
                {"rowcount": -2, "error_message": "second failed"},
            ]
        }
    )
    with pytest.raises(exceptions.ProgrammingError) as excinfo:
        raise_for_status(400, "Bad Request", JSON, body)
    assert excinfo.value.message == "first failed\nsecond failed"


def test_raise_for_status_bulk_without_errors_uses_error():
    body = orjson.dumps(
        {"results": [{"rowcount": 1}], "error": {"message": "failed"}}
    )
    with pytest.raises(exceptions.ProgrammingError, match="^failed$"):
        raise_for_status(400, "Bad Request", JSON, body)


@pytest.mark.parametrize(
    "content, expected",
    [
        (
            {"name": "crate-1", "version": {"number": "6.1.2"}},
            ("http://localhost:4200", "crate-1", "6.1.2"),
        ),
        ({}, ("http://localhost:4200", None, "0.0.0")),
    ],
)
def test_parse_server_infos(content, expected):
    assert parse_server_infos("http://localhost:4200", content) == expected


@pytest.mark.parametrize(
    "status, expected", [(201, True), (409, False), (200, False)]
)
def test_blob_put_result(status, expected):
    assert blob_put_result(status, "", TEXT, b"", "myfiles", DIGEST) is (
        expected
    )


@pytest.mark.parametrize("status", [400, 404])
def test_blob_put_result_location_not_found(status):
    with pytest.raises(exceptions.BlobLocationNotFoundException):
        blob_put_result(status, "", TEXT, b"", "myfiles", DIGEST)


@pytest.mark.parametrize(
    "status, expected", [(204, True), (404, False), (200, False)]
)
def test_blob_del_result(status, expected):
    assert blob_del_result(status, "", TEXT, b"") is expected


@pytest.mark.parametrize(
    "status, expected", [(200, True), (404, False), (204, False)]
)
def test_blob_exists_result(status, expected):
    assert blob_exists_result(status, "", TEXT, b"") is expected


@pytest.mark.parametrize(
    "result", [blob_put_result, blob_del_result, blob_exists_result]
)
def test_blob_result_server_error(result):
    args = (500, "Internal Server Error", TEXT, b"")
    if result is blob_put_result:
        args += ("myfiles", DIGEST)
    with pytest.raises(exceptions.ProgrammingError, match="500 Server Error"):
        result(*args)


@pytest.mark.parametrize(
    "status, location, expected",
    [
        (307, "http://localhost:4201/_sql", "http://localhost:4201"),
        (301, "https://node2:4200/_blobs/x", "https://node2:4200"),
        (308, "http://localhost:4201/", "http://localhost:4201"),
        (307, None, None),
        (307, "", None),
        (200, False, None),
        (309, "http://localhost:4201/_sql", None),
    ],
)
def test_redirect_target(status, location, expected):
    assert redirect_target(status, location) == expected


@pytest.mark.parametrize(
    "ex, expected",
    [
        (Exception("reset", ConnectionResetError(104, "reset")), True),
        (Exception("broken", BrokenPipeError(32, "broken")), True),
        (Exception("refused", ConnectionRefusedError()), False),
        (Exception("Connection aborted."), False),
        (ConnectionResetError(104, "reset"), False),
    ],
)
def test_should_preserve_server(ex, expected):
    assert should_preserve_server(ex) is expected
