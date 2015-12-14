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
from mock import MagicMock

import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

from crate.client.sqlalchemy.types import Craty
from crate.client.sqlalchemy.predicates import match
from crate.client.cursor import Cursor


fake_cursor = MagicMock(name='fake_cursor')
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


class SqlAlchemyMatchTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        metadata = sa.MetaData()
        self.quotes = sa.Table('quotes', metadata,
                               sa.Column('author', sa.String),
                               sa.Column('quote', sa.String))
        self.session, self.Character = self.set_up_character_and_session()
        self.maxDiff = None

    def assertSQL(self, expected_str, actual_expr):
        self.assertEquals(expected_str, str(actual_expr).replace('\n', ''))

    def set_up_character_and_session(self):
        Base = declarative_base(bind=self.engine)

        class Character(Base):
            __tablename__ = 'characters'
            name = sa.Column(sa.String, primary_key=True)
            info = sa.Column(Craty)

        session = Session()
        return session, Character

    def test_simple_match(self):
        query = self.session.query(self.Character.name) \
                    .filter(match(self.Character.name, 'Trillian'))
        self.assertSQL(
            "SELECT characters.name AS characters_name FROM characters " +
            "WHERE match(characters.name, ?)",
            query
        )

    def test_match_boost(self):
        query = self.session.query(self.Character.name) \
            .filter(match({self.Character.name: 0.5}, 'Trillian'))
        self.assertSQL(
            "SELECT characters.name AS characters_name FROM characters " +
            "WHERE match((characters.name 0.5), ?)",
            query
        )

    def test_muli_match(self):
        query = self.session.query(self.Character.name) \
            .filter(match({self.Character.name: 0.5,
                           self.Character.info['race']: 0.9},
                          'Trillian'))
        self.assertSQL(
            "SELECT characters.name AS characters_name FROM characters " +
            "WHERE match(" +
            "(characters.info['race'] 0.9, characters.name 0.5), ?" +
            ")",
            query
        )

    def test_match_type_options(self):
        query = self.session.query(self.Character.name) \
            .filter(match({self.Character.name: 0.5,
                           self.Character.info['race']: 0.9},
                          'Trillian',
                          match_type='phrase',
                          options={'fuzziness': 3, 'analyzer': 'english'}))
        self.assertSQL(
            "SELECT characters.name AS characters_name FROM characters " +
            "WHERE match(" +
            "(characters.info['race'] 0.9, characters.name 0.5), ?" +
            ") using phrase with (analyzer=english, fuzziness=3)",
            query
        )

    def test_score(self):
        query = self.session.query(self.Character.name, '_score') \
                    .filter(match(self.Character.name, 'Trillian'))
        self.assertSQL(
            "SELECT characters.name AS characters_name, _score " +
            "FROM characters WHERE match(characters.name, ?)",
            query
        )

    def test_options_without_type(self):
        query = self.session.query(self.Character.name).filter(
            match({self.Character.name: 0.5, self.Character.info['race']: 0.9},
                  'Trillian',
                  options={'boost': 10.0})
        )
        err = None
        try:
            str(query)
        except ValueError as e:
            err = e
        msg = "missing match_type. " + \
              "It's not allowed to specify options without match_type"
        self.assertEquals(str(err), msg)
