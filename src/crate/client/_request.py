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
import io
import os
import typing as t
from base64 import b64encode

from crate.client._codec import json_dumps


def super_len(o: t.Any) -> t.Optional[int]:
    if hasattr(o, "__len__"):
        return len(o)
    if hasattr(o, "len"):
        return o.len
    if hasattr(o, "fileno"):
        try:
            fileno = o.fileno()
        except io.UnsupportedOperation:
            pass
        else:
            return os.fstat(fileno).st_size
    if hasattr(o, "getvalue"):
        # e.g. BytesIO, cStringIO.StringI
        return len(o.getvalue())
    return None


def build_headers(
    headers: t.Optional[t.Dict[str, str]],
    data: t.Any,
    username: t.Optional[str] = None,
    password: t.Optional[str] = None,
    schema: t.Optional[str] = None,
    jwt_token: t.Optional[str] = None,
) -> t.Dict[str, str]:
    """
    Add the length, authentication, schema and content type headers.

    A given `headers` dict is updated in place and returned.
    """
    if headers is None:
        headers = {}
    if "Content-Length" not in headers:
        length = super_len(data)
        if length is not None:
            headers["Content-Length"] = str(length)

    # Sanity checks.
    if jwt_token is not None and username is not None:
        raise ValueError(
            "Either JWT tokens are accepted, or user credentials, but not both"
        )

    # Authentication token
    if jwt_token is not None and "Authorization" not in headers:
        headers["Authorization"] = "Bearer %s" % jwt_token

    # Authentication credentials
    if username is not None:
        if "Authorization" not in headers and username is not None:
            credentials = username + ":"
            if password is not None:
                credentials += password
            headers["Authorization"] = "Basic %s" % b64encode(
                credentials.encode("utf-8")
            ).decode("utf-8")
        # For backwards compatibility with Crate <= 2.2
        if "X-User" not in headers:
            headers["X-User"] = username

    if schema is not None:
        headers["Default-Schema"] = schema
    headers["Accept"] = "application/json"
    headers["Content-Type"] = "application/json"
    return headers


def compress_body(
    data: bytes, compress: t.Union[int, bool]
) -> t.Tuple[bytes, bool]:
    """
    Return the request body to send and whether it is gzip-compressed.

    `compress` is either a flag, or the body size in bytes from which on
    to compress.
    """
    compress_enabled = compress is True or (
        not isinstance(compress, bool) and len(data) >= compress
    )
    if compress_enabled:
        return gzip.compress(data, compresslevel=6), True
    return data, False


def create_sql_payload(
    stmt: str,
    args: t.Optional[t.Union[t.List, t.Tuple, t.Dict]],
    bulk_args: t.Optional[t.List],
) -> bytes:
    if not isinstance(stmt, str):
        raise ValueError("stmt is not a string")
    if args and bulk_args:
        raise ValueError("Cannot provide both: args and bulk_args")

    data: t.Dict[str, t.Any] = {"stmt": stmt}
    if args:
        data["args"] = args
    if bulk_args:
        data["bulk_args"] = bulk_args
    return json_dumps(data)
