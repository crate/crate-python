
from __future__ import absolute_import
from unittest import TestCase

from sqlalchemy import create_engine


class SqlAlchemyTest(TestCase):

    def setUp(self):
        self.engine = create_engine('crate://')
        self.connection = self.engine.connect()

    def test_default_connection(self):
        engine = create_engine('crate://')
        conn = engine.raw_connection()
        self.assertEquals("<Connection <Client ['localhost:9200']>>",
                          repr(conn.connection))

    def test_connection_server(self):
        engine = create_engine(
            "crate://otherhost:19201")
        conn = engine.raw_connection()
        self.assertEquals("<Connection <Client ['otherhost:19201']>>",
                          repr(conn.connection))

    def test_connection_multiple_server(self):
        engine = create_engine(
            "crate://", connect_args={
                'servers': ['localhost:9201', 'localhost:9202']
            }
        )
        conn = engine.raw_connection()
        self.assertEquals(
            "<Connection <Client ['localhost:9201', 'localhost:9202']>>",
            repr(conn.connection))
