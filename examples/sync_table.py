"""
About
=====

Example program to demonstrate how to connect to CrateDB using its SQLAlchemy
dialect, and exercise a few basic examples using the low-level table API.

Both the HTTP driver based on `urllib3`, and the PostgreSQL driver based on
`psycopg` are exercised. The corresponding SQLAlchemy dialect identifiers are::

    # CrateDB HTTP API on port 4200
    crate+urllib3://localhost:4200/doc

    # PostgreSQL protocol on port 5432
    crate+psycopg://crate@localhost:5432/doc

Synopsis
========
::

    # Run CrateDB
    docker run --rm -it --publish=4200:4200 --publish=5432:5432 crate

    # Use HTTP API
    python examples/sync_table.py urllib3

    # Use PostgreSQL protocol
    python examples/sync_table.py psycopg

    # Use with both variants
    python examples/sync_table.py urllib3 psycopg

"""
import sys
import typing as t
from functools import lru_cache

import sqlalchemy as sa


class SynchronousTableExample:
    """
    Demonstrate the CrateDB SQLAlchemy dialect with the `urllib3` and `psycopg` drivers.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn

    @property
    @lru_cache
    def engine(self):
        """
        Provide an SQLAlchemy engine object.
        """
        return sa.create_engine(self.dsn, isolation_level="AUTOCOMMIT", echo=True)

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
            # TODO: When omitting `autoincrement`, SA's DDL generator will use `SERIAL`.
            #       (psycopg.errors.InternalError_) Cannot find data type: serial
            #       This is probably one more thing to redirect to the CrateDialect.
            sa.Column("x", sa.Integer, primary_key=True, autoincrement=False),
            sa.Column("y", sa.Integer),
        )

    def run(self):
        """
        Run the whole recipe, returning the result from the "read" step.
        """
        self.create()
        self.insert(sync=True)
        return self.read()

    def create(self):
        """
        Create table schema, completely dropping it upfront.
        """
        self.table.drop(bind=self.engine, checkfirst=True)
        self.table.create(bind=self.engine)

    def insert(self, sync: bool = False):
        """
        Write data from the database, taking CrateDB-specific `REFRESH TABLE` into account.
        """
        with self.engine.begin() as session:
            stmt = self.table.insert().values(x=1, y=42)
            session.execute(stmt)
            stmt = self.table.insert().values(x=2, y=42)
            session.execute(stmt)
            if sync and self.dsn.startswith("crate"):
                session.execute(sa.text("REFRESH TABLE testdrive;"))

    def read(self):
        """
        Read data from the database.
        """
        with self.engine.begin() as session:
            cursor = session.execute(sa.text("SELECT * FROM testdrive;"))
            return cursor.fetchall()

    def reflect(self):
        """
        Reflect the table schema from the database.
        """
        meta = sa.MetaData()
        # Debugging.
        # self.trace()
        reflected_table = sa.Table("testdrive", meta, autoload_with=self.engine)
        print("Table information:")
        print(f"Table:       {reflected_table}")
        print(f"Columns:     {reflected_table.columns}")
        print(f"Constraints: {reflected_table.constraints}")
        print(f"Primary key: {reflected_table.primary_key}")

    @staticmethod
    def trace():
        """
        Trace execution flow through SQLAlchemy.

        pip install hunter
        """
        from hunter import Q, trace

        constraint = Q(module_startswith="sqlalchemy")
        trace(constraint)


def run_example(dsn: str):
    example = SynchronousTableExample(dsn)

    # Run a basic conversation.
    # It also includes a catalog inquiry at `table.drop(checkfirst=True)`.
    result = example.run()
    print(result)

    # Reflect the table schema.
    # example.reflect()


def run_drivers(drivers: t.List[str]):
    for driver in drivers:
        if driver == "urllib3":
            dsn = "crate+urllib3://localhost:4200/doc"
        elif driver == "psycopg":
            dsn = "crate+psycopg://crate@localhost:5432/doc"
        else:
            raise ValueError(f"Unknown driver: {driver}")

        run_example(dsn)


if __name__ == "__main__":

    drivers = sys.argv[1:]
    run_drivers(drivers)
