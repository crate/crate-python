
from unittest import TestCase
from datetime import datetime
from mock import patch, MagicMock

import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

from crate.client.cursor import Cursor


fake_cursor = MagicMock(name='fake_cursor')
fake_cursor.rowcount = 1
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


class SqlAlchemyUpdateTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        Base = declarative_base(bind=self.engine)

        class Character(Base):
            __tablename__ = 'characters'

            name = sa.Column(sa.String, primary_key=True)
            age = sa.Column(sa.Integer)
            ts = sa.Column(sa.DateTime, onupdate=datetime.utcnow)

        self.character = Character
        self.session = Session()

    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_onupdate_is_triggered(self):
        char = self.character(name='Arthur')
        self.session.add(char)
        self.session.commit()
        now = datetime.utcnow()

        fake_cursor.fetchall.return_value = [('Arthur', None)]
        fake_cursor.description = (
            ('characters_name', None, None, None, None, None, None),
            ('characters_ts', None, None, None, None, None, None),
        )

        char.age = 40
        self.session.commit()

        expected_stmt = ("UPDATE characters SET age = ?, "
                          "ts = ? WHERE characters.name = ?")
        args, kwargs = fake_cursor.execute.call_args
        stmt = args[0]
        args = args[1]
        self.assertEqual(expected_stmt, stmt)
        self.assertEqual(40, args[0])
        dt = datetime.strptime(args[1], '%Y-%m-%dT%H:%M:%S.%fZ') 
        self.assertTrue(isinstance(dt, datetime))
        self.assertTrue(dt > now)
        self.assertEqual('Arthur', args[2])
