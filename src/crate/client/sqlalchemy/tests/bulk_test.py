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

from unittest import TestCase
from unittest.mock import patch, MagicMock

import sqlalchemy as sa
from sqlalchemy.orm import Session
try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

from crate.client.cursor import Cursor


fake_cursor = MagicMock(name='fake_cursor')
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


class SqlAlchemyBulkTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        Base = declarative_base()

        class Character(Base):
            __tablename__ = 'characters'

            name = sa.Column(sa.String, primary_key=True)
            age = sa.Column(sa.Integer)

        self.character = Character
        self.session = Session(bind=self.engine)

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_bulk_save(self):
        chars = [
            self.character(name='Arthur', age=35),
            self.character(name='Banshee', age=26),
            self.character(name='Callisto', age=37),
        ]

        fake_cursor.description = ()
        fake_cursor.rowcount = len(chars)
        fake_cursor.executemany.return_value = [
            {'rowcount': 1},
            {'rowcount': 1},
            {'rowcount': 1},
        ]
        self.session.bulk_save_objects(chars)
        (stmt, bulk_args), _ = fake_cursor.executemany.call_args

        expected_stmt = "INSERT INTO characters (name, age) VALUES (?, ?)"
        self.assertEqual(expected_stmt, stmt)

        expected_bulk_args = (
            ('Arthur', 35),
            ('Banshee', 26),
            ('Callisto', 37)
        )
        self.assertSequenceEqual(expected_bulk_args, bulk_args)
