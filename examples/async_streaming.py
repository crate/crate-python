"""
About
=====

Example program to demonstrate how to connect to CrateDB using its SQLAlchemy
dialect, and exercise a few basic examples using the low-level table API, this
time in asynchronous mode.

Specific to the asynchronous mode of SQLAlchemy is the streaming of results:

> The `AsyncConnection` also features a "streaming" API via the `AsyncConnection.stream()`
> method that returns an `AsyncResult` object. This result object uses a server-side cursor
> and provides an async/await API, such as an async iterator.
>
> -- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#synopsis-core

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
    python examples/async_streaming.py psycopg

    # Use PostgreSQL protocol, with `asyncpg`
    python examples/async_streaming.py asyncpg

    # Use with both variants
    python examples/async_streaming.py psycopg asyncpg

Bugs
====

When using the `psycopg` driver, the program currently croaks like::

    sqlalchemy.exc.InternalError: (psycopg.errors.InternalError_) Cannot find portal: c_10479c0a0_1

"""
import asyncio
import sys
import typing as t
from functools import lru_cache

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

metadata = sa.MetaData()
table = sa.Table(
    "t1",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
    sa.Column("name", sa.String),
)


class AsynchronousTableStreamingExample:
    """
    Demonstrate reading streamed results when using the CrateDB SQLAlchemy
    dialect in asynchronous mode with the `psycopg` and `asyncpg` drivers.

    - https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#synopsis-core
    - https://docs.sqlalchemy.org/en/20/_modules/examples/asyncio/basic.html
    """

    def __init__(self, dsn: str):
        self.dsn = dsn

    @property
    @lru_cache
    def engine(self):
        """
        Provide an SQLAlchemy engine object.
        """
        return create_async_engine(self.dsn, echo=True)

    async def run(self):
        """
        Run the whole recipe.
        """
        await self.create_and_insert()
        await self.read_buffered()
        await self.read_streaming()

    async def create_and_insert(self):
        """
        Create table schema, completely dropping it upfront, and insert a few records.
        """
        # conn is an instance of AsyncConnection
        async with self.engine.begin() as conn:
            # to support SQLAlchemy DDL methods as well as legacy functions, the
            # AsyncConnection.run_sync() awaitable method will pass a "sync"
            # version of the AsyncConnection object to any synchronous method,
            # where synchronous IO calls will be transparently translated for
            # await.
            await conn.run_sync(metadata.drop_all, checkfirst=True)
            await conn.run_sync(metadata.create_all)

            # for normal statement execution, a traditional "await execute()"
            # pattern is used.
            await conn.execute(
                table.insert(),
                [{"id": 1, "name": "some name 1"}, {"id": 2, "name": "some name 2"}],
            )

            # CrateDB specifics to flush/synchronize the write operation.
            await conn.execute(sa.text("REFRESH TABLE t1;"))

    async def read_buffered(self):
        """
        Read data from the database, in buffered mode.
        """
        async with self.engine.connect() as conn:
            # the default result object is the
            # sqlalchemy.engine.Result object
            result = await conn.execute(table.select())

            # the results are buffered so no await call is necessary
            # for this case.
            print(result.fetchall())

    async def read_streaming(self):
        """
        Read data from the database, in streaming mode.
        """
        async with self.engine.connect() as conn:

            # for a streaming result that buffers only segments of the
            # result at time, the AsyncConnection.stream() method is used.
            # this returns a sqlalchemy.ext.asyncio.AsyncResult object.
            async_result = await conn.stream(table.select())

            # this object supports async iteration and awaitable
            # versions of methods like .all(), fetchmany(), etc.
            async for row in async_result:
                print(row)


async def run_example(dsn: str):
    example = AsynchronousTableStreamingExample(dsn)

    # Run a basic conversation.
    # It also includes a catalog inquiry at `table.drop(checkfirst=True)`.
    await example.run()


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
