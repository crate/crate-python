"""
About
=====

Example program to demonstrate multi-row inserts and batched inserts
using SQLAlchemy's `insertmanyvalues_page_size` option.

- https://docs.sqlalchemy.org/core/connections.html#controlling-the-batch-size
- https://github.com/crate/crate-python/pull/539



Setup
=====
::

    pip install --upgrade 'crate[sqlalchemy]'


Synopsis
========
::

    # Run CrateDB
    docker run --rm -it --publish=4200:4200 crate

    # Run PostgreSQL
    docker run --rm -it --publish=5432:5432 --env "POSTGRES_HOST_AUTH_METHOD=trust" postgres:15 postgres -c log_statement=all

    # Use SQLite
    time python insert_efficient.py sqlite multirow
    time python insert_efficient.py sqlite batched

    # Use PostgreSQL
    time python insert_efficient.py postgresql multirow
    time python insert_efficient.py postgresql batched

    # Use CrateDB
    time python insert_efficient.py cratedb multirow
    time python insert_efficient.py cratedb batched


Bugs
====
- With `insert_batched`, the CrateDB dialect currently does not invoke SQLAlchemy's
  `Connection._exec_insertmany_context`, but the PostgreSQL dialect does.
  The CrateDB dialect currently only implements the legacy `bulk_save_objects` method.

[1] https://docs.sqlalchemy.org/orm/session_api.html#sqlalchemy.orm.Session.bulk_save_objects

"""
import sys

import sqlalchemy as sa

# INSERT_RECORDS = 1275
# INSERT_RECORDS = 50_000
INSERT_RECORDS = 2_750_000

BATCHED_PAGE_SIZE = 20_000


def insert_multirow(engine, table, records):
    """
    Demonstrate in-place multirow inserts.

    - Needs `dialect.supports_multivalues_insert = True`.
    - Will issue a single SQL statement.
    - SA can not control the batch-/chunksize, as there are no batches.
    - Will OOM CrateDB with large numbers of records, unless externally chunked, like pandas does.
    """
    insertable = table.insert().values(records)
    with engine.begin() as conn:
        conn.execute(insertable)


def insert_batched(engine, table, records):
    """
    Demonstrate batched inserts, with page-size.

    - Will issue multiple SQL statements.
    - SA controls batch-size per `insertmanyvalues_page_size` option.
    """
    insertable = table.insert()
    with engine.begin() as conn:
        # Optional: Adjust page size on a per-connection level.
        # conn.execution_options(insertmanyvalues_page_size=5)
        conn.execute(insertable, parameters=records)


def run_example(dburi: str, variant: str):
    metadata = sa.MetaData()
    table = sa.Table(
        "testdrive",
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("name", sa.String),
    )

    # Create 275 test records.
    records = [{"id": i, "name": f"foo_{i}"} for i in range(1, INSERT_RECORDS + 1)]

    # Run multi-row insert, with a specified batch-/page-size.
    engine = sa.create_engine(dburi, insertmanyvalues_page_size=BATCHED_PAGE_SIZE, echo=True)
    table.drop(bind=engine, checkfirst=True)
    table.create(bind=engine)

    if variant == "multirow":
        insert_multirow(engine, table, records)
    elif variant == "batched":
        insert_batched(engine, table, records)
    else:
        raise ValueError(f"Unknown variant: {variant}")

    with engine.begin() as conn:
        if dburi.startswith("crate://"):
            conn.execute(sa.text("REFRESH TABLE testdrive"))
        result = conn.execute(sa.text("SELECT COUNT(*) FROM testdrive"))
        print("Number of records:", result.scalar_one())


def run_database(database: str, variant: str):
    if database == "sqlite":
        dburi = "sqlite:///:memory:"
    elif database == "postgresql":
        dburi = "postgresql://postgres@localhost:5432"
    elif database == "cratedb":
        dburi = "crate://localhost:4200"
    else:
        raise ValueError(f"Unknown database: {database}")

    run_example(dburi, variant)


if __name__ == "__main__":
    database = sys.argv[1]
    variant = sys.argv[2]
    run_database(database, variant)
