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

from __future__ import absolute_import
from unittest import TestCase, skipIf

import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.sql.operators import eq

from crate.client.sqlalchemy import SA_VERSION, SA_1_4
from crate.testing.settings import crate_host

try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

from crate.client.sqlalchemy.types import ObjectType, ObjectArray


class SqlAlchemyQueryCompilationCaching(TestCase):

    def setUp(self):
        self.engine = sa.create_engine(f"crate://{crate_host}")
        self.metadata = sa.MetaData(schema="testdrive")
        self.session = Session(bind=self.engine)
        self.Character = self.setup_entity()

    def setup_entity(self):
        """
        Define ORM entity.
        """
        Base = declarative_base(metadata=self.metadata)

        class Character(Base):
            __tablename__ = 'characters'
            name = sa.Column(sa.String, primary_key=True)
            age = sa.Column(sa.Integer)
            data = sa.Column(ObjectType)
            data_list = sa.Column(ObjectArray)

        return Character

    def setup_data(self):
        """
        Insert two records into the `characters` table.
        """
        self.metadata.drop_all(self.engine)
        self.metadata.create_all(self.engine)

        Character = self.Character
        char1 = Character(name='Trillian', data={'x': 1}, data_list=[{'foo': 1, 'bar': 10}])
        char2 = Character(name='Slartibartfast', data={'y': 2}, data_list=[{'bar': 2}])
        self.session.add(char1)
        self.session.add(char2)
        self.session.commit()
        self.session.execute(sa.text("REFRESH TABLE testdrive.characters;"))

    @skipIf(SA_VERSION < SA_1_4, "On SA13, the 'ResultProxy' object has no attribute 'scalar_one'")
    def test_object_multiple_select_legacy(self):
        """
        The SQLAlchemy implementation of CrateDB's `OBJECT` type offers indexed
        access to the instance's content in form of a dictionary. Thus, it must
        not use `cache_ok = True` on its implementation, i.e. this part of the
        compiled SQL clause must not be cached.

        This test verifies that two subsequent `SELECT` statements are translated
        well, and don't trip on incorrect SQL compiled statement caching.

        This variant uses direct value matching on the `OBJECT`s attribute.
        """
        self.setup_data()
        Character = self.Character

        selectable = sa.select(Character).where(Character.data['x'] == 1)
        result = self.session.execute(selectable).scalar_one().data
        self.assertEqual({"x": 1}, result)

        selectable = sa.select(Character).where(Character.data['y'] == 2)
        result = self.session.execute(selectable).scalar_one().data
        self.assertEqual({"y": 2}, result)

    @skipIf(SA_VERSION < SA_1_4, "On SA13, the 'ResultProxy' object has no attribute 'scalar_one'")
    def test_object_multiple_select_modern(self):
        """
        The SQLAlchemy implementation of CrateDB's `OBJECT` type offers indexed
        access to the instance's content in form of a dictionary. Thus, it must
        not use `cache_ok = True` on its implementation, i.e. this part of the
        compiled SQL clause must not be cached.

        This test verifies that two subsequent `SELECT` statements are translated
        well, and don't trip on incorrect SQL compiled statement caching.

        This variant uses comparator method matching on the `OBJECT`s attribute.
        """
        self.setup_data()
        Character = self.Character

        selectable = sa.select(Character).where(Character.data['x'].as_integer() == 1)
        result = self.session.execute(selectable).scalar_one().data
        self.assertEqual({"x": 1}, result)

        selectable = sa.select(Character).where(Character.data['y'].as_integer() == 2)
        result = self.session.execute(selectable).scalar_one().data
        self.assertEqual({"y": 2}, result)

    @skipIf(SA_VERSION < SA_1_4, "On SA13, the 'ResultProxy' object has no attribute 'scalar_one'")
    def test_objectarray_multiple_select(self):
        """
        The SQLAlchemy implementation of CrateDB's `ARRAY` type in form of the
        `ObjectArray`, does *not* offer indexed access to the instance's content.
        Thus, using `cache_ok = True` on that type should be sane, and not mess
        up SQLAlchemy's SQL compiled statement caching.
        """
        self.setup_data()
        Character = self.Character

        selectable = sa.select(Character).where(Character.data_list['foo'].any(1, operator=eq))
        result = self.session.execute(selectable).scalar_one().data
        self.assertEqual({"x": 1}, result)

        selectable = sa.select(Character).where(Character.data_list['bar'].any(2, operator=eq))
        result = self.session.execute(selectable).scalar_one().data
        self.assertEqual({"y": 2}, result)
