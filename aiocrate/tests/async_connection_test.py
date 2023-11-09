from unittest import TestCase
from sqlalchemy.ext.asyncio import create_async_engine
import sqlalchemy as sa


class SqlAlchemyAsyncConnectionTest(TestCase):

    def setUp(self):
        #self.async_engine = create_async_engine('crate+aiocrate://')
        #self.connection = self.engine.connect()
        pass

    # def test_default_sqllite_connection(self):
    #     async_engine = create_async_engine('sqlite+aiosqlite://')
    #     import pdb;pdb.set_trace()
    #     conn = async_engine.raw_connection()
    #     self.assertEqual("<Connection <Client ['http://127.0.0.1:4200']>>",
    #                      repr(conn.connection))

    def test_default_connection(self):
        async_engine = create_async_engine('sqlite+aiosqlite://')
        #import pdb;pdb.set_trace()
        #engine = sa.create_engine('crate://')
        #import pdb;pdb.set_trace()
        engine = sa.create_engine('crate+aiocrate://')
        import pdb;pdb.set_trace()
        async_engine = create_async_engine('crate+aiocrate://')

        conn = engine.raw_connection()
        self.assertEqual("<Connection <Client ['http://127.0.0.1:4200']>>",
                         repr(conn.connection))

    # def test_connection_server(self):
    #     async_engine = create_async_engine("crate+aiocrate://otherhost:19201")
    #     conn = async_engine.raw_connection()
    #     self.assertEqual("<Connection <Client ['http://otherhost:19201']>>",
    #                      repr(conn.connection))
    #
    # def test_connection_multiple_server(self):
    #     async_engine = create_async_engine(
    #         "crate+aiocrate://", connect_args={
    #             'servers': ['localhost:4201', 'localhost:4202']
    #         }
    #     )
    #     conn = async_engine.raw_connection()
    #     self.assertEqual(
    #         "<Connection <Client ['http://localhost:4201', " +
    #         "'http://localhost:4202']>>",
    #         repr(conn.connection))
