"""
Introduction
============

CrateDB's `gen_random_text_uuid()` can be used like this to
auto-generate primary key values::

    crash <<EOL
        DROP TABLE IF EXISTS testdrive;
        CREATE TABLE IF NOT EXISTS "doc"."testdrive" (
          "x" TEXT DEFAULT gen_random_text_uuid() NOT NULL,
          "y" INT
        );
        INSERT INTO testdrive (y) VALUES (42);
        INSERT INTO testdrive (y) VALUES (42);
        REFRESH TABLE testdrive;
        SELECT * FROM testdrive;
    EOL

Setup
=====
::

    pip install 'crate[sqlalchemy]' 'psycopg[binary]' 'sqlalchemy>=2'

Usage
=====
::

    # Use PostgreSQL.
    docker run --rm -it --publish=5432:5432 --env "POSTGRES_HOST_AUTH_METHOD=trust" postgres:15
    python examples/column_autogenerate_uuid.py postgresql

    # Use CrateDB.
    docker run --rm -it --publish=4200:4200 --publish=6432:5432 crate
    python examples/column_autogenerate_uuid.py cratedb

Objective
=========

The second example currently croaks. Improve `CrateDDLCompiler` to make it work.

Proposal
========

Support SQLAlchemy column definitions like that::

    sa.Column("x", sa.String, primary_key=True, crate_autogenerate_uuid=True)

> Support custom column DDL within the generation of CREATE TABLE statements,
> by using the compiler extension documented in Custom SQL Constructs and
> Compilation Extension to extend CreateColumn.
>
> -- https://docs.sqlalchemy.org/en/20/core/ddl.html#sqlalchemy.schema.CreateColumn

"""
import re
import sys
from functools import lru_cache

import sqlalchemy as sa


class AutoIncrementExample:
    def __init__(self, dsn: str):
        self.dsn = dsn

    @property
    @lru_cache
    def engine(self):
        return sa.create_engine(self.dsn, echo=True)

    @property
    @lru_cache
    def table(self):
        metadata = sa.MetaData()
        if self.is_postgresql:
            # PostgreSQL can handle auto-incremented primary keys of type INTEGER or LONG.
            return sa.Table(
                "testdrive",
                metadata,
                sa.Column("x", sa.Integer, primary_key=True, autoincrement=True),
                sa.Column("y", sa.Integer),
            )
        elif self.is_cratedb:
            # CrateDB can automatically generate primary keys of type TEXT
            # using the `gen_random_text_uuid()` function.
            # Does _not_ work with PostgreSQL.
            return sa.Table(
                "testdrive",
                metadata,
                sa.Column("x", sa.String, primary_key=True, crate_autogenerate_uuid=True),
                sa.Column("y", sa.Integer),
            )
        else:
            raise ValueError("Unknown database type")

    @property
    def is_postgresql(self):
        return self.match_dsn("postgresql")

    @property
    def is_cratedb(self):
        return self.match_dsn("crate")

    def match_dsn(self, prefix: str):
        return re.match(rf"^{prefix}(?:\+\w+?)?://", self.dsn)

    def create(self):
        self.table.drop(bind=self.engine, checkfirst=True)
        self.table.create(bind=self.engine)

    def insert(self):
        stmt = self.table.insert().values(y=42)
        with self.engine.begin() as session:
            session.execute(stmt)
            session.execute(stmt)

    def read(self):
        with self.engine.begin() as session:
            if self.is_cratedb:
                session.execute(sa.text("REFRESH TABLE testdrive;"))
            result = session.execute(sa.text("SELECT * FROM testdrive;"))
            print("result:", result.fetchall())

    def reflect(self):
        meta = sa.MetaData()
        reflected_table = sa.Table("testdrive", meta, autoload_with=self.engine)
        print(reflected_table)
        print(reflected_table.columns)
        print(reflected_table.constraints)
        print(reflected_table.primary_key)


if __name__ == "__main__":

    kind = sys.argv[1]
    if kind == "cratedb":
        DSN = "crate://localhost:4200"
    elif kind == "postgresql":
        DSN = "postgresql+psycopg://postgres@localhost:5432"
    else:
        raise ValueError("Unknown kind")

    ex = AutoIncrementExample(DSN)
    ex.create()
    ex.insert()
    ex.read()
    # ex.reflect()
