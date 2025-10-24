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

"""
Tests for serializing data, typically python objects
 into CrateDB-sql compatible structures.
"""
import datetime
import datetime as dt
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from crate.client.http import Client, json_dumps
from tests.conftest import REQUEST_PATH, fake_response


def test_data_is_serialized():
    """
    Verify that when a request is issued, `json_dumps` is called with
    the right parameters and that a requests gets the output from json_dumps,
    this verifies the entire serialization call chain, so in the following
    tests we can just test `json_dumps` and ignore
    `Client` altogether.
    """
    mock = MagicMock(spec=bytes)

    with patch('crate.client.http.json_dumps', return_value=mock) as f:
        with patch(REQUEST_PATH, return_value=fake_response(200)) as request:
            client = Client(servers="localhost:4200")
            client.sql(
                "insert into t (a, b) values (?, ?)",
                (datetime.datetime(2025, 10, 23, 11, ),
                 "ss"
                 )
            )

            # Verify json_dumps is called with the right parameters.
            f.assert_called_once_with(
                {
                    'stmt': 'insert into t (a, b) values (?, ?)',
                    'args': (datetime.datetime(2025, 10, 23, 11, 0), 'ss')
                }
            )

            # Verify that the output of json_dumps is used as
            # call argument for a request.
            assert request.call_args[1]['data'] is mock


def test_naive_datetime_serialization():
    """
    Verify that a `datetime.datetime` can be serialized.
    """
    data = dt.datetime(2015, 2, 28, 7, 31, 40)
    result = json_dumps(data)
    assert isinstance(result, bytes)
    assert result == b'1425108700000'


def test_aware_datetime_serialization():
    """
    Verify that a `datetime` that is tz aware type can be serialized.
    """
    data = dt.datetime.fromisoformat("2023-06-26T09:24:00.123+02:00")
    result = json_dumps(data)
    assert isinstance(result, bytes)
    assert result == b"1687764240123"


def test_decimal_serialization():
    """
    Verify that a `Decimal` type can be serialized.
    """

    data = Decimal(0.12)
    expected = b'"0.11999999999999999555910790149937383830547332763671875"'
    result = json_dumps(data)
    assert isinstance(result, bytes)

    # Question: Is this deterministic in every Python release?
    assert result == expected


def test_date_serialization():
    """
    Verify that a `datetime.date` can be serialized.
    """
    data = dt.date(2016, 4, 21)
    result = json_dumps(data)
    assert result == b'1461196800000'


def test_uuid_serialization():
    """
    Verify that a `uuid.UUID` can be serialized.

    We do not care about specific uuid versions, just the object that is
    re-used across all versions of the uuid module.
    """
    data = uuid.UUID(
        bytes=(50583033507982468033520929066863110751).to_bytes(16),
        version=4)
    result = json_dumps(data)
    assert result == b'"260df019-a183-431f-ad46-115ccdf12a5f"'
