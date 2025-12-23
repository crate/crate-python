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

import datetime
import sys
from ipaddress import IPv4Address
from unittest import mock

import pytest

from crate.client.exceptions import ProgrammingError

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

import pytz

from crate.client import connect
from crate.client.converter import DataType, DefaultTypeConverter


def test_cursor_fetch(mocked_connection):
    """Verify fetchone/fetchmany behaviour"""
    cursor = mocked_connection.cursor()
    response = {
        "col_types": [4, 5],
        "cols": ["name", "address"],
        "rows": [["foo", "10.10.10.1"], ["bar", "10.10.10.2"]],
        "rowcount": 2,
        "duration": 123,
    }
    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        cursor.execute("")
        assert cursor.fetchone() == ["foo", "10.10.10.1"]
        assert cursor.fetchmany() == [
            ["bar", "10.10.10.2"],
        ]


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="Test needs Python >= 3.10"
)
def test_cursor_description(mocked_connection):
    cursor = mocked_connection.cursor()
    response = {
        "col_types": [4, 5],
        "cols": ["name", "address"],
        "rows": [["foo", "10.10.10.1"], ["bar", "10.10.10.2"]],
        "rowcount": 2,
        "duration": 123,
    }
    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        cursor.execute("")
        assert len(cursor.description) == len(response["cols"])
        assert len(cursor.description[0]) == 7  # It's 7 by convention.
        for expected_name, name in zip(
            response["cols"], cursor.description, strict=False
        ):
            assert expected_name == name[0]

        cursor.close()

        assert cursor.description is None


def test_cursor_rowcount(mocked_connection):
    """Verify the logic of cursor.rowcount"""
    cursor = mocked_connection.cursor()
    response = {
        "col_types": [4, 5],
        "cols": ["name", "address"],
        "rows": [["foo", "10.10.10.1"], ["bar", "10.10.10.2"]],
        "rowcount": 2,
        "duration": 123,
    }
    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        cursor.execute("")
        assert cursor.rowcount == len(response["rows"])

        cursor._result = None
        assert cursor.rowcount == -1

        cursor.execute("")
        cursor._result = {}
        assert cursor.rowcount == -1

        cursor.execute("")
        cursor.close()
        assert cursor.rowcount == -1


def test_cursor_executemany(mocked_connection):
    """
    Verify executemany.
    """
    response = {
        "col_types": [],
        "cols": [],
        "duration": 123,
        "results": [{"rowcount": 1, "rowcount:": 1}],
    }
    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        cursor = mocked_connection.cursor()
        result = cursor.executemany("some sql", ())

        assert isinstance(result, list)
        assert response["results"] == result


def test_create_with_timezone_as_datetime_object(mocked_connection):
    """
    The cursor can return timezone-aware `datetime` objects when requested.
    Switching the time zone at runtime on the cursor object is possible.
    Here: Use a `datetime.timezone` instance.
    """
    tz_mst = datetime.timezone(datetime.timedelta(hours=7), name="MST")
    cursor = mocked_connection.cursor(time_zone=tz_mst)

    assert cursor.time_zone.tzname(None) == "MST"
    assert cursor.time_zone.utcoffset(None) == datetime.timedelta(seconds=25200)

    cursor.time_zone = datetime.timezone.utc

    assert cursor.time_zone.tzname(None) == "UTC"
    assert cursor.time_zone.utcoffset(None) == datetime.timedelta(0)


def test_create_with_timezone_as_pytz_object(mocked_connection):
    """
    The cursor can return timezone-aware `datetime` objects when requested.
    Here: Use a `pytz.timezone` instance.
    """

    cursor = mocked_connection.cursor(
        time_zone=pytz.timezone("Australia/Sydney")
    )
    assert cursor.time_zone.tzname(None) == "Australia/Sydney"

    # Apparently, when using `pytz`, the timezone object does not return
    # an offset. Nevertheless, it works, as demonstrated per doctest in
    # `cursor.txt`.
    assert cursor.time_zone.utcoffset(None) is None


def test_create_with_timezone_as_zoneinfo_object(mocked_connection):
    """
    The cursor can return timezone-aware `datetime` objects when requested.
    Here: Use a `zoneinfo.ZoneInfo` instance.
    """
    cursor = mocked_connection.cursor(
        time_zone=zoneinfo.ZoneInfo("Australia/Sydney")
    )
    assert cursor.time_zone.key == "Australia/Sydney"


