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

from crate.client.sqlalchemy.compiler import crate_before_execute

import sqlalchemy as sa
from sqlalchemy.sql import text, Update

from crate.client.sqlalchemy.sa_version import SA_VERSION, SA_1_4
from crate.client.sqlalchemy.types import Craty


class SqlAlchemyCompilerTest(TestCase):

    def setUp(self):
        self.crate_engine = sa.create_engine('crate://')
        self.sqlite_engine = sa.create_engine('sqlite://')
        self.metadata = sa.MetaData()
        self.mytable = sa.Table('mytable', self.metadata,
                                sa.Column('name', sa.String),
                                sa.Column('data', Craty))

        self.update = Update(self.mytable).where(text('name=:name'))
        self.values = [{'name': 'crate'}]
        self.values = (self.values, )

    def test_sqlite_update_not_rewritten(self):
        clauseelement, multiparams, params = crate_before_execute(
            self.sqlite_engine, self.update, self.values, {}
        )

        self.assertFalse(hasattr(clauseelement, '_crate_specific'))

    def test_crate_update_rewritten(self):
        clauseelement, multiparams, params = crate_before_execute(
            self.crate_engine, self.update, self.values, {}
        )

        self.assertTrue(hasattr(clauseelement, '_crate_specific'))

    def test_bulk_update_on_builtin_type(self):
        """
        The "before_execute" hook in the compiler doesn't get
        access to the parameters in case of a bulk update. It
        should not try to optimize any parameters.
        """
        data = ({},)
        clauseelement, multiparams, params = crate_before_execute(
            self.crate_engine, self.update, data, None
        )

        self.assertFalse(hasattr(clauseelement, '_crate_specific'))

    def test_select_with_offset(self):
        """
        Verify the `CrateCompiler.limit_clause` method, with offset.
        """
        selectable = self.mytable.select().offset(5)
        statement = str(selectable.compile(bind=self.crate_engine))
        if SA_VERSION >= SA_1_4:
            self.assertEqual(statement, "SELECT mytable.name, mytable.data \nFROM mytable\n LIMIT ALL OFFSET ?")
        else:
            self.assertEqual(statement, "SELECT mytable.name, mytable.data \nFROM mytable \n LIMIT ALL OFFSET ?")

    def test_select_with_limit(self):
        """
        Verify the `CrateCompiler.limit_clause` method, with limit.
        """
        selectable = self.mytable.select().limit(42)
        statement = str(selectable.compile(bind=self.crate_engine))
        self.assertEqual(statement, "SELECT mytable.name, mytable.data \nFROM mytable \n LIMIT ?")

    def test_select_with_offset_and_limit(self):
        """
        Verify the `CrateCompiler.limit_clause` method, with offset and limit.
        """
        selectable = self.mytable.select().offset(5).limit(42)
        statement = str(selectable.compile(bind=self.crate_engine))
        self.assertEqual(statement, "SELECT mytable.name, mytable.data \nFROM mytable \n LIMIT ? OFFSET ?")
