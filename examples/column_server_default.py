"""
Introduction
============

CrateDB's `NOW()` can be used like this to auto-generate timestamp values::

    crash <<EOL
        DROP TABLE IF EXISTS testdrive;
        CREATE TABLE IF NOT EXISTS "doc"."testdrive" (
          "timestamp" TIMESTAMP DEFAULT NOW() NOT NULL,
          "value" FLOAT
        );
        INSERT INTO testdrive (value) VALUES (42.42);
        INSERT INTO testdrive (value) VALUES (42.42);
        REFRESH TABLE testdrive;
        SELECT * FROM testdrive;
    EOL

Setup
=====
::

    pip install 'crate[sqlalchemy]'

Usage
=====
::

    # Use CrateDB.
    docker run --rm -it --publish=4200:4200 --publish=6432:5432 crate
    python examples/column_server_default.py cratedb

Objective
=========

Make the `CrateDDLCompiler` honor the `server_default` option, like::

    >>> import sqlalchemy as sa
    >>> sa.Column("timestamp", sa.DateTime, server_default=sa.text("NOW()"))

-- https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.Column.params.server_default

"""
import re
import sys
from functools import lru_cache

import sqlalchemy as sa


class ColumnServerDefaultExample:
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
        if self.is_cratedb:
            return sa.Table(
                "testdrive",
                metadata,
                sa.Column("timestamp", sa.DateTime, server_default=sa.text("NOW()")),
                sa.Column("value", sa.Float),
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
        stmt = self.table.insert().values(value=42.42)
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
    else:
        raise ValueError("Unknown kind")

    ex = ColumnServerDefaultExample(DSN)
    ex.create()
    ex.insert()
    ex.read()
    # ex.reflect()
