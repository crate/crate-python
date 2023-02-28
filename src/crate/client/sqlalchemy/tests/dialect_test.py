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
from unittest import TestCase, skipIf
from unittest.mock import MagicMock, patch

import sqlalchemy as sa

from crate.client.cursor import Cursor
from crate.client.sqlalchemy import SA_VERSION
from crate.client.sqlalchemy.sa_version import SA_1_4, SA_2_0
from crate.client.sqlalchemy.types import Object
from sqlalchemy import inspect
from sqlalchemy.orm import Session
try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.testing import eq_, in_, is_true

FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)


@patch('crate.client.connection.Cursor', FakeCursor)
class SqlAlchemyDialectTest(TestCase):

    def execute_wrapper(self, query, *args, **kwargs):
        self.executed_statement = query
        return self.fake_cursor

    def setUp(self):

        self.fake_cursor = MagicMock(name='fake_cursor')
        FakeCursor.return_value = self.fake_cursor

        self.engine = sa.create_engine('crate://')

        self.executed_statement = None

        self.connection = self.engine.connect()

        self.fake_cursor.execute = self.execute_wrapper

        self.base = declarative_base()

        class Character(self.base):
            __tablename__ = 'characters'

            name = sa.Column(sa.String, primary_key=True)
            age = sa.Column(sa.Integer, primary_key=True)
            obj = sa.Column(Object)
            ts = sa.Column(sa.DateTime, onupdate=datetime.utcnow)

        self.session = Session(bind=self.engine)

    def init_mock(self, return_value=None):
        self.fake_cursor.rowcount = 1
        self.fake_cursor.description = (
            ('foo', None, None, None, None, None, None),
        )
        self.fake_cursor.fetchall = MagicMock(return_value=return_value)

    def test_primary_keys_2_3_0(self):
        insp = inspect(self.session.bind)
        self.engine.dialect.server_version_info = (2, 3, 0)

        self.fake_cursor.rowcount = 3
        self.fake_cursor.description = (
            ('foo', None, None, None, None, None, None),
        )
        self.fake_cursor.fetchall = MagicMock(return_value=[["id"], ["id2"], ["id3"]])

        eq_(insp.get_pk_constraint("characters")['constrained_columns'], {"id", "id2", "id3"})
        self.fake_cursor.fetchall.assert_called_once_with()
        in_("information_schema.key_column_usage", self.executed_statement)
        in_("table_catalog = ?", self.executed_statement)

    def test_primary_keys_3_0_0(self):
        insp = inspect(self.session.bind)
        self.engine.dialect.server_version_info = (3, 0, 0)

        self.fake_cursor.rowcount = 3
        self.fake_cursor.description = (
            ('foo', None, None, None, None, None, None),
        )
        self.fake_cursor.fetchall = MagicMock(return_value=[["id"], ["id2"], ["id3"]])

        eq_(insp.get_pk_constraint("characters")['constrained_columns'], {"id", "id2", "id3"})
        self.fake_cursor.fetchall.assert_called_once_with()
        in_("information_schema.key_column_usage", self.executed_statement)
        in_("table_schema = ?", self.executed_statement)

    def test_get_table_names(self):
        self.fake_cursor.rowcount = 1
        self.fake_cursor.description = (
            ('foo', None, None, None, None, None, None),
        )
        self.fake_cursor.fetchall = MagicMock(return_value=[["t1"], ["t2"]])

        insp = inspect(self.session.bind)
        self.engine.dialect.server_version_info = (2, 0, 0)
        eq_(insp.get_table_names(schema="doc"),
            ['t1', 't2'])
        in_("WHERE table_schema = ? AND table_type = 'BASE TABLE' ORDER BY", self.executed_statement)

    def test_get_view_names(self):
        self.fake_cursor.rowcount = 1
        self.fake_cursor.description = (
            ('foo', None, None, None, None, None, None),
        )
        self.fake_cursor.fetchall = MagicMock(return_value=[["v1"], ["v2"]])

        insp = inspect(self.session.bind)
        self.engine.dialect.server_version_info = (2, 0, 0)
        eq_(insp.get_view_names(schema="doc"),
            ['v1', 'v2'])
        eq_(self.executed_statement, "SELECT table_name FROM information_schema.views "
                                     "ORDER BY table_name ASC, table_schema ASC")

    @skipIf(SA_VERSION < SA_1_4, "Inspector.has_table only available on SQLAlchemy>=1.4")
    def test_has_table(self):
        self.init_mock(return_value=[["foo"], ["bar"]])
        insp = inspect(self.session.bind)
        is_true(insp.has_table("bar"))
        eq_(self.executed_statement,
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = ? AND table_type = 'BASE TABLE' "
            "ORDER BY table_name ASC, table_schema ASC")

    @skipIf(SA_VERSION < SA_2_0, "Inspector.has_schema only available on SQLAlchemy>=2.0")
    def test_has_schema(self):
        self.init_mock(
            return_value=[["blob"], ["doc"], ["information_schema"], ["pg_catalog"], ["sys"]])
        insp = inspect(self.session.bind)
        is_true(insp.has_schema("doc"))
        eq_(self.executed_statement,
            "select schema_name from information_schema.schemata order by schema_name asc")
