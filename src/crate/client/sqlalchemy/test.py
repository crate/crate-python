
from __future__ import absolute_import
from unittest import TestCase, TestSuite, makeSuite
from mock import patch, MagicMock

import sqlalchemy as sa
from sqlalchemy.sql import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

from .types import Craty
from ..cursor import Cursor


fake_cursor = MagicMock(name='fake_cursor')
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


class SqlAlchemyConnectionTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        self.connection = self.engine.connect()

    def test_default_connection(self):
        engine = sa.create_engine('crate://')
        conn = engine.raw_connection()
        self.assertEquals("<Connection <Client ['127.0.0.1:9200']>>",
                          repr(conn.connection))

    def test_connection_server(self):
        engine = sa.create_engine(
            "crate://otherhost:19201")
        conn = engine.raw_connection()
        self.assertEquals("<Connection <Client ['otherhost:19201']>>",
                          repr(conn.connection))

    def test_connection_multiple_server(self):
        engine = sa.create_engine(
            "crate://", connect_args={
                'servers': ['localhost:9201', 'localhost:9202']
            }
        )
        conn = engine.raw_connection()
        self.assertEquals(
            "<Connection <Client ['localhost:9201', 'localhost:9202']>>",
            repr(conn.connection))


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
            "SELECT mytable.name FROM mytable WHERE mytable.data['x']['y'] = ?",
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
            "SELECT mytable.name FROM mytable WHERE mytable.data['x'] = mytable.name",
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

        session = Session()
        return session, Character

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
            "UPDATE characters SET characters.data = ? WHERE characters.name = ?",
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
        if only one attribute of Craty is changed the update should only update
        that attribute not all attributes of Craty
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
            ("UPDATE characters SET characters.age = ?, data['x'] = ? "
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

tests = TestSuite()
tests.addTest(makeSuite(SqlAlchemyConnectionTest))
tests.addTest(makeSuite(SqlAlchemyDictTypeTest))
