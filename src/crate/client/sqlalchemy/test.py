
from __future__ import absolute_import
from unittest import TestCase

import sqlalchemy as sa
from sqlalchemy.sql import select

from .types import Dict


class SqlAlchemyTest(TestCase):

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

    def test_select_with_dict_column(self):
        metadata = sa.MetaData()
        mytable = sa.Table('mytable', metadata,
                           sa.Column('data', Dict))
        s = select([mytable.c.data['x']], bind=self.engine)
        self.assertEquals(
            "SELECT mytable.data['x'] AS anon_1 FROM mytable",
            str(s).replace('\n', '')
        )

    def test_select_with_dict_column_where_clause(self):
        metadata = sa.MetaData()
        mytable = sa.Table('mytable', metadata,
                           sa.Column('data', Dict))
        s = select([mytable], bind=self.engine).where(mytable.c.data['x'] == 1)
        self.assertEquals(
            "SELECT mytable.data FROM mytable WHERE mytable.data['x'] = ?",
            str(s).replace('\n', '')
        )

    def test_select_with_dict_column_where_clause_gt(self):
        metadata = sa.MetaData()
        mytable = sa.Table('mytable', metadata,
                           sa.Column('data', Dict))
        s = select([mytable], bind=self.engine).where(mytable.c.data['x'] > 1)
        self.assertEquals(
            "SELECT mytable.data FROM mytable WHERE mytable.data['x'] > ?",
            str(s).replace('\n', '')
        )

    def test_select_with_dict_column_where_clause_other_col(self):
        metadata = sa.MetaData()
        mytable = sa.Table('mytable', metadata,
                           sa.Column('name', sa.String),
                           sa.Column('data', Dict))
        s = select([mytable.c.name], bind=self.engine)
        s = s.where(mytable.c.data['x'] == mytable.c.name)
        self.assertEquals(
            "SELECT mytable.name FROM mytable WHERE mytable.data['x'] = mytable.name",
            str(s).replace('\n', '')
        )
