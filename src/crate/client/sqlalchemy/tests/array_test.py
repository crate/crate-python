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


from mock import patch, MagicMock
from unittest import TestCase

import sqlalchemy as sa
from sqlalchemy.sql import operators
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

from crate.client.cursor import Cursor

fake_cursor = MagicMock(name='fake_cursor')
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


@patch('crate.client.connection.Cursor', FakeCursor)
class SqlAlchemyArrayTypeTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        Base = declarative_base(bind=self.engine)
        self.metadata = sa.MetaData()

        class User(Base):
                __tablename__ = 'users'

                name = sa.Column(sa.String, primary_key=True)
                friends = sa.Column(sa.ARRAY(sa.String))
                scores = sa.Column(sa.ARRAY(sa.Integer))

        self.User = User
        self.session = Session()

    def assertSQL(self, expected_str, actual_expr):
            self.assertEquals(expected_str, str(actual_expr).replace('\n', ''))


    def test_create_with_array(self):
        t1 = sa.Table('t', self.metadata,
                      sa.Column('int_array', sa.ARRAY(sa.Integer)),
                      sa.Column('str_array', sa.ARRAY(sa.String))
                      )
        t1.create(self.engine)
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'int_array ARRAY(INT), \n\t'
             'str_array ARRAY(STRING)\n)\n\n'),
            ())

    def test_array_insert(self):
        trillian = self.User(name='Trillian', friends=['Arthur', 'Ford'])
        self.session.add(trillian)
        self.session.commit()
        fake_cursor.execute.assert_called_with(
            ("INSERT INTO users (name, friends, scores) VALUES (?, ?, ?)"),
            ('Trillian', ['Arthur', 'Ford'], None))

    def test_any(self):
        s = self.session.query(self.User.name) \
                .filter(self.User.friends.any("arthur"))
        self.assertSQL(
            "SELECT users.name AS users_name FROM users "
            "WHERE ? = ANY (users.friends)",
            s
        )

    def test_any_with_operator(self):
        s = self.session.query(self.User.name) \
                .filter(self.User.scores.any(6, operator=operators.lt))
        self.assertSQL(
            "SELECT users.name AS users_name FROM users "
            "WHERE ? < ANY (users.scores)",
            s
        )

    def test_multidimensional_arrays(self):
        t1 = sa.Table('t', self.metadata,
                      sa.Column('unsupported_array',
                                sa.ARRAY(sa.Integer, dimensions=2)),
                      )
        err = None
        try:
            t1.create(self.engine)
        except NotImplementedError as e:
            err = e
        self.assertEquals(str(err),
                          "CrateDB doesn't support multidimensional arrays")
