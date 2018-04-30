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

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch, MagicMock

from crate.client.sqlalchemy.types import Object

import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

from crate.client.cursor import Cursor


fake_cursor = MagicMock(name='fake_cursor')
fake_cursor.rowcount = 1
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


class SqlAlchemyUpdateTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        self.base = declarative_base(bind=self.engine)

        class Character(self.base):
            __tablename__ = 'characters'

            name = sa.Column(sa.String, primary_key=True)
            age = sa.Column(sa.Integer)
            obj = sa.Column(Object)
            ts = sa.Column(sa.DateTime, onupdate=datetime.utcnow)

        self.character = Character
        self.session = Session()

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_onupdate_is_triggered(self):
        char = self.character(name='Arthur')
        self.session.add(char)
        self.session.commit()
        now = datetime.utcnow()

        fake_cursor.fetchall.return_value = [('Arthur', None)]
        fake_cursor.description = (
            ('characters_name', None, None, None, None, None, None),
            ('characters_ts', None, None, None, None, None, None),
        )

        char.age = 40
        self.session.commit()

        expected_stmt = ("UPDATE characters SET age = ?, "
                         "ts = ? WHERE characters.name = ?")
        args, kwargs = fake_cursor.execute.call_args
        stmt = args[0]
        args = args[1]
        self.assertEqual(expected_stmt, stmt)
        self.assertEqual(40, args[0])
        dt = datetime.strptime(args[1], '%Y-%m-%dT%H:%M:%S.%fZ')
        self.assertTrue(isinstance(dt, datetime))
        self.assertTrue(dt > now)
        self.assertEqual('Arthur', args[2])

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_bulk_update(self):
        """
            Checks whether bulk updates work correctly
            on native types and Crate types.
        """
        before_update_time = datetime.utcnow()

        self.session.query(self.character).update({
            # change everyone's name to Julia
            self.character.name: 'Julia',
            self.character.obj: {'favorite_book': 'Romeo & Juliet'}
        })

        self.session.commit()

        expected_stmt = ("UPDATE characters SET "
                         "name = ?, obj = ?, ts = ?")
        args, kwargs = fake_cursor.execute.call_args
        stmt = args[0]
        args = args[1]
        self.assertEqual(expected_stmt, stmt)
        self.assertEqual('Julia', args[0])
        self.assertEqual({'favorite_book': 'Romeo & Juliet'}, args[1])
        dt = datetime.strptime(args[2], '%Y-%m-%dT%H:%M:%S.%fZ')
        self.assertTrue(isinstance(dt, datetime))
        self.assertTrue(dt > before_update_time)
