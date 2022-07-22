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

import os
from datetime import datetime, timezone, date
from unittest import TestCase, mock

import time_machine
from freezegun import freeze_time

from crate.testing.util import datetime_now_utc_naive, date_now_utc_naive


class UtcNowDatetimeTest(TestCase):
    """
    Demonstrate some scenarios of "datetime.utcnow() considered harmful".

    The reason is that it depends on the system time zone setting of the
    machine. On the other hand, `datetime.now(timezone.utc)` works the same way
    in all situations.

    - https://blog.ganssle.io/articles/2019/11/utcnow.html
    - https://aaronoellis.com/articles/python-datetime-utcnow-considered-harmful
    """

    @mock.patch.dict(os.environ, {"TZ": "UTC"})
    def test_utcnow_depends_on_system_timezone_success_with_utc(self):
        """
        Exercise difference between `datetime.now(timezone.utc)` vs. `datetime.utcnow()`.

        When your server time is UTC time, everything will work perfectly.
        """
        self.assertAlmostEqual(
            datetime.now(timezone.utc).timestamp(),
            datetime.utcnow().timestamp(),
            places=1)

    @mock.patch.dict(os.environ, {"TZ": "Europe/Prague"})
    def test_utcnow_depends_on_system_timezone_failure_with_non_utc(self):
        """
        Exercise difference between `datetime.now(timezone.utc)` vs. `datetime.utcnow()`.

        When your server time is expressed in a different time zone than UTC,
        things will go south.
        """
        self.assertNotAlmostEqual(
            datetime.now(timezone.utc).timestamp(),
            datetime.utcnow().timestamp(),
            places=1)

    @time_machine.travel("2022-07-22T00:42:00+0200")
    def test_utcnow_naive_success(self):
        """
        Demonstrate that `datetime_now_utc_naive()` correctly expresses UTC.
        The `day` component should be one day before the day of the timestamp
        expressed in UTC.
        """
        dt = datetime_now_utc_naive()
        self.assertEqual(dt.day, 21)

    @time_machine.travel("2022-07-22T00:42:00+0200")
    def test_date_today_naive_success(self):
        """
        Demonstrate that `date_now_utc_naive()` correctly expresses UTC.
        The `day` component should be one day before the day of the timestamp
        expressed in UTC.
        """
        dt = date_now_utc_naive()
        self.assertEqual(dt.day, 21)

    @time_machine.travel("2022-07-22T00:42:00+0200")
    def test_date_today_failure(self):
        """
        Demonstrate that `date.today()` does not yield the date in UTC.

        This causes problems when verifying individual date components
        (here: day) around midnight.
        """
        dt = date.today()
        self.assertEqual(dt.day, 22)


class UtcFromTimestampDatetimeTest(TestCase):
    """
    Demonstrate some scenarios of "datetime.utcfromtimestamp() considered harmful".

    The reason is that it depends on the system time zone setting of the
    machine. On the other hand, `datetime.fromtimestamp(..., tz=timezone.utc)`
    works the same way in all situations.

    - https://blog.ganssle.io/articles/2019/11/utcnow.html
    - https://aaronoellis.com/articles/python-datetime-utcnow-considered-harmful
    """

    TIMESTAMP_AFTER_MIDNIGHT = 1658450520  # Fri, 22 Jul 2022 00:42:00 GMT

    @mock.patch.dict(os.environ, {"TZ": "UTC"})
    def test_utcfromtimestamp_depends_on_system_timezone_success_with_utc(self):
        """
        Exercise flaw of `datetime.utcfromtimestamp()`.

        When your server time is UTC time, everything will work perfectly.
        """
        dt = datetime.utcfromtimestamp(self.TIMESTAMP_AFTER_MIDNIGHT)
        self.assertEqual(dt.timestamp(), self.TIMESTAMP_AFTER_MIDNIGHT)

    @mock.patch.dict(os.environ, {"TZ": "Europe/Prague"})
    def test_utcfromtimestamp_depends_on_system_timezone_failure_with_non_utc(self):
        """
        Exercise flaw of `datetime.utcfromtimestamp()`.

        When your server time is expressed in a different time zone than UTC,
        things will go south.
        """
        dt = datetime.utcfromtimestamp(self.TIMESTAMP_AFTER_MIDNIGHT)
        self.assertNotEqual(dt.timestamp(), self.TIMESTAMP_AFTER_MIDNIGHT)

    @mock.patch.dict(os.environ, {"TZ": "Europe/Prague"})
    @freeze_time("2022-07-22T00:42:00+0200")
    def test_utcfromtimestamp_depends_on_system_timezone_failure_with_non_utc_success_with_freezegun(self):
        """
        Exercise flaw of `datetime.utcfromtimestamp()`.

        Don't be fooled: While this test has an apparent positive outcome, this
        is only because `freezegun` works around the problem resp. has the same
        flaw.
        """
        dt = datetime.utcfromtimestamp(self.TIMESTAMP_AFTER_MIDNIGHT)
        self.assertEqual(dt.timestamp(), self.TIMESTAMP_AFTER_MIDNIGHT)

    @mock.patch.dict(os.environ, {"TZ": "UTC"})
    def test_fromtimestamp_always_correct_with_utc(self):
        """
        Demonstrate that `datetime.fromtimestamp(..., tz=timezone.utc)` is always correct.
        Here: Emulate system time zone in UTC.
        """
        dt = datetime.fromtimestamp(self.TIMESTAMP_AFTER_MIDNIGHT, tz=timezone.utc)
        self.assertEqual(dt.timestamp(), self.TIMESTAMP_AFTER_MIDNIGHT)

    @mock.patch.dict(os.environ, {"TZ": "Europe/Prague"})
    def test_fromtimestamp_always_correct_with_non_utc(self):
        """
        Demonstrate that `datetime.fromtimestamp(..., tz=timezone.utc)` is always correct.
        Here: Emulate non-UTC system time zone.
        """
        dt = datetime.fromtimestamp(self.TIMESTAMP_AFTER_MIDNIGHT, tz=timezone.utc)
        self.assertEqual(dt.timestamp(), self.TIMESTAMP_AFTER_MIDNIGHT)
