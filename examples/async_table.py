"""
About
=====

Example program to demonstrate how to connect to CrateDB using its SQLAlchemy
dialect, and exercise a few basic examples using the low-level table API, this
time in asynchronous mode.

Both the PostgreSQL drivers based on `psycopg` and `asyncpg` are exercised.
The corresponding SQLAlchemy dialect identifiers are::

    # PostgreSQL protocol on port 5432, using `psycopg`
    crate+psycopg://crate@localhost:5432/doc

    # PostgreSQL protocol on port 5432, using `asyncpg`
    crate+asyncpg://crate@localhost:5432/doc

Synopsis
========
::

    # Run CrateDB
    docker run --rm -it --publish=4200:4200 --publish=5432:5432 crate

    # Use PostgreSQL protocol, with asynchronous support of `psycopg`
    python examples/async_table.py psycopg

    # Use PostgreSQL protocol, with `asyncpg`
    python examples/async_table.py asyncpg

    # Use with both variants
    python examples/async_table.py psycopg asyncpg

"""
import asyncio
import sys
import typing as t
from functools import lru_cache

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine


class AsynchronousTableExample:
    """
    Demonstrate the CrateDB SQLAlchemy dialect in asynchronous mode with the `psycopg` and `asyncpg` drivers.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn

    @property
    @lru_cache
    def engine(self):
        """
        Provide an SQLAlchemy engine object.
        """
        return create_async_engine(self.dsn, isolation_level="AUTOCOMMIT", echo=True)

    @property
    @lru_cache
    def table(self):
        """
        Provide an SQLAlchemy table object.
        """
        metadata = sa.MetaData()
        return sa.Table(
            "testdrive",
            metadata,
            sa.Column("x", sa.Integer, primary_key=True, autoincrement=False),
            sa.Column("y", sa.Integer),
        )

    async def conn_run_sync(self, func: t.Callable, *args, **kwargs):
        """
        To support SQLAlchemy DDL methods as well as legacy functions, the
        AsyncConnection.run_sync() awaitable method will pass a "sync"
        version of the AsyncConnection object to any synchronous method,
        where synchronous IO calls will be transparently translated for
        await.

        https://docs.sqlalchemy.org/en/20/_modules/examples/asyncio/basic.html
        """
        # `conn` is an instance of `AsyncConnection`
        async with self.engine.begin() as conn:
            return await conn.run_sync(func, *args, **kwargs)

    async def run(self):
        """
        Run the whole recipe, returning the result from the "read" step.
        """
        await self.create()
        await self.insert(sync=True)
        return await self.read()

    async def create(self):
        """
        Create table schema, completely dropping it upfront.
        """
        await self.conn_run_sync(self.table.drop, checkfirst=True)
        await self.conn_run_sync(self.table.create)

    async def insert(self, sync: bool = False):
        """
        Write data from the database, taking CrateDB-specific `REFRESH TABLE` into account.
        """
        async with self.engine.begin() as conn:
            stmt = self.table.insert().values(x=1, y=42)
            await conn.execute(stmt)
            stmt = self.table.insert().values(x=2, y=42)
            await conn.execute(stmt)
            if sync and self.dsn.startswith("crate"):
                await conn.execute(sa.text("REFRESH TABLE testdrive;"))

    async def read(self):
        """
        Read data from the database.
        """
        async with self.engine.begin() as conn:
            cursor = await conn.execute(sa.text("SELECT * FROM testdrive;"))
            return cursor.fetchall()

    async def reflect(self):
        """
        Reflect the table schema from the database.
        """

        # Debugging.
        # self.trace()

        def reflect(session):
            """
            A function written in "synchronous" style that will be invoked
            within the asyncio event loop.

            The session object passed is a traditional orm.Session object with
            synchronous interface.

            https://docs.sqlalchemy.org/en/20/_modules/examples/asyncio/greenlet_orm.html
            """
            meta = sa.MetaData()
            reflected_table = sa.Table("testdrive", meta, autoload_with=session)
            print("Table information:")
            print(f"Table:       {reflected_table}")
            print(f"Columns:     {reflected_table.columns}")
            print(f"Constraints: {reflected_table.constraints}")
            print(f"Primary key: {reflected_table.primary_key}")

        return await self.conn_run_sync(reflect)

    @staticmethod
    def trace():
        """
        Trace execution flow through SQLAlchemy.

        pip install hunter
        """
        from hunter import Q, trace

        constraint = Q(module_startswith="sqlalchemy")
        trace(constraint)


async def run_example(dsn: str):
    example = AsynchronousTableExample(dsn)

    # Run a basic conversation.
    # It also includes a catalog inquiry at `table.drop(checkfirst=True)`.
    result = await example.run()
    print(result)

    # Reflect the table schema.
    await example.reflect()


def run_drivers(drivers: t.List[str]):
    for driver in drivers:
        if driver == "psycopg":
            dsn = "crate+psycopg://crate@localhost:5432/doc"
        elif driver == "asyncpg":
            dsn = "crate+asyncpg://crate@localhost:5432/doc"
        else:
            raise ValueError(f"Unknown driver: {driver}")

        asyncio.run(run_example(dsn))


if __name__ == "__main__":

    drivers = sys.argv[1:]
    run_drivers(drivers)
