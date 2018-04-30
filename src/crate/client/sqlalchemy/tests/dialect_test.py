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
from unittest.mock import MagicMock

import sqlalchemy as sa
from crate.client.sqlalchemy.types import Object
from sqlalchemy import inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.testing import eq_, in_

fake_cursor = MagicMock(name='fake_cursor')


class DialectTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        self.executed_statement = None

        def execute_wrapper(query, *args, **kwargs):
            self.executed_statement = query
            return fake_cursor

        self.engine.execute = execute_wrapper
        self.connection = self.engine.connect()
        self.connection.execute = execute_wrapper
        self.base = declarative_base(bind=self.engine)

        class Character(self.base):
            __tablename__ = 'characters'

            name = sa.Column(sa.String, primary_key=True)
            age = sa.Column(sa.Integer, primary_key=True)
            obj = sa.Column(Object)
            ts = sa.Column(sa.DateTime, onupdate=datetime.utcnow)

        self.character = Character
        self.session = Session()

    def test_pks_are_retrieved_depending_on_version_set(self):
        meta = self.character.metadata

        # test the old pk retrieval
        insp = inspect(meta.bind)
        self.engine.dialect.server_version_info = (0, 54, 0)
        fake_cursor.rowcount = 1
        fake_cursor.fetchone = MagicMock(return_value=[["id", "id2", "id3"]])
        eq_(insp.get_pk_constraint("characters")['constrained_columns'], {"id", "id2", "id3"})
        fake_cursor.fetchone.assert_called_once_with()
        in_("information_schema.table_constraints", self.executed_statement)

        # test the new pk retrieval
        insp = inspect(meta.bind)
        self.engine.dialect.server_version_info = (2, 3, 0)
        fake_cursor.rowcount = 3
        fake_cursor.fetchall = MagicMock(return_value=[["id"], ["id2"], ["id3"]])
        eq_(insp.get_pk_constraint("characters")['constrained_columns'], {"id", "id2", "id3"})
        fake_cursor.fetchall.assert_called_once_with()
        in_("information_schema.key_column_usage", self.executed_statement)

    def test_get_table_names(self):
        fake_cursor.rowcount = 1
        fake_cursor.fetchall = MagicMock(return_value=[["t1"], ["t2"]])

        insp = inspect(self.character.metadata.bind)
        self.engine.dialect.server_version_info = (2, 0, 0)
        eq_(insp.get_table_names(self.connection, "doc"),
            ['t1', 't2'])
        in_("AND table_type = 'BASE TABLE' ORDER BY", self.executed_statement)

        insp = inspect(self.character.metadata.bind)
        self.engine.dialect.server_version_info = (1, 0, 0)
        eq_(insp.get_table_names(self.connection, "doc"),
            ['t1', 't2'])
        in_("WHERE table_schema = ? ORDER BY", self.executed_statement)

        insp = inspect(self.character.metadata.bind)
        self.engine.dialect.server_version_info = (0, 56, 0)
        eq_(insp.get_table_names(self.connection, "doc"),
            ['t1', 't2'])
        in_("WHERE schema_name = ? ORDER BY", self.executed_statement)
