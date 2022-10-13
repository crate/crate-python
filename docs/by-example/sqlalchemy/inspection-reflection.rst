=====================================================
SQLAlchemy: Database schema inspection and reflection
=====================================================

This section of the documentation, related to CrateDB's SQLAlchemy integration,
focuses on database schema inspection and reflection features. That is, given
that you connect to an existing database, how to introspect its metadata
information to retrieve table- and view-names, and table column metadata.


Introduction
============

The `runtime inspection API`_ provides the ``inspect()`` function, which
delivers runtime information about a wide variety of SQLAlchemy objects, both
within SQLAlchemy Core and the SQLAlchemy ORM.

A low level interface which provides a backend-agnostic system of loading lists
of schema, table, column, and constraint descriptions from a given database is
available. This is known as the `SQLAlchemy inspector`_.

    >>> inspector = sa.inspect(engine)


Inspector usage
===============

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

A ``Table`` object can be instructed to load information about itself from the
corresponding database schema object already existing within the database. This
process is called *reflection*, see `reflecting database objects`_.

In the most simple case you need only specify the table name, a ``MetaData``
object, and the ``autoload_with`` argument.

Create a SQLAlchemy table object:

    >>> meta = sa.MetaData()
    >>> table = sa.Table(
    ...     "characters", meta,
    ...     autoload=True,
    ...     autoload_with=engine)

Reflect column data types from the table metadata:

    >>> table.columns.get('name')
    Column('name', String(), table=<characters>)

    >>> table.primary_key
    PrimaryKeyConstraint(Column('id', String(), table=<characters>, primary_key=True...


.. _reflecting database objects: https://docs.sqlalchemy.org/en/14/core/reflection.html#reflecting-database-objects
.. _runtime inspection API: https://docs.sqlalchemy.org/en/14/core/inspection.html
.. _SQLAlchemy inspector: https://docs.sqlalchemy.org/en/14/core/reflection.html#fine-grained-reflection-with-inspector
