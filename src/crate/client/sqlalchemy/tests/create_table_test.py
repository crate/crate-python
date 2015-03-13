import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

from crate.client.sqlalchemy.types import Object
from crate.client.cursor import Cursor

from mock import patch, MagicMock
from unittest import TestCase


fake_cursor = MagicMock(name='fake_cursor')
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor)
FakeCursor.return_value = fake_cursor


@patch('crate.client.connection.Cursor', FakeCursor)
class CreateTableTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        self.Base = declarative_base(bind=self.engine)

    def test_create_table_with_basic_types(self):
        class User(self.Base):
            __tablename__ = 'users'
            string_col = sa.Column(sa.String, primary_key=True)
            unicode_col = sa.Column(sa.Unicode)
            text_col = sa.Column(sa.Text)
            int_col = sa.Column(sa.Integer)
            long_col = sa.Column(sa.BigInteger)
            bool_col = sa.Column(sa.Boolean)
            short_col = sa.Column(sa.SmallInteger)
            ts_col = sa.Column(sa.DateTime)
            float_col = sa.Column(sa.Float)

        self.Base.metadata.create_all()
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE users (\n\tstring_col STRING, '
             '\n\tunicode_col STRING, \n\ttext_col STRING, \n\tint_col INT, '
             '\n\tlong_col LONG, \n\tbool_col BOOLEAN, '
             '\n\tshort_col SHORT, \n\tts_col TIMESTAMP, '
             '\n\tfloat_col FLOAT, \n\tPRIMARY KEY (string_col)\n)\n\n'
             ),
            ()
        )

    def test_with_obj_column(self):
        class DummyTable(self.Base):
            __tablename__ = 'dummy'
            pk = sa.Column(sa.String, primary_key=True)
            obj_col = sa.Column(Object)
        self.Base.metadata.create_all()
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE dummy (\n\tpk STRING, \n\tobj_col OBJECT, '
             '\n\tPRIMARY KEY (pk)\n)\n\n'),
            ()
        )

    def test_with_clustered_by(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            __table_args__ = {
                'crate_clustered_by': 'p'
            }
            pk = sa.Column(sa.String, primary_key=True)
            p = sa.Column(sa.String)
        self.Base.metadata.create_all()
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'pk STRING, \n\t'
             'p STRING, \n\t'
             'PRIMARY KEY (pk)\n'
             ') CLUSTERED BY (p)\n\n'), ())

    def test_with_partitioned_by(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            __table_args__ = {
                'crate_partitioned_by': 'p',
                'invalid_option': 1
            }
            pk = sa.Column(sa.String, primary_key=True)
            p = sa.Column(sa.String)
        self.Base.metadata.create_all()
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'pk STRING, \n\t'
             'p STRING, \n\t'
             'PRIMARY KEY (pk)\n'
             ') PARTITIONED BY (p)\n\n'), ())

    def test_with_number_of_shards_and_replicas(self):
        class DummyTable(self.Base):
            __tablename__ = 't'
            __table_args__ = {
                'crate_number_of_replicas': '2',
                'crate_number_of_shards': 3
            }
            pk = sa.Column(sa.String, primary_key=True)

        self.Base.metadata.create_all()
        fake_cursor.execute.assert_called_with(
            ('\nCREATE TABLE t (\n\t'
             'pk STRING, \n\t'
             'PRIMARY KEY (pk)\n'
             ') CLUSTERED INTO 3 SHARDS WITH (NUMBER_OF_REPLICAS = 2)\n\n'), ())
