=====================
SQLAlchemy: Internals
=====================

This section of the documentation, related to CrateDB's SQLAlchemy integration,
focuses on showing specific internals.


CrateDialect
============

The initialize method sets the default schema name and version info:

    >>> connection = engine.connect()
    >>> dialect = CrateDialect()
    >>> dialect.initialize(connection)


    >>> dialect.server_version_info >= (1, 0, 0)
    True

Check if table exists:

    >>> dialect.has_table(connection, 'locations')
    True

Check if schema exists:

    >>> dialect.has_schema(connection, 'doc')
    True

.. Hidden: close connection

    >>> connection.close()
