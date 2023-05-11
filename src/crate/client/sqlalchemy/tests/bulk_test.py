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
import math
import sys
from unittest import TestCase, skipIf
from unittest.mock import patch, MagicMock

import sqlalchemy as sa
from sqlalchemy.orm import Session

from crate.client.sqlalchemy.sa_version import SA_VERSION, SA_2_0, SA_1_4

try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

from crate.client.cursor import Cursor


fake_cursor = MagicMock(name='fake_cursor')
FakeCursor = MagicMock(name='FakeCursor', spec=Cursor, return_value=fake_cursor)


class SqlAlchemyBulkTest(TestCase):

    def setUp(self):
        self.engine = sa.create_engine('crate://')
        Base = declarative_base()

        class Character(Base):
            __tablename__ = 'characters'

            name = sa.Column(sa.String, primary_key=True)
            age = sa.Column(sa.Integer)

        self.character = Character
        self.session = Session(bind=self.engine)

    @skipIf(SA_VERSION >= SA_2_0, "SQLAlchemy 2.x uses modern bulk INSERT mode")
    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_bulk_save_legacy(self):
        """
        Verify legacy SQLAlchemy bulk INSERT mode.

        > bulk_save_objects: Perform a bulk save of the given list of objects.
        > This method is a legacy feature as of the 2.0 series of SQLAlchemy. For modern
        > bulk INSERT and UPDATE, see the sections ORM Bulk INSERT Statements and ORM Bulk
        > UPDATE by Primary Key.
        >
        > -- https://docs.sqlalchemy.org/orm/session_api.html#sqlalchemy.orm.Session.bulk_save_objects

        > The Session includes legacy methods for performing "bulk" INSERT and UPDATE
        > statements. These methods share implementations with the SQLAlchemy 2.0
        > versions of these features, described at ORM Bulk INSERT Statements and
        > ORM Bulk UPDATE by Primary Key, however lack many features, namely RETURNING
        > support as well as support for session-synchronization.
        >
        > -- https://docs.sqlalchemy.org/orm/queryguide/dml.html#legacy-session-bulk-insert-methods

        > The 1.4 version of the "ORM bulk insert" methods are really not very efficient and
        > don't grant that much of a performance bump vs. regular ORM `session.add()`, provided
        > in both cases the objects you provide already have their primary key values assigned.
        > SQLAlchemy 2.0 made a much more comprehensive change to how this all works as well so
        > that all INSERT methods are essentially extremely fast now, relative to the 1.x series.
        >
        > -- https://github.com/sqlalchemy/sqlalchemy/discussions/6935#discussioncomment-4789701
        """
        chars = [
            self.character(name='Arthur', age=35),
            self.character(name='Banshee', age=26),
            self.character(name='Callisto', age=37),
        ]

        fake_cursor.description = ()
        fake_cursor.rowcount = len(chars)
        fake_cursor.executemany.return_value = [
            {'rowcount': 1},
            {'rowcount': 1},
            {'rowcount': 1},
        ]
        self.session.bulk_save_objects(chars)
        (stmt, bulk_args), _ = fake_cursor.executemany.call_args

        expected_stmt = "INSERT INTO characters (name, age) VALUES (?, ?)"
        self.assertEqual(expected_stmt, stmt)

        expected_bulk_args = (
            ('Arthur', 35),
            ('Banshee', 26),
            ('Callisto', 37)
        )
        self.assertSequenceEqual(expected_bulk_args, bulk_args)

    @skipIf(SA_VERSION < SA_2_0, "SQLAlchemy 1.x uses legacy bulk INSERT mode")
    @patch('crate.client.connection.Cursor', FakeCursor)
    def test_bulk_save_modern(self):
        """
        Verify modern SQLAlchemy bulk INSERT mode.

        > A list of parameter dictionaries sent to the `Session.execute.params` parameter,
        > separate from the Insert object itself, will invoke *bulk INSERT mode* for the
        > statement, which essentially means the operation will optimize as much as
        > possible for many rows.
        >
        > -- https://docs.sqlalchemy.org/orm/queryguide/dml.html#orm-queryguide-bulk-insert

        > We have been looking into getting performance optimizations
        > from `bulk_save()` to be inherently part of `add_all()`.
        >
        > -- https://github.com/sqlalchemy/sqlalchemy/discussions/6935#discussioncomment-1233465

        > The remaining performance limitation, that the `cursor.executemany()` DBAPI method
        > does not allow for rows to be fetched, is resolved for most backends by *foregoing*
        > the use of `executemany()` and instead restructuring individual INSERT statements
        > to each accommodate a large number of rows in a single statement that is invoked
        > using `cursor.execute()`. This approach originates from the `psycopg2` fast execution
        > helpers feature of the `psycopg2` DBAPI, which SQLAlchemy incrementally added more
        > and more support towards in recent release series.
        >
        > -- https://docs.sqlalchemy.org/core/connections.html#engine-insertmanyvalues
        """

        # Don't truncate unittest's diff output on `assertListEqual`.
        self.maxDiff = None

        chars = [
            self.character(name='Arthur', age=35),
            self.character(name='Banshee', age=26),
            self.character(name='Callisto', age=37),
        ]

        fake_cursor.description = ()
        fake_cursor.rowcount = len(chars)
        fake_cursor.execute.return_value = [
            {'rowcount': 1},
            {'rowcount': 1},
            {'rowcount': 1},
        ]
        self.session.add_all(chars)
        self.session.commit()
        (stmt, bulk_args), _ = fake_cursor.execute.call_args

        expected_stmt = "INSERT INTO characters (name, age) VALUES (?, ?), (?, ?), (?, ?)"
        self.assertEqual(expected_stmt, stmt)

        expected_bulk_args = (
            'Arthur', 35,
            'Banshee', 26,
            'Callisto', 37,
        )
        self.assertSequenceEqual(expected_bulk_args, bulk_args)

    @skipIf(sys.version_info < (3, 8), "SQLAlchemy/pandas is not supported on Python <3.8")
    @skipIf(SA_VERSION < SA_1_4, "SQLAlchemy 1.3 is not supported by pandas")
    @patch('crate.client.connection.Cursor', mock_cursor=FakeCursor)
    def test_bulk_save_pandas(self, mock_cursor):
        """
        Verify bulk INSERT with pandas.
        """
        from pandas._testing import makeTimeDataFrame
        from crate.client.sqlalchemy.support import insert_bulk

        # 42 records / 8 chunksize = 5.25, which means 6 batches will be emitted.
        INSERT_RECORDS = 42
        CHUNK_SIZE = 8
        OPCOUNT = math.ceil(INSERT_RECORDS / CHUNK_SIZE)

        # Create a DataFrame to feed into the database.
        df = makeTimeDataFrame(nper=INSERT_RECORDS, freq="S")

        dburi = "crate://localhost:4200"
        engine = sa.create_engine(dburi, echo=True)
        retval = df.to_sql(
            name="test-testdrive",
            con=engine,
            if_exists="replace",
            index=False,
            chunksize=CHUNK_SIZE,
            method=insert_bulk,
        )
        self.assertIsNone(retval)

        # Initializing the query has an overhead of two calls to the cursor object, probably one
        # initial connection from the DB-API driver, to inquire the database version, and another
        # one, for SQLAlchemy. SQLAlchemy will use it to inquire the table schema using `information_schema`,
        # and to eventually issue the `CREATE TABLE ...` statement.
        effective_op_count = mock_cursor.call_count - 2

        # Verify number of batches.
        self.assertEqual(effective_op_count, OPCOUNT)

    @skipIf(sys.version_info < (3, 8), "SQLAlchemy/Dask is not supported on Python <3.8")
    @skipIf(SA_VERSION < SA_1_4, "SQLAlchemy 1.3 is not supported by pandas")
    @patch('crate.client.connection.Cursor', mock_cursor=FakeCursor)
    def test_bulk_save_dask(self, mock_cursor):
        """
        Verify bulk INSERT with Dask.
        """
        import dask.dataframe as dd
        from pandas._testing import makeTimeDataFrame
        from crate.client.sqlalchemy.support import insert_bulk

        # 42 records / 4 partitions means each partition has a size of 10.5 elements.
        # Because the chunk size 8 is slightly smaller than 10, the partition will not
        # fit into it, so two batches will be emitted to the database for each data
        # partition. 4 partitions * 2 batches = 8 insert operations will be emitted.
        # Those settings are a perfect example of non-optimal settings, and have been
        # made so on purpose, in order to demonstrate that using optimal settings
        # is crucial.
        INSERT_RECORDS = 42
        NPARTITIONS = 4
        CHUNK_SIZE = 8
        OPCOUNT = math.ceil(INSERT_RECORDS / NPARTITIONS / CHUNK_SIZE) * NPARTITIONS

        # Create a DataFrame to feed into the database.
        df = makeTimeDataFrame(nper=INSERT_RECORDS, freq="S")
        ddf = dd.from_pandas(df, npartitions=NPARTITIONS)

        dburi = "crate://localhost:4200"
        retval = ddf.to_sql(
            name="test-testdrive",
            uri=dburi,
            if_exists="replace",
            index=False,
            chunksize=CHUNK_SIZE,
            method=insert_bulk,
            parallel=True,
        )
        self.assertIsNone(retval)

        # Each of the insert operation incurs another call to the cursor object. This is probably
        # the initial connection from the DB-API driver, to inquire the database version.
        # This compensation formula has been determined empirically / by educated guessing.
        effective_op_count = (mock_cursor.call_count - 2 * NPARTITIONS) - 2

        # Verify number of batches.
        self.assertEqual(effective_op_count, OPCOUNT)
