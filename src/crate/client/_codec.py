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

import calendar
import datetime as dt
import typing as t
from decimal import Decimal

import orjson

epoch_aware = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
epoch_naive = dt.datetime(1970, 1, 1)


def json_encoder(obj: t.Any) -> t.Union[int, str]:
    """
    Encoder function for orjson, with additional type support.

    - Python's `Decimal` type will be serialized to `str`.
    - Python's `dt.datetime` and `dt.date` types will be
      serialized to `int` after converting to milliseconds
      since epoch.
    - Python's `dt.time` will be serialized to `str`, following
    the ISO format.

    https://github.com/ijl/orjson#default
    https://cratedb.com/docs/crate/reference/en/latest/general/ddl/data-types.html#type-timestamp
    """
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dt.datetime):
        if obj.tzinfo is not None:
            delta = obj - epoch_aware
        else:
            delta = obj - epoch_naive
        return int(
            delta.microseconds / 1000.0
            + (delta.seconds + delta.days * 24 * 3600) * 1000.0
        )
    if isinstance(obj, dt.time):
        return obj.isoformat()
    if isinstance(obj, dt.date):
        return calendar.timegm(obj.timetuple()) * 1000
    raise TypeError


def json_dumps(obj: t.Any) -> bytes:
    """
    Serialize to JSON format, using `orjson`, with additional type support.

    https://github.com/ijl/orjson
    """
    return orjson.dumps(
        obj,
        default=json_encoder,
        option=(
            orjson.OPT_PASSTHROUGH_DATETIME
            | orjson.OPT_NON_STR_KEYS
            | orjson.OPT_SERIALIZE_NUMPY
        ),
    )
