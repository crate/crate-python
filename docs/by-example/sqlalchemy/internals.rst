=====================
SQLAlchemy: Internals
=====================

This section of the documentation, related to CrateDB's SQLAlchemy integration,
focuses on showing specific internals.


CrateDialect
============

Import the relevant symbols:

    >>> import sqlalchemy as sa
    >>> from crate.client.sqlalchemy.dialect import CrateDialect

Establish a connection to the database:

    >>> engine = sa.create_engine(f"crate://{crate_host}")
    >>> connection = engine.connect()

After initializing the dialect instance with a connection instance,

    >>> dialect = CrateDialect()
    >>> dialect.initialize(connection)

the database server version and default schema name can be inquired.

    >>> dialect.server_version_info >= (1, 0, 0)
    True

Check if schema exists:

    >>> dialect.has_schema(connection, 'doc')
    True

Check if table exists:

    >>> dialect.has_table(connection, 'locations')
    True

.. Hidden: close connection

    >>> connection.close()
