
from __future__ import absolute_import
from unittest import TestCase, TestSuite, makeSuite
from mock import patch, MagicMock

import sqlalchemy as sa
from sqlalchemy.sql import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableDict

from .types import Dict
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
                                sa.Column('data', Dict))

    def setUpCharacter(self):
        Base = declarative_base(bind=self.engine)
        class Character(Base):
            __tablename__ = 'characters'
            name = sa.Column(sa.String, primary_key=True)
            data = sa.Column(MutableDict.as_mutable(Dict))
        self.Character = Character

    def test_select_with_dict_column(self):
        mytable = self.mytable
        s = select([mytable.c.data['x']], bind=self.engine)
        self.assertEquals(
            "SELECT mytable.data['x'] AS anon_1 FROM mytable",
            str(s).replace('\n', '')
        )

    def test_select_with_dict_column_where_clause(self):
        mytable = self.mytable
        s = select([mytable.c.data], bind=self.engine).\
            where(mytable.c.data['x'] == 1)
        self.assertEquals(
            "SELECT mytable.data FROM mytable WHERE mytable.data['x'] = ?",
            str(s).replace('\n', '')
        )

    def test_select_with_dict_column_nested_where(self):
        mytable = self.mytable
        s = select([mytable.c.name], bind=self.engine)
        s = s.where(mytable.c.data['x']['y'] == 1)
        self.assertEquals(
            "SELECT mytable.name FROM mytable WHERE mytable.data['x']['y'] = ?",
            str(s).replace('\n', '')
        )

    def test_select_with_dict_column_where_clause_gt(self):
        mytable = self.mytable
        s = select([mytable.c.data], bind=self.engine).\
            where(mytable.c.data['x'] > 1)
        self.assertEquals(
            "SELECT mytable.data FROM mytable WHERE mytable.data['x'] > ?",
            str(s).replace('\n', '')
        )

    def test_select_with_dict_column_where_clause_other_col(self):
        mytable = self.mytable
        s = select([mytable.c.name], bind=self.engine)
        s = s.where(mytable.c.data['x'] == mytable.c.name)
        self.assertEquals(
            "SELECT mytable.name FROM mytable WHERE mytable.data['x'] = mytable.name",
            str(s).replace('\n', '')
        )

    def test_update_with_dict_column(self):
        mytable = self.mytable
        stmt = mytable.update().\
            where(mytable.c.name == 'Arthur Dent').\
            values({
                "data['x']": "Trillian"
            })
        self.assertEquals(
            "UPDATE foo",
            str(stmt)
        )

    def setUp_fake_cursor(self):
        fake_cursor.fetchall.return_value = [('Trillian', {})]
        fake_cursor.description = (
            ('characters_name', None, None, None, None, None, None),
            ('characters_data', None, None, None, None, None, None)
        )
        fake_cursor.rowcount = 1

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_change_tracking(self):
        self.setUpCharacter()
        self.setUp_fake_cursor()

        sess = Session()
        char = self.Character(name='Trillian')
        sess.add(char)
        sess.commit()

        try:
            char.data['x'] = 1
        except Exception:
            print(fake_cursor.fetchall.called)
            print(fake_cursor.mock_calls)
            raise

        self.assertTrue(char in sess.dirty)
        try:
            sess.commit()
        except Exception:
            print(fake_cursor.mock_calls)
            raise
        self.assertFalse(char in sess.dirty)

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_partial_dict_update(self):
        self.setUpCharacter()
        self.setUp_fake_cursor()

        sess = Session()
        char = self.Character(name='Trillian')
        sess.add(char)
        sess.commit()
        char.data['x'] = 1
        sess.commit()
        fake_cursor.execute.assert_called_with(
            "UPDATE characters SET data['x']=? WHERE characters.name = ?",
            (1, 'Trillian')
        )


tests = TestSuite()
tests.addTest(makeSuite(SqlAlchemyConnectionTest))
tests.addTest(makeSuite(SqlAlchemyDictTypeTest))
