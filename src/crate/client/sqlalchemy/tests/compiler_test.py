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
from textwrap import dedent
from unittest import mock, skipIf

from crate.client.sqlalchemy.compiler import crate_before_execute

import sqlalchemy as sa
from sqlalchemy.sql import text, Update

from crate.client.sqlalchemy.sa_version import SA_VERSION, SA_1_4, SA_2_0
from crate.client.sqlalchemy.types import ObjectType
from crate.client.test_util import ParametrizedTestCase


class SqlAlchemyCompilerTest(ParametrizedTestCase):

    def setUp(self):
        self.crate_engine = sa.create_engine('crate://')
        if isinstance(self.param, dict) and "server_version_info" in self.param:
            server_version_info = self.param["server_version_info"]
            self.crate_engine.dialect.server_version_info = server_version_info
        self.sqlite_engine = sa.create_engine('sqlite://')
        self.metadata = sa.MetaData()
        self.mytable = sa.Table('mytable', self.metadata,
                                sa.Column('name', sa.String),
                                sa.Column('data', ObjectType))

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

    def test_select_with_ilike_no_escape(self):
        """
        Verify the compiler uses CrateDB's native `ILIKE` method.
        """
        selectable = self.mytable.select().where(self.mytable.c.name.ilike("%foo%"))
        statement = str(selectable.compile(bind=self.crate_engine))
        if self.crate_engine.dialect.has_ilike_operator():
            self.assertEqual(statement, dedent("""
                SELECT mytable.name, mytable.data 
                FROM mytable 
                WHERE mytable.name ILIKE ?
            """).strip())  # noqa: W291
        else:
            self.assertEqual(statement, dedent("""
                SELECT mytable.name, mytable.data 
                FROM mytable 
                WHERE lower(mytable.name) LIKE lower(?)
            """).strip())  # noqa: W291

    def test_select_with_not_ilike_no_escape(self):
        """
        Verify the compiler uses CrateDB's native `ILIKE` method.
        """
        selectable = self.mytable.select().where(self.mytable.c.name.notilike("%foo%"))
        statement = str(selectable.compile(bind=self.crate_engine))
        if SA_VERSION < SA_1_4 or not self.crate_engine.dialect.has_ilike_operator():
            self.assertEqual(statement, dedent("""
                SELECT mytable.name, mytable.data 
                FROM mytable 
                WHERE lower(mytable.name) NOT LIKE lower(?)
            """).strip())  # noqa: W291
        else:
            self.assertEqual(statement, dedent("""
                SELECT mytable.name, mytable.data 
                FROM mytable 
                WHERE mytable.name NOT ILIKE ?
            """).strip())  # noqa: W291

    def test_select_with_ilike_and_escape(self):
        """
        Verify the compiler fails when using CrateDB's native `ILIKE` method together with `ESCAPE`.
        """

        selectable = self.mytable.select().where(self.mytable.c.name.ilike("%foo%", escape='\\'))
        with self.assertRaises(NotImplementedError) as cmex:
            selectable.compile(bind=self.crate_engine)
        self.assertEqual(str(cmex.exception), "Unsupported feature: ESCAPE is not supported")

    @skipIf(SA_VERSION < SA_1_4, "SQLAlchemy 1.3 and earlier do not support native `NOT ILIKE` compilation")
    def test_select_with_not_ilike_and_escape(self):
        """
        Verify the compiler fails when using CrateDB's native `ILIKE` method together with `ESCAPE`.
        """

        selectable = self.mytable.select().where(self.mytable.c.name.notilike("%foo%", escape='\\'))
        with self.assertRaises(NotImplementedError) as cmex:
            selectable.compile(bind=self.crate_engine)
        self.assertEqual(str(cmex.exception), "Unsupported feature: ESCAPE is not supported")

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

    def test_insert_multivalues(self):
        """
        Verify that "in-place multirow inserts" aka. "multivalues inserts" aka.
        the `supports_multivalues_insert` dialect feature works.

        When this feature is not enabled, using it will raise an error:

            CompileError: The 'crate' dialect with current database version
            settings does not support in-place multirow inserts

        > The Insert construct also supports being passed a list of dictionaries
        > or full-table-tuples, which on the server will render the less common
        > SQL syntax of "multiple values" - this syntax is supported on backends
        > such as SQLite, PostgreSQL, MySQL, but not necessarily others.

        > It is essential to note that passing multiple values is NOT the same
        > as using traditional `executemany()` form. The above syntax is a special
        > syntax not typically used. To emit an INSERT statement against
        > multiple rows, the normal method is to pass a multiple values list to
        > the `Connection.execute()` method, which is supported by all database
        > backends and is generally more efficient for a very large number of
        > parameters.

        - https://docs.sqlalchemy.org/core/dml.html#sqlalchemy.sql.expression.Insert.values.params.*args
        """
        records = [{"name": f"foo_{i}"} for i in range(3)]
        insertable = self.mytable.insert().values(records)
        statement = str(insertable.compile(bind=self.crate_engine))
        self.assertEqual(statement, "INSERT INTO mytable (name) VALUES (?), (?), (?)")

    @skipIf(SA_VERSION < SA_2_0, "SQLAlchemy 1.x does not support the 'insertmanyvalues' dialect feature")
    def test_insert_manyvalues(self):
        """
        Verify the `use_insertmanyvalues` and `use_insertmanyvalues_wo_returning` dialect features.

        > For DML statements such as "INSERT", "UPDATE" and "DELETE", we can
        > send multiple parameter sets to the `Connection.execute()` method by
        > passing a list of dictionaries instead of a single dictionary, which
        > indicates that the single SQL statement should be invoked multiple
        > times, once for each parameter set. This style of execution is known
        > as "executemany".

        > A key characteristic of "insertmanyvalues" is that the size of the INSERT
        > statement is limited on a fixed max number of "values" clauses as well as
        > a dialect-specific fixed total number of bound parameters that may be
        > represented in one INSERT statement at a time.
        > When the number of parameter dictionaries given exceeds a fixed limit [...],
        > multiple INSERT statements will be invoked within the scope of a single
        > `Connection.execute()` call, each of which accommodate for a portion of the
        > parameter dictionaries, referred towards as a "batch".

        - https://docs.sqlalchemy.org/tutorial/dbapi_transactions.html#tutorial-multiple-parameters
        - https://docs.sqlalchemy.org/glossary.html#term-executemany
        - https://docs.sqlalchemy.org/core/connections.html#engine-insertmanyvalues
        - https://docs.sqlalchemy.org/core/connections.html#controlling-the-batch-size
        """

        # Don't truncate unittest's diff output on `assertListEqual`.
        self.maxDiff = None

        # Five records with a batch size of two should produce three `INSERT` statements.
        record_count = 5
        batch_size = 2

        # Prepare input data and verify insert statement.
        records = [{"name": f"foo_{i}"} for i in range(record_count)]
        insertable = self.mytable.insert()
        statement = str(insertable.compile(bind=self.crate_engine))
        self.assertEqual(statement, "INSERT INTO mytable (name, data) VALUES (?, ?)")

        with mock.patch("crate.client.http.Client.sql", autospec=True, return_value={"cols": []}) as client_mock:

            with self.crate_engine.begin() as conn:
                # Adjust page size on a per-connection level.
                conn.execution_options(insertmanyvalues_page_size=batch_size)
                conn.execute(insertable, parameters=records)

        # Verify that input data has been batched correctly.
        self.assertListEqual(client_mock.mock_calls, [
            mock.call(mock.ANY, 'INSERT INTO mytable (name) VALUES (?), (?)', ('foo_0', 'foo_1'), None),
            mock.call(mock.ANY, 'INSERT INTO mytable (name) VALUES (?), (?)', ('foo_2', 'foo_3'), None),
            mock.call(mock.ANY, 'INSERT INTO mytable (name) VALUES (?)', ('foo_4', ), None),
        ])
