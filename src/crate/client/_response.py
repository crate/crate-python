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

import typing as t
from urllib.parse import urlparse

import orjson

from crate.client.exceptions import (
    BlobLocationNotFoundException,
    ConnectionError,
    IntegrityError,
    ProgrammingError,
)

SRV_UNAVAILABLE_STATUSES = {502, 503, 504, 509}
PRESERVE_ACTIVE_SERVER_EXCEPTIONS = {ConnectionResetError, BrokenPipeError}


def raise_for_status(
    status: int,
    reason: t.Optional[str],
    headers: t.Mapping[str, str],
    body: bytes,
) -> None:
    """
    Raise `IntegrityError` exceptions for `DuplicateKeyException` errors.
    """
    try:
        return _raise_for_status_real(status, reason, headers, body)
    except ProgrammingError as ex:
        if "DuplicateKeyException" in ex.message:
            raise IntegrityError(ex.message, error_trace=ex.error_trace) from ex
        raise


def _raise_for_status_real(
    status: int,
    reason: t.Optional[str],
    headers: t.Mapping[str, str],
    body: bytes,
) -> None:
    """make sure that only crate.exceptions are raised that are defined in
    the DB-API specification"""
    message = ""
    if 400 <= status < 500:
        message = "%s Client Error: %s" % (status, reason)
    elif 500 <= status < 600:
        message = "%s Server Error: %s" % (status, reason)
    else:
        return
    if status == 503:
        raise ConnectionError(message)
    if headers.get("content-type", "").startswith("application/json"):
        data = orjson.loads(body)
        error = data.get("error", {})
        error_trace = data.get("error_trace", None)
        if "results" in data:
            errors = [
                res["error_message"]
                for res in data["results"]
                if res.get("error_message")
            ]
            if errors:
                raise ProgrammingError("\n".join(errors))
        if isinstance(error, dict):
            raise ProgrammingError(
                error.get("message", ""), error_trace=error_trace
            )
        raise ProgrammingError(error, error_trace=error_trace)
    raise ProgrammingError(message)


def parse_server_infos(
    server: str, content: t.Dict[str, t.Any]
) -> t.Tuple[str, t.Optional[str], str]:
    node_name = content.get("name")
    node_version = content.get("version", {}).get("number", "0.0.0")
    return server, node_name, node_version


def blob_put_result(
    status: int,
    reason: t.Optional[str],
    headers: t.Mapping[str, str],
    body: bytes,
    table: str,
    digest: str,
) -> bool:
    if status == 201:
        # blob created
        return True
    if status == 409:
        # blob exists
        return False
    if status in (400, 404):
        raise BlobLocationNotFoundException(table, digest)
    raise_for_status(status, reason, headers, body)
    return False


def blob_del_result(
    status: int,
    reason: t.Optional[str],
    headers: t.Mapping[str, str],
    body: bytes,
) -> bool:
    if status == 204:
        return True
    if status == 404:
        return False
    raise_for_status(status, reason, headers, body)
    return False


def blob_exists_result(
    status: int,
    reason: t.Optional[str],
    headers: t.Mapping[str, str],
    body: bytes,
) -> bool:
    if status == 200:
        return True
    elif status == 404:
        return False
    raise_for_status(status, reason, headers, body)
    return False


def redirect_target(
    status: int, location: t.Union[str, None, t.Literal[False]]
) -> t.Optional[str]:
    """
    Return the server to follow a redirect to, as ``scheme://netloc``.
    """
    if location and 300 <= status <= 308:
        redirect_url = urlparse(location)
        return f"{redirect_url.scheme}://{redirect_url.netloc}"
    return None


def should_preserve_server(ex: BaseException) -> bool:
    return any(
        t in [type(arg) for arg in ex.args]
        for t in PRESERVE_ACTIVE_SERVER_EXCEPTIONS
    )
