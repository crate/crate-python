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
from datetime import datetime
from mock import patch, MagicMock

import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import select, insert

from crate.client.cursor import Cursor


fake_cursor = MagicMock(name='fake_cursor')
fake_cursor.rowcount = 1
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


class SqlAlchemyInsertFromSelectTest(TestCase):

    def assertSQL(self, expected_str, actual_expr):
        self.assertEquals(expected_str, str(actual_expr).replace('\n', ''))

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        Base = declarative_base(bind=self.engine)

        class Character(Base):
            __tablename__ = 'characters'

            name = sa.Column(sa.String, primary_key=True)
            age = sa.Column(sa.Integer)
            ts = sa.Column(sa.DateTime, onupdate=datetime.utcnow)
            status = sa.Column(sa.String)

        class CharacterArchive(Base):
            __tablename__ = 'characters_archive'

            name = sa.Column(sa.String, primary_key=True)
            age = sa.Column(sa.Integer)
            ts = sa.Column(sa.DateTime, onupdate=datetime.utcnow)
            status = sa.Column(sa.String)

        self.character = Character
        self.character_archived = CharacterArchive
        self.session = Session()

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_insert_from_select_triggered(self):
        char = self.character(name='Arthur', status='Archived')
        self.session.add(char)
        self.session.commit()

        sel = select([self.character.name, self.character.age]).where(self.character.status == "Archived")
        ins = insert(self.character_archived).from_select(['name', 'age'], sel)
        self.session.execute(ins)
        self.session.commit()
        self.assertSQL(
            "INSERT INTO characters_archive (name, age) (SELECT characters.name, characters.age FROM characters WHERE characters.status = ?)",
            ins
        )
