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
from unittest import TestCase
from mock import patch, MagicMock

import sqlalchemy as sa
from sqlalchemy.sql import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

from crate.client.sqlalchemy.types import Craty, ObjectArray
from crate.client.cursor import Cursor


fake_cursor = MagicMock(name='fake_cursor')
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


class SqlAlchemyDictTypeTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        metadata = sa.MetaData()
        self.mytable = sa.Table('mytable', metadata,
                                sa.Column('name', sa.String),
                                sa.Column('data', Craty))

    def assertSQL(self, expected_str, actual_expr):
        self.assertEquals(expected_str, str(actual_expr).replace('\n', ''))

    def test_select_with_dict_column(self):
        mytable = self.mytable
        self.assertSQL(
            "SELECT mytable.data['x'] AS anon_1 FROM mytable",
            select([mytable.c.data['x']], bind=self.engine)
        )

    def test_select_with_dict_column_where_clause(self):
        mytable = self.mytable
        s = select([mytable.c.data], bind=self.engine).\
            where(mytable.c.data['x'] == 1)
        self.assertSQL(
            "SELECT mytable.data FROM mytable WHERE mytable.data['x'] = ?",
            s
        )

    def test_select_with_dict_column_nested_where(self):
        mytable = self.mytable
        s = select([mytable.c.name], bind=self.engine)
        s = s.where(mytable.c.data['x']['y'] == 1)
        self.assertSQL(
            "SELECT mytable.name FROM mytable " +
            "WHERE mytable.data['x']['y'] = ?",
            s
        )

    def test_select_with_dict_column_where_clause_gt(self):
        mytable = self.mytable
        s = select([mytable.c.data], bind=self.engine).\
            where(mytable.c.data['x'] > 1)
        self.assertSQL(
            "SELECT mytable.data FROM mytable WHERE mytable.data['x'] > ?",
            s
        )

    def test_select_with_dict_column_where_clause_other_col(self):
        mytable = self.mytable
        s = select([mytable.c.name], bind=self.engine)
        s = s.where(mytable.c.data['x'] == mytable.c.name)
        self.assertSQL(
            "SELECT mytable.name FROM mytable " +
            "WHERE mytable.data['x'] = mytable.name",
            s
        )

    def test_update_with_dict_column(self):
        mytable = self.mytable
        stmt = mytable.update(bind=self.engine).\
            where(mytable.c.name == 'Arthur Dent').\
            values({
                "data['x']": "Trillian"
            })
        self.assertSQL(
            "UPDATE mytable SET data['x'] = ? WHERE mytable.name = ?",
            stmt
        )

    def set_up_character_and_cursor(self, return_value=None):
        return_value = return_value or [('Trillian', {})]
        fake_cursor.fetchall.return_value = return_value
        fake_cursor.description = (
            ('characters_name', None, None, None, None, None, None),
            ('characters_data', None, None, None, None, None, None)
        )
        fake_cursor.rowcount = 1
        Base = declarative_base(bind=self.engine)

        class Character(Base):
            __tablename__ = 'characters'
            name = sa.Column(sa.String, primary_key=True)
            age = sa.Column(sa.Integer)
            data = sa.Column(Craty)
            data_list = sa.Column(ObjectArray)

        session = Session()
        return session, Character

    def test_assign_null_to_object_array(self):
        session, Character = self.set_up_character_and_cursor()
        char_1 = Character(name='Trillian', data_list=None)
        self.assertTrue(char_1.data_list is None)
        char_2 = Character(name='Trillian', data_list=1)
        self.assertTrue(char_2.data_list == [1])
        char_3 = Character(name='Trillian', data_list=[None])
        self.assertTrue(char_3.data_list == [None])

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_assign_to_craty_type_after_commit(self):
        session, Character = self.set_up_character_and_cursor(
            return_value=[('Trillian', None, None)]
        )
        char = Character(name='Trillian')
        session.add(char)
        session.commit()
        char.data = {'x': 1}
        self.assertTrue(char in session.dirty)
        session.commit()
        fake_cursor.execute.assert_called_with(
            "UPDATE characters SET data = ? WHERE characters.name = ?",
            ({'x': 1}, 'Trillian',)
        )

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_change_tracking(self):
        session, Character = self.set_up_character_and_cursor()
        char = Character(name='Trillian')
        session.add(char)
        session.commit()

        try:
            char.data['x'] = 1
        except Exception:
            print(fake_cursor.fetchall.called)
            print(fake_cursor.mock_calls)
            raise

        self.assertTrue(char in session.dirty)
        try:
            session.commit()
        except Exception:
            print(fake_cursor.mock_calls)
            raise
        self.assertFalse(char in session.dirty)

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_partial_dict_update(self):
        session, Character = self.set_up_character_and_cursor()
        char = Character(name='Trillian')
        session.add(char)
        session.commit()
        char.data['x'] = 1
        char.data['y'] = 2
        session.commit()

        # on python 3 dicts aren't sorted so the order if x or y is updated
        # first isn't deterministic
        try:
            fake_cursor.execute.assert_called_with(
                ("UPDATE characters SET data['y'] = ?, data['x'] = ? "
                    "WHERE characters.name = ?"),
                (2, 1, 'Trillian')
            )
        except AssertionError:
            fake_cursor.execute.assert_called_with(
                ("UPDATE characters SET data['x'] = ?, data['y'] = ? "
                    "WHERE characters.name = ?"),
                (1, 2, 'Trillian')
            )

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_partial_dict_update_only_one_key_changed(self):
        """
        If only one attribute of Crate is changed
        the update should only update that attribute
        not all attributes of Crate.
        """
        session, Character = self.set_up_character_and_cursor(
            return_value=[('Trillian', dict(x=1, y=2))]
        )

        char = Character(name='Trillian')
        char.data = dict(x=1, y=2)
        session.add(char)
        session.commit()
        char.data['y'] = 3
        session.commit()
        fake_cursor.execute.assert_called_with(
            ("UPDATE characters SET data['y'] = ? "
             "WHERE characters.name = ?"),
            (3, 'Trillian')
        )

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_partial_dict_update_with_regular_column(self):
        session, Character = self.set_up_character_and_cursor()

        char = Character(name='Trillian')
        session.add(char)
        session.commit()
        char.data['x'] = 1
        char.age = 20
        session.commit()
        fake_cursor.execute.assert_called_with(
            ("UPDATE characters SET age = ?, data['x'] = ? "
             "WHERE characters.name = ?"),
            (20, 1, 'Trillian')
        )

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_partial_dict_update_with_delitem(self):
        session, Character = self.set_up_character_and_cursor(
            return_value=[('Trillian', {'x': 1})]
        )

        char = Character(name='Trillian')
        char.data = {'x': 1}
        session.add(char)
        session.commit()
        del char.data['x']
        self.assertTrue(char in session.dirty)
        session.commit()
        fake_cursor.execute.assert_called_with(
            ("UPDATE characters SET data['x'] = ? "
             "WHERE characters.name = ?"),
            (None, 'Trillian')
        )

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_partial_dict_update_with_delitem_setitem(self):
        """ test that the change tracking doesn't get messed up

        delitem -> setitem
        """
        session, Character = self.set_up_character_and_cursor(
            return_value=[('Trillian', {'x': 1})]
        )

        session = Session()
        char = Character(name='Trillian')
        char.data = {'x': 1}
        session.add(char)
        session.commit()
        del char.data['x']
        char.data['x'] = 4
        self.assertTrue(char in session.dirty)
        session.commit()
        fake_cursor.execute.assert_called_with(
            ("UPDATE characters SET data['x'] = ? "
             "WHERE characters.name = ?"),
            (4, 'Trillian')
        )

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_partial_dict_update_with_setitem_delitem(self):
        """ test that the change tracking doesn't get messed up

        setitem -> delitem
        """
        session, Character = self.set_up_character_and_cursor(
            return_value=[('Trillian', {'x': 1})]
        )

        char = Character(name='Trillian')
        char.data = {'x': 1}
        session.add(char)
        session.commit()
        char.data['x'] = 4
        del char.data['x']
        self.assertTrue(char in session.dirty)
        session.commit()
        fake_cursor.execute.assert_called_with(
            ("UPDATE characters SET data['x'] = ? "
             "WHERE characters.name = ?"),
            (None, 'Trillian')
        )

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_partial_dict_update_with_setitem_delitem_setitem(self):
        """ test that the change tracking doesn't get messed up

        setitem -> delitem -> setitem
        """
        session, Character = self.set_up_character_and_cursor(
            return_value=[('Trillian', {'x': 1})]
        )

        char = Character(name='Trillian')
        char.data = {'x': 1}
        session.add(char)
        session.commit()
        char.data['x'] = 4
        del char.data['x']
        char.data['x'] = 3
        self.assertTrue(char in session.dirty)
        session.commit()
        fake_cursor.execute.assert_called_with(
            ("UPDATE characters SET data['x'] = ? "
             "WHERE characters.name = ?"),
            (3, 'Trillian')
        )

    def set_up_character_and_cursor_data_list(self, return_value=None):
        return_value = return_value or [('Trillian', {})]
        fake_cursor.fetchall.return_value = return_value
        fake_cursor.description = (
            ('characters_name', None, None, None, None, None, None),
            ('characters_data_list', None, None, None, None, None, None)

        )
        fake_cursor.rowcount = 1
        Base = declarative_base(bind=self.engine)

        class Character(Base):
            __tablename__ = 'characters'
            name = sa.Column(sa.String, primary_key=True)
            data_list = sa.Column(ObjectArray)

        session = Session()
        return session, Character

    def _setup_object_array_char(self):
        session, Character = self.set_up_character_and_cursor_data_list(
            return_value=[('Trillian', [{'1': 1}, {'2': 2}])]
        )
        char = Character(name='Trillian', data_list=[{'1': 1}, {'2': 2}])
        session.add(char)
        session.commit()
        return session, char

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_object_array_setitem_change_tracking(self):
        session, char = self._setup_object_array_char()
        char.data_list[1] = {'3': 3}
        self.assertTrue(char in session.dirty)
        session.commit()
        fake_cursor.execute.assert_called_with(
            ("UPDATE characters SET data_list = ? "
             "WHERE characters.name = ?"),
            ([{'1': 1}, {'3': 3}], 'Trillian')
        )

    def _setup_nested_object_char(self):
        session, Character = self.set_up_character_and_cursor(
            return_value=[('Trillian', {'nested': {'x': 1, 'y': {'z': 2}}})]
        )
        char = Character(name='Trillian')
        char.data = {'nested': {'x': 1, 'y': {'z': 2}}}
        session.add(char)
        session.commit()
        return session, char


    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_nested_object_change_tracking(self):
        session, char = self._setup_nested_object_char()
        char.data["nested"]["x"] = 3
        self.assertTrue(char in session.dirty)
        session.commit()
        fake_cursor.execute.assert_called_with(
            ("UPDATE characters SET data['nested'] = ? "
             "WHERE characters.name = ?"),
            ({'y': {'z': 2}, 'x': 3}, 'Trillian')
        )


    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_deep_nested_object_change_tracking(self):
        session, char = self._setup_nested_object_char()
        # change deep nested object
        char.data["nested"]["y"]["z"] = 5
        self.assertTrue(char in session.dirty)
        session.commit()
        fake_cursor.execute.assert_called_with(
            ("UPDATE characters SET data['nested'] = ? "
             "WHERE characters.name = ?"),
            ({'y': {'z': 5}, 'x': 1}, 'Trillian')
        )

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_delete_nested_object_tracking(self):
        session, char = self._setup_nested_object_char()
        # delete nested object
        del char.data["nested"]["y"]["z"]
        self.assertTrue(char in session.dirty)
        session.commit()
        fake_cursor.execute.assert_called_with(
            ("UPDATE characters SET data['nested'] = ? "
             "WHERE characters.name = ?"),
            ({'y': {}, 'x': 1}, 'Trillian')
        )


    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_object_array_append_change_tracking(self):
        session, char = self._setup_object_array_char()
        char.data_list.append({'3': 3})
        self.assertTrue(char in session.dirty)

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_object_array_insert_change_tracking(self):
        session, char = self._setup_object_array_char()
        char.data_list.insert(0, {'3': 3})
        self.assertTrue(char in session.dirty)

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_object_array_slice_change_tracking(self):
        session, char = self._setup_object_array_char()
        char.data_list[:] = [{'3': 3}]
        self.assertTrue(char in session.dirty)

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_object_array_extend_change_tracking(self):
        session, char = self._setup_object_array_char()
        char.data_list.extend([{'3': 3}])
        self.assertTrue(char in session.dirty)

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_object_array_pop_change_tracking(self):
        session, char = self._setup_object_array_char()
        char.data_list.pop()
        self.assertTrue(char in session.dirty)

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_object_array_remove_change_tracking(self):
        session, char = self._setup_object_array_char()
        item = char.data_list[0]
        char.data_list.remove(item)
        self.assertTrue(char in session.dirty)
