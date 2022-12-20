.. _sqlalchemy-inspection-reflection:

=====================================================
SQLAlchemy: Database schema inspection and reflection
=====================================================

This section shows you how to inspect the schema of a database using CrateDB's
SQLAlchemy integration.


Introduction
============

The CrateDB SQLAlchemy integration provides different ways to inspect the
database.

1) The :ref:`runtime inspection API <sa:inspection_toplevel>` allows you to get
   an ``Inspector`` instance that can be used to fetch schema names, table names
   and other information.

2) Reflection capabilities allow you to create ``Table`` instances from
   existing tables to inspect their columns and constraints.

3) A ``CrateDialect`` allows you to get connection information and it contains
   low level function to check the existence of schemas and tables.

All approaches require an ``Engine`` instance, which you can create like this:

    >>> import sqlalchemy as sa
    >>> engine = sa.create_engine(f"crate://{crate_host}")

This effectively establishes a connection to the database, see also
:ref:`sa:engines_toplevel` and :ref:`connect`.


Inspector
=========

The :ref:`SQLAlchemy inspector <sa:metadata_reflection_inspector>` is a low
level interface which provides a backend-agnostic system of loading lists of
schema, table, column, and constraint descriptions from a given database.
You can create an inspector like this:

    >>> inspector = sa.inspect(engine)

List all schemas:

    >>> inspector.get_schema_names()
    ['blob', 'doc', 'information_schema', 'pg_catalog', 'sys']

List all tables:

    >>> set(['characters', 'cities', 'locations']).issubset(inspector.get_table_names())
    True

    >>> set(['checks', 'cluster', 'jobs', 'jobs_log']).issubset(inspector.get_table_names(schema='sys'))
    True

List all views:

    >>> inspector.get_view_names()
    ['characters_view']

Get default schema name:

    >>> inspector.default_schema_name
    'doc'


Schema-supported reflection
===========================

A ``Table`` object can load its own schema information from the corresponding
table in the database. This process is called *reflection*, see
:ref:`sa:metadata_reflection`.

In the most simple case you need only specify the table name, a ``MetaData``
object, and the ``autoload_with`` argument.

Create a SQLAlchemy table object:

    >>> meta = sa.MetaData()
    >>> table = sa.Table(
    ...     "characters", meta,
    ...     autoload_with=engine)

Reflect column data types from the table metadata:

    >>> table.columns.get('name')
    Column('name', String(), table=<characters>)

    >>> table.primary_key
    PrimaryKeyConstraint(Column('id', String(), table=<characters>, primary_key=True...


CrateDialect
============

After initializing the dialect instance with a connection instance,

    >>> from crate.client.sqlalchemy.dialect import CrateDialect
    >>> dialect = CrateDialect()

    >>> connection = engine.connect()
    >>> dialect.initialize(connection)

the database server version and default schema name can be inquired.

    >>> dialect.server_version_info >= (1, 0, 0)
    True

Check if a schema exists:

    >>> dialect.has_schema(connection, 'doc')
    True

Check if a table exists:

    >>> dialect.has_table(connection, 'locations')
    True


.. hidden: Disconnect from database

    >>> connection.close()
    >>> engine.dispose()