def test_create_with_timezone_as_utc_offset_success(mocked_connection):
    """
    Verify the cursor can return timezone-aware `datetime` objects when
    requested.

    Here: Use a UTC offset in string format.
    """

    cursor = mocked_connection.cursor(time_zone="+0530")
    assert cursor.time_zone.tzname(None) == "+0530"
    assert cursor.time_zone.utcoffset(None) == datetime.timedelta(seconds=19800)

    cursor = mocked_connection.cursor(time_zone="-1145")
    assert cursor.time_zone.tzname(None) == "-1145"
    assert cursor.time_zone.utcoffset(None) == datetime.timedelta(
        days=-1, seconds=44100
    )


def test_create_with_timezone_as_utc_offset_failure(mocked_connection):
    """
    Verify the cursor trips when trying to use invalid UTC offset strings.
    """

    with pytest.raises(ValueError) as err:
        mocked_connection.cursor(time_zone="foobar")
        assert err == "Time zone 'foobar' is given in invalid UTC offset format"

    with pytest.raises(ValueError) as err:
        mocked_connection.cursor(time_zone="+abcd")
        assert (
            err
            == "Time zone '+abcd' is given in invalid UTC offset format: "
            + "invalid literal for int() with base 10: '+ab'"
        )


def test_create_with_timezone_connection_cursor_precedence(mocked_connection):
    """
    Verify that the time zone specified on the cursor object instance
    takes precedence over the one specified on the connection instance.
    """
    connection = connect(
        client=mocked_connection.client,
        time_zone=pytz.timezone("Australia/Sydney"),
    )
    cursor = connection.cursor(time_zone="+0530")
    assert cursor.time_zone.tzname(None) == "+0530"
    assert cursor.time_zone.utcoffset(None) == datetime.timedelta(seconds=19800)


def test_execute_with_args(mocked_connection):
    """
    Verify that `cursor.execute` is called with the right parameters.
    """
    cursor = mocked_connection.cursor()
    statement = "select * from locations where position = ?"
    cursor.execute(statement, 1)
    mocked_connection.client.sql.assert_called_once_with(statement, 1, None)


