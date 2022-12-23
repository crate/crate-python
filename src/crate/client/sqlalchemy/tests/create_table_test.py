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

import sqlalchemy as sa
try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

from crate.client.sqlalchemy.types import Object, ObjectArray, Geopoint
from crate.client.cursor import Cursor

from unittest import TestCase
from unittest.mock import patch, MagicMock


fake_cursor = MagicMock(name='fake_cursor')
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


@patch('crate.client.connection.Cursor', FakeCursor)
class SqlAlchemyCreateTableTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        self.Base = declarative_base()

    def test_table_basic_types(self):
        class User(self.Base):
            __tablename__ = 'users'
            string_col = sa.Column(sa.String, primary_key=True)
            unicode_col = sa.Column(sa.Unicode)
            text_col = sa.Column(sa.Text)
            int_col = sa.Column(sa.Integer)
            long_col1 = sa.Column(sa.BigInteger)
            long_col2 = sa.Column(sa.NUMERIC)
            bool_col = sa.Column(sa.Boolean)
            short_col = sa.Column(sa.SmallInteger)
            datetime_col = sa.Column(sa.DateTime)
            date_col = sa.Column(sa.Date)
            float_col = sa.Column(sa.Float)
            double_col = sa.Column(sa.DECIMAL)

        self.Base.metadata.create_all(bind=self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE users (\n\tstring_col STRING NOT NULL, '
             '\n\tunicode_col STRING, \n\ttext_col STRING, \n\tint_col INT, '
             '\n\tlong_col1 LONG, \n\tlong_col2 LONG, '
             '\n\tbool_col BOOLEAN, '
             '\n\tshort_col SHORT, '
             '\n\tdatetime_col TIMESTAMP, \n\tdate_col TIMESTAMP, '
             '\n\tfloat_col FLOAT, \n\tdouble_col DOUBLE, '
             '\n\tPRIMARY KEY (string_col)\n)\n\n'),
            ())

    def test_column_obj(self):
        class DummyTable(self.Base):
            __tablename__ = 'dummy'
            pk = sa.Column(sa.String, primary_key=True)
            obj_col = sa.Column(Object)
        self.Base.metadata.create_all(bind=self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE dummy (\n\tpk STRING NOT NULL, \n\tobj_col OBJECT, '
             '\n\tPRIMARY KEY (pk)\n)\n\n'),
            ())

    def test_table_clustered_by(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            __table_args__ = {
                'crate_clustered_by': 'p'
            }
            pk = sa.Column(sa.String, primary_key=True)
            p = sa.Column(sa.String)
        self.Base.metadata.create_all(bind=self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'pk STRING NOT NULL, \n\t'
             'p STRING, \n\t'
             'PRIMARY KEY (pk)\n'
             ') CLUSTERED BY (p)\n\n'),
            ())

    def test_column_computed(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            ts = sa.Column(sa.BigInteger, primary_key=True)
            p = sa.Column(sa.BigInteger, sa.Computed("date_trunc('day', ts)"))
        self.Base.metadata.create_all(bind=self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'ts LONG NOT NULL, \n\t'
             'p LONG GENERATED ALWAYS AS (date_trunc(\'day\', ts)), \n\t'
             'PRIMARY KEY (ts)\n'
             ')\n\n'),
            ())

    def test_column_computed_virtual(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            ts = sa.Column(sa.BigInteger, primary_key=True)
            p = sa.Column(sa.BigInteger, sa.Computed("date_trunc('day', ts)", persisted=False))
        with self.assertRaises(sa.exc.CompileError):
            self.Base.metadata.create_all(bind=self.engine)

    def test_table_partitioned_by(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            __table_args__ = {
                'crate_partitioned_by': 'p',
                'invalid_option': 1
            }
            pk = sa.Column(sa.String, primary_key=True)
            p = sa.Column(sa.String)
        self.Base.metadata.create_all(bind=self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'pk STRING NOT NULL, \n\t'
             'p STRING, \n\t'
             'PRIMARY KEY (pk)\n'
             ') PARTITIONED BY (p)\n\n'),
            ())

    def test_table_number_of_shards_and_replicas(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            __table_args__ = {
                'crate_number_of_replicas': '2',
                'crate_number_of_shards': 3
            }
            pk = sa.Column(sa.String, primary_key=True)

        self.Base.metadata.create_all(bind=self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'pk STRING NOT NULL, \n\t'
             'PRIMARY KEY (pk)\n'
             ') CLUSTERED INTO 3 SHARDS WITH (NUMBER_OF_REPLICAS = 2)\n\n'),
            ())

    def test_table_clustered_by_and_number_of_shards(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            __table_args__ = {
                'crate_clustered_by': 'p',
                'crate_number_of_shards': 3
            }
            pk = sa.Column(sa.String, primary_key=True)
            p = sa.Column(sa.String, primary_key=True)
        self.Base.metadata.create_all(bind=self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'pk STRING NOT NULL, \n\t'
             'p STRING NOT NULL, \n\t'
             'PRIMARY KEY (pk, p)\n'
             ') CLUSTERED BY (p) INTO 3 SHARDS\n\n'),
            ())

    def test_column_object_array(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            pk = sa.Column(sa.String, primary_key=True)
            tags = sa.Column(ObjectArray)

        self.Base.metadata.create_all(bind=self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'pk STRING NOT NULL, \n\t'
             'tags ARRAY(OBJECT), \n\t'
             'PRIMARY KEY (pk)\n)\n\n'), ())

    def test_column_nullable(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            pk = sa.Column(sa.String, primary_key=True)
            a = sa.Column(sa.Integer, nullable=True)
            b = sa.Column(sa.Integer, nullable=False)

        self.Base.metadata.create_all(bind=self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'pk STRING NOT NULL, \n\t'
             'a INT, \n\t'
             'b INT NOT NULL, \n\t'
             'PRIMARY KEY (pk)\n)\n\n'), ())

    def test_column_pk_nullable(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            pk = sa.Column(sa.String, primary_key=True, nullable=True)
        with self.assertRaises(sa.exc.CompileError):
            self.Base.metadata.create_all(bind=self.engine)

    def test_column_crate_index(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            pk = sa.Column(sa.String, primary_key=True)
            a = sa.Column(sa.Integer, crate_index=False)
            b = sa.Column(sa.Integer, crate_index=True)

        self.Base.metadata.create_all(bind=self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'pk STRING NOT NULL, \n\t'
             'a INT INDEX OFF, \n\t'
             'b INT, \n\t'
             'PRIMARY KEY (pk)\n)\n\n'), ())

    def test_column_geopoint_without_index(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            pk = sa.Column(sa.String, primary_key=True)
            a = sa.Column(Geopoint, crate_index=False)
        with self.assertRaises(sa.exc.CompileError):
            self.Base.metadata.create_all(bind=self.engine)
