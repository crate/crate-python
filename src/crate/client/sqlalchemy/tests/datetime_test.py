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

from __future__ import absolute_import
from datetime import datetime, tzinfo, timedelta
from unittest import TestCase
from mock import patch, MagicMock

import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

from crate.client.cursor import Cursor


fake_cursor = MagicMock(name='fake_cursor')
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


class CST(tzinfo):
    """
    Timezone object for CST
    """

    def utcoffset(self, date_time):
        return timedelta(seconds=-3600)

    def dst(self, date_time):
        return timedelta(seconds=-7200)


@patch('crate.client.connection.Cursor', FakeCursor)
class SqlAlchemyDateAndDateTimeTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        Base = declarative_base(bind=self.engine)

        class Character(Base):
            __tablename__ = 'characters'
            name = sa.Column(sa.String, primary_key=True)
            date = sa.Column(sa.Date)
            timestamp = sa.Column(sa.DateTime)

        fake_cursor.description = (
            ('characters_name', None, None, None, None, None, None),
            ('characters_date', None, None, None, None, None, None)
        )
        self.session = Session()
        self.Character = Character

    def test_date_can_handle_datetime(self):
        """ date type should also be able to handle iso datetime strings.

        this verifies that the fallback in the Date result_processor works.
        """
        fake_cursor.fetchall.return_value = [
            ('Trillian', '2013-07-16T00:00:00.000Z')
        ]
        self.session.query(self.Character).first()

    def test_date_cannot_handle_tz_aware_datetime(self):
        character = self.Character()
        character.name = "Athur"
        character.timestamp = datetime(2009, 5, 13, 19, 19, 30, tzinfo=CST())
        self.session.add(character)
        self.assertRaises(DBAPIError, self.session.commit)