def test_execute_with_bulk_args(mocked_connection):
    """
    Verify that `cursor.execute` is called with the right parameters
    when passing `bulk_parameters`.
    """
    cursor = mocked_connection.cursor()
    statement = "select * from locations where position = ?"
    cursor.execute(statement, bulk_parameters=[[1]])
    mocked_connection.client.sql.assert_called_once_with(statement, None, [[1]])


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="Converter needs Python >= 3.10"
)
def test_execute_custom_converter(mocked_connection):
    """
    Verify that a custom converter is correctly applied when passed to a cursor.
    """
    # Extends the DefaultTypeConverter
    converter = DefaultTypeConverter(
        {
            DataType.BIT: lambda value: value is not None
            and int(value[2:-1], 2)
            or None
        }
    )
    cursor = mocked_connection.cursor(converter=converter)
    response = {
        "col_types": [4, 5, 11, 25],
        "cols": ["name", "address", "timestamp", "bitmask"],
        "rows": [
            ["foo", "10.10.10.1", 1658167836758, "B'0110'"],
            [None, None, None, None],
        ],
        "rowcount": 1,
        "duration": 123,
    }

    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        cursor.execute("")
        result = cursor.fetchall()

        assert result == [
            [
                "foo",
                IPv4Address("10.10.10.1"),
                datetime.datetime(
                    2022,
                    7,
                    18,
                    18,
                    10,
                    36,
                    758000,
                    tzinfo=datetime.timezone.utc,
                ),
                6,
            ],
            [None, None, None, None],
        ]


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="Converter needs Python >= 3.10"
)
def test_execute_with_converter_and_invalid_data_type(mocked_connection):
    converter = DefaultTypeConverter()

    # Create a `Cursor` object with converter.
    cursor = mocked_connection.cursor(converter=converter)

    response = {
        "col_types": [999],
        "cols": ["foo"],
        "rows": [
            ["n/a"],
        ],
        "rowcount": 1,
        "duration": 123,
    }
    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        cursor.execute("")
        with pytest.raises(ValueError) as e:
            cursor.fetchone()
            assert e.exception.args == "999 is not a valid DataType"


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="Converter needs Python >= 3.10"
)
def test_execute_array_with_converter(mocked_connection):
    converter = DefaultTypeConverter()
    cursor = mocked_connection.cursor(converter=converter)
    response = {
        "col_types": [4, [100, 5]],
        "cols": ["name", "address"],
        "rows": [["foo", ["10.10.10.1", "10.10.10.2"]]],
        "rowcount": 1,
        "duration": 123,
    }
    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        cursor.execute("")
        result = cursor.fetchone()

        assert result == [
            "foo",
            [IPv4Address("10.10.10.1"), IPv4Address("10.10.10.2")],
        ]


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="Converter needs Python >= 3.10"
)
def test_execute_array_with_converter_invalid(mocked_connection):
    converter = DefaultTypeConverter()
    cursor = mocked_connection.cursor(converter=converter)
    response = {
        "col_types": [4, [6, 5]],
        "cols": ["name", "address"],
        "rows": [["foo", ["10.10.10.1", "10.10.10.2"]]],
        "rowcount": 1,
        "duration": 123,
    }
    # Converting collections only works for `ARRAY`s. (ID=100).
    # When using `DOUBLE` (ID=6), it should raise an Exception.
    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        cursor.execute("")
        with pytest.raises(ValueError) as e:
            cursor.fetchone()
            assert e.exception.args == (
                "Data type 6 is not implemented as collection type"
            )


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="Converter needs Python >= 3.10"
)
def test_execute_nested_array_with_converter(mocked_connection):
    converter = DefaultTypeConverter()
    cursor = mocked_connection.cursor(converter=converter)
    response = {
        "col_types": [4, [100, [100, 5]]],
        "cols": ["name", "address_buckets"],
        "rows": [
            [
                "foo",
                [
                    ["10.10.10.1", "10.10.10.2"],
                    ["10.10.10.3"],
                    [],
                    None,
                ],
            ]
        ],
        "rowcount": 1,
        "duration": 123,
    }

    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        cursor.execute("")
        result = cursor.fetchone()
        assert result == [
            "foo",
            [
                [IPv4Address("10.10.10.1"), IPv4Address("10.10.10.2")],
                [IPv4Address("10.10.10.3")],
                [],
                None,
            ],
        ]


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="Converter needs Python >= 3.10"
)
def test_executemany_with_converter(mocked_connection):
    converter = DefaultTypeConverter()
    cursor = mocked_connection.cursor(converter=converter)
    response = {
        "col_types": [4, 5],
        "cols": ["name", "address"],
        "rows": [["foo", "10.10.10.1"]],
        "rowcount": 1,
        "duration": 123,
    }
    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        cursor.executemany("", [])
        result = cursor.fetchall()

        # ``executemany()`` is not intended to be used with statements
        # returning result sets. The result will always be empty.
        assert result == []


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="Converter needs Python >= 3.10"
)
def test_execute_with_timezone(mocked_connection):
    # Create a `Cursor` object with `time_zone`.
    tz_mst = datetime.timezone(datetime.timedelta(hours=7), name="MST")
    cursor = mocked_connection.cursor(time_zone=tz_mst)

    # Make up a response using CrateDB data type `TIMESTAMP`.
    response = {
        "col_types": [4, 11],
        "cols": ["name", "timestamp"],
        "rows": [
            ["foo", 1658167836758],
            [None, None],
        ],
    }
    with mock.patch.object(
        mocked_connection.client, "sql", return_value=response
    ):
        # Run execution and verify the returned `datetime` object is
        # timezone-aware, using the designated timezone object.
        cursor.execute("")
        result = cursor.fetchall()
        assert result == [
            [
                "foo",
                datetime.datetime(
                    2022,
                    7,
                    19,
                    1,
                    10,
                    36,
                    758000,
                    tzinfo=datetime.timezone(
                        datetime.timedelta(seconds=25200), "MST"
                    ),
                ),
            ],
            [
                None,
                None,
            ],
        ]

        assert result[0][1].tzname() == "MST"

        # Change timezone and verify the returned `datetime` object is using it.
        cursor.time_zone = datetime.timezone.utc
        cursor.execute("")
        result = cursor.fetchall()
        assert result == [
            [
                "foo",
                datetime.datetime(
                    2022,
                    7,
                    18,
                    18,
                    10,
                    36,
                    758000,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                None,
                None,
            ],
        ]

        assert result[0][1].tzname() == "UTC"


def test_cursor_close(mocked_connection):
    """
    Verify that a cursor is not closed if not specifically closed.
    """

    cursor = mocked_connection.cursor()
    cursor.execute("")
    assert cursor._closed is False

    cursor.close()

    assert cursor._closed is True
    assert not cursor._result
    assert cursor.duration == -1

    with pytest.raises(ProgrammingError, match="Connection closed"):
        mocked_connection.close()
        cursor.execute("")


def test_cursor_closes_access(mocked_connection):
    """
    Verify that a cursor cannot be used once it is closed.
    """

    cursor = mocked_connection.cursor()
    cursor.execute("")

    cursor.close()

    with pytest.raises(ProgrammingError):
        cursor.execute("s")
