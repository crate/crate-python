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
from ipaddress import IPv4Address
from unittest import TestCase
from unittest.mock import MagicMock
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

import pytz

from crate.client import connect
from crate.client.converter import DataType, DefaultTypeConverter
from crate.client.http import Client
from crate.client.test_util import ClientMocked


class CursorTest(TestCase):

    @staticmethod
    def get_mocked_connection():
        client = MagicMock(spec=Client)
        return connect(client=client)

    def test_create_with_timezone_as_datetime_object(self):
        """
        Verify the cursor returns timezone-aware `datetime` objects when requested to.
        Switching the time zone at runtime on the cursor object is possible.
        Here: Use a `datetime.timezone` instance.
        """

        connection = self.get_mocked_connection()

        tz_mst = datetime.timezone(datetime.timedelta(hours=7), name="MST")
        cursor = connection.cursor(time_zone=tz_mst)

        self.assertEqual(cursor.time_zone.tzname(None), "MST")
        self.assertEqual(cursor.time_zone.utcoffset(None), datetime.timedelta(seconds=25200))

        cursor.time_zone = datetime.timezone.utc
        self.assertEqual(cursor.time_zone.tzname(None), "UTC")
        self.assertEqual(cursor.time_zone.utcoffset(None), datetime.timedelta(0))

    def test_create_with_timezone_as_pytz_object(self):
        """
        Verify the cursor returns timezone-aware `datetime` objects when requested to.
        Here: Use a `pytz.timezone` instance.
        """
        connection = self.get_mocked_connection()
        cursor = connection.cursor(time_zone=pytz.timezone('Australia/Sydney'))
        self.assertEqual(cursor.time_zone.tzname(None), "Australia/Sydney")

        # Apparently, when using `pytz`, the timezone object does not return an offset.
        # Nevertheless, it works, as demonstrated per doctest in `cursor.txt`.
        self.assertEqual(cursor.time_zone.utcoffset(None), None)

    def test_create_with_timezone_as_zoneinfo_object(self):
        """
        Verify the cursor returns timezone-aware `datetime` objects when requested to.
        Here: Use a `zoneinfo.ZoneInfo` instance.
        """
        connection = self.get_mocked_connection()
        cursor = connection.cursor(time_zone=zoneinfo.ZoneInfo('Australia/Sydney'))
        self.assertEqual(cursor.time_zone.key, 'Australia/Sydney')

    def test_create_with_timezone_as_utc_offset_success(self):
        """
        Verify the cursor returns timezone-aware `datetime` objects when requested to.
        Here: Use a UTC offset in string format.
        """
        connection = self.get_mocked_connection()
        cursor = connection.cursor(time_zone="+0530")
        self.assertEqual(cursor.time_zone.tzname(None), "+0530")
        self.assertEqual(cursor.time_zone.utcoffset(None), datetime.timedelta(seconds=19800))

        connection = self.get_mocked_connection()
        cursor = connection.cursor(time_zone="-1145")
        self.assertEqual(cursor.time_zone.tzname(None), "-1145")
        self.assertEqual(cursor.time_zone.utcoffset(None), datetime.timedelta(days=-1, seconds=44100))

    def test_create_with_timezone_as_utc_offset_failure(self):
        """
        Verify the cursor croaks when trying to create it with invalid UTC offset strings.
        """
        connection = self.get_mocked_connection()
        with self.assertRaises(AssertionError) as ex:
            connection.cursor(time_zone="foobar")
        self.assertEqual(str(ex.exception), "Time zone 'foobar' is given in invalid UTC offset format")

        connection = self.get_mocked_connection()
        with self.assertRaises(ValueError) as ex:
            connection.cursor(time_zone="+abcd")
        self.assertEqual(str(ex.exception), "Time zone '+abcd' is given in invalid UTC offset format: "
                                            "invalid literal for int() with base 10: '+ab'")

    def test_create_with_timezone_connection_cursor_precedence(self):
        """
        Verify that the time zone specified on the cursor object instance
        takes precedence over the one specified on the connection instance.
        """
        client = MagicMock(spec=Client)
        connection = connect(client=client, time_zone=pytz.timezone('Australia/Sydney'))
        cursor = connection.cursor(time_zone="+0530")
        self.assertEqual(cursor.time_zone.tzname(None), "+0530")
        self.assertEqual(cursor.time_zone.utcoffset(None), datetime.timedelta(seconds=19800))

    def test_execute_with_args(self):
        client = MagicMock(spec=Client)
        conn = connect(client=client)
        c = conn.cursor()
        statement = 'select * from locations where position = ?'
        c.execute(statement, 1)
        client.sql.assert_called_once_with(statement, 1, None)
        conn.close()

    def test_execute_with_bulk_args(self):
        client = MagicMock(spec=Client)
        conn = connect(client=client)
        c = conn.cursor()
        statement = 'select * from locations where position = ?'
        c.execute(statement, bulk_parameters=[[1]])
        client.sql.assert_called_once_with(statement, None, [[1]])
        conn.close()

    def test_execute_with_converter(self):
        client = ClientMocked()
        conn = connect(client=client)

        # Use the set of data type converters from `DefaultTypeConverter`
        # and add another custom converter.
        converter = DefaultTypeConverter(
            {DataType.BIT: lambda value: value is not None and int(value[2:-1], 2) or None})

        # Create a `Cursor` object with converter.
        c = conn.cursor(converter=converter)

        # Make up a response using CrateDB data types `TEXT`, `IP`,
        # `TIMESTAMP`, `BIT`.
        conn.client.set_next_response({
            "col_types": [4, 5, 11, 25],
            "cols": ["name", "address", "timestamp", "bitmask"],
            "rows": [
                ["foo", "10.10.10.1", 1658167836758, "B'0110'"],
                [None, None, None, None],
            ],
            "rowcount": 1,
            "duration": 123
        })

        c.execute("")
        result = c.fetchall()
        self.assertEqual(result, [
            ['foo', IPv4Address('10.10.10.1'), datetime.datetime(2022, 7, 18, 18, 10, 36, 758000), 6],
            [None, None, None, None],
        ])

        conn.close()

    def test_execute_with_converter_and_invalid_data_type(self):
        client = ClientMocked()
        conn = connect(client=client)
        converter = DefaultTypeConverter()

        # Create a `Cursor` object with converter.
        c = conn.cursor(converter=converter)

        # Make up a response using CrateDB data types `TEXT`, `IP`,
        # `TIMESTAMP`, `BIT`.
        conn.client.set_next_response({
            "col_types": [999],
            "cols": ["foo"],
            "rows": [
                ["n/a"],
            ],
            "rowcount": 1,
            "duration": 123
        })

        c.execute("")
        with self.assertRaises(ValueError) as ex:
            c.fetchone()
        self.assertEqual(ex.exception.args, ("999 is not a valid DataType",))

    def test_execute_array_with_converter(self):
        client = ClientMocked()
        conn = connect(client=client)
        converter = DefaultTypeConverter()
        cursor = conn.cursor(converter=converter)

        conn.client.set_next_response({
            "col_types": [4, [100, 5]],
            "cols": ["name", "address"],
            "rows": [["foo", ["10.10.10.1", "10.10.10.2"]]],
            "rowcount": 1,
            "duration": 123
        })

        cursor.execute("")
        result = cursor.fetchone()
        self.assertEqual(result, [
            'foo',
            [IPv4Address('10.10.10.1'), IPv4Address('10.10.10.2')],
        ])

    def test_execute_array_with_converter_and_invalid_collection_type(self):
        client = ClientMocked()
        conn = connect(client=client)
        converter = DefaultTypeConverter()
        cursor = conn.cursor(converter=converter)

        # Converting collections only works for `ARRAY`s. (ID=100).
        # When using `DOUBLE` (ID=6), it should croak.
        conn.client.set_next_response({
            "col_types": [4, [6, 5]],
            "cols": ["name", "address"],
            "rows": [["foo", ["10.10.10.1", "10.10.10.2"]]],
            "rowcount": 1,
            "duration": 123
        })

        cursor.execute("")

        with self.assertRaises(ValueError) as ex:
            cursor.fetchone()
        self.assertEqual(ex.exception.args, ("Data type 6 is not implemented as collection type",))

    def test_execute_nested_array_with_converter(self):
        client = ClientMocked()
        conn = connect(client=client)
        converter = DefaultTypeConverter()
        cursor = conn.cursor(converter=converter)

        conn.client.set_next_response({
            "col_types": [4, [100, [100, 5]]],
            "cols": ["name", "address_buckets"],
            "rows": [["foo", [["10.10.10.1", "10.10.10.2"], ["10.10.10.3"], [], None]]],
            "rowcount": 1,
            "duration": 123
        })

        cursor.execute("")
        result = cursor.fetchone()
        self.assertEqual(result, [
            'foo',
            [[IPv4Address('10.10.10.1'), IPv4Address('10.10.10.2')], [IPv4Address('10.10.10.3')], [], None],
        ])

    def test_executemany_with_converter(self):
        client = ClientMocked()
        conn = connect(client=client)
        converter = DefaultTypeConverter()
        cursor = conn.cursor(converter=converter)

        conn.client.set_next_response({
            "col_types": [4, 5],
            "cols": ["name", "address"],
            "rows": [["foo", "10.10.10.1"]],
            "rowcount": 1,
            "duration": 123
        })

        cursor.executemany("", [])
        result = cursor.fetchall()

        # ``executemany()`` is not intended to be used with statements returning result
        # sets. The result will always be empty.
        self.assertEqual(result, [])

    def test_execute_with_timezone(self):
        client = ClientMocked()
        conn = connect(client=client)

        # Create a `Cursor` object with `time_zone`.
        tz_mst = datetime.timezone(datetime.timedelta(hours=7), name="MST")
        c = conn.cursor(time_zone=tz_mst)

        # Make up a response using CrateDB data type `TIMESTAMP`.
        conn.client.set_next_response({
            "col_types": [4, 11],
            "cols": ["name", "timestamp"],
            "rows": [
                ["foo", 1658167836758],
                [None, None],
            ],
        })

        # Run execution and verify the returned `datetime` object is timezone-aware,
        # using the designated timezone object.
        c.execute("")
        result = c.fetchall()
        self.assertEqual(result, [
            [
                'foo',
                datetime.datetime(2022, 7, 19, 1, 10, 36, 758000,
                                  tzinfo=datetime.timezone(datetime.timedelta(seconds=25200), 'MST')),
            ],
            [
                None,
                None,
            ],
        ])
        self.assertEqual(result[0][1].tzname(), "MST")

        # Change timezone and verify the returned `datetime` object is using it.
        c.time_zone = datetime.timezone.utc
        c.execute("")
        result = c.fetchall()
        self.assertEqual(result, [
            [
                'foo',
                datetime.datetime(2022, 7, 18, 18, 10, 36, 758000, tzinfo=datetime.timezone.utc),
            ],
            [
                None,
                None,
            ],
        ])
        self.assertEqual(result[0][1].tzname(), "UTC")

        conn.close()
