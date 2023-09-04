.. _sqlalchemy-getting-started:

===========================
SQLAlchemy: Getting started
===========================

This section of the documentation shows how to connect to CrateDB using its
SQLAlchemy dialect, and how to run basic DDL statements based on an SQLAlchemy
ORM schema definition.

Subsequent sections of the documentation will cover:

- :ref:`sqlalchemy-crud`
- :ref:`sqlalchemy-working-with-types`
- :ref:`sqlalchemy-advanced-querying`
- :ref:`sqlalchemy-inspection-reflection`


.. rubric:: Table of Contents

.. contents::
   :local:


Introduction
============

Import the relevant symbols:

    >>> import sqlalchemy as sa
    >>> from sqlalchemy.orm import sessionmaker
    >>> try:
    ...     from sqlalchemy.orm import declarative_base
    ... except ImportError:
    ...     from sqlalchemy.ext.declarative import declarative_base

Establish a connection to the database, see also :ref:`sa:engines_toplevel`
and :ref:`connect`:

    >>> engine = sa.create_engine(f"crate://{crate_host}")
    >>> connection = engine.connect()

Create an SQLAlchemy :doc:`Session <sa:orm/session_basics>`:

    >>> session = sessionmaker(bind=engine)()
    >>> Base = declarative_base()


Connect
=======

In SQLAlchemy, a connection is established using the ``create_engine`` function.
This function takes a connection string, actually an `URL`_, that varies from
database to database.

In order to connect to a CrateDB cluster, the following connection strings are
valid:

    >>> sa.create_engine('crate://')
    Engine(crate://)

This will connect to the default server ('127.0.0.1:4200'). In order to connect
to a different server the following syntax can be used:

    >>> sa.create_engine('crate://otherserver:4200')
    Engine(crate://otherserver:4200)

Multiple Hosts
--------------
Because CrateDB is a clustered database running on multiple servers, it is
recommended to connect to all of them. This enables the DB-API layer to
use round-robin to distribute the load and skip a server if it becomes
unavailable. In order to make the driver aware of multiple servers, use
the ``connect_args`` parameter like so:

    >>> sa.create_engine('crate://', connect_args={
    ...     'servers': ['host1:4200', 'host2:4200']
    ... })
    Engine(crate://)

TLS Options
-----------
As defined in :ref:`https_connection`, the client validates SSL server
certificates by default. To configure this further, use e.g. the ``ca_cert``
attribute within the ``connect_args``, like:

    >>> ssl_engine = sa.create_engine(
    ...     'crate://',
    ...     connect_args={
    ...         'servers': ['https://host1:4200'],
    ...         'ca_cert': '/path/to/cacert.pem',
    ...     })

In order to disable SSL verification, use ``verify_ssl_cert = False``, like:

    >>> ssl_engine = sa.create_engine(
    ...     'crate://',
    ...     connect_args={
    ...         'servers': ['https://host1:4200'],
    ...         'verify_ssl_cert': False,
    ...     })

Timeout Options
---------------
In order to configure TCP timeout options, use the ``timeout`` parameter within
``connect_args``,

    >>> timeout_engine = sa.create_engine('crate://localhost/', connect_args={'timeout': 42.42})
    >>> timeout_engine.raw_connection().driver_connection.client._pool_kw["timeout"]
    42.42

or use the ``timeout`` URL parameter within the database connection URL.

    >>> timeout_engine = sa.create_engine('crate://localhost/?timeout=42.42')
    >>> timeout_engine.raw_connection().driver_connection.client._pool_kw["timeout"]
    42.42

Pool Size
---------

In order to configure the database connection pool size, use the ``pool_size``
parameter within ``connect_args``,

    >>> timeout_engine = sa.create_engine('crate://localhost/', connect_args={'pool_size': 20})
    >>> timeout_engine.raw_connection().driver_connection.client._pool_kw["maxsize"]
    20

or use the ``pool_size`` URL parameter within the database connection URL.

    >>> timeout_engine = sa.create_engine('crate://localhost/?pool_size=20')
    >>> timeout_engine.raw_connection().driver_connection.client._pool_kw["maxsize"]
    20


Basic DDL operations
====================

.. note::

    CrateDB currently does not know about different "databases". Instead,
    tables can be created in different *schemas*. Schemas are created
    implicitly on table creation and cannot be created explicitly. If a schema
    does not exist yet, it will be created.

    The default CrateDB schema is ``doc``, and if you do not specify a schema,
    this is what will be used.

    See also :ref:`schema-selection` and :ref:`crate-reference:ddl-create-table-schemas`.


Create tables
-------------

First the table definition as class, using SQLAlchemy's :ref:`sa:orm_declarative_mapping`:

    >>> class Department(Base):
    ...     __tablename__ = 'departments'
    ...     __table_args__ = {
    ...         'crate_number_of_replicas': '0'
    ...     }
    ...     id = sa.Column(sa.String, primary_key=True)
    ...     name = sa.Column(sa.String)
    ...     code = sa.Column(sa.Integer)

As seen below, the table doesn't exist yet:

    >>> engine.dialect.has_table(connection, table_name='departments')
    False

In order to create all missing tables, the ``create_all`` method can be used:

    >>> Base.metadata.create_all(bind=engine)

With that, the table has been created:

    >>> engine.dialect.has_table(connection, table_name='departments')
    True

Let's also verify that by inquiring the ``information_schema.columns`` table:

    >>> stmt = ("select table_name, column_name, ordinal_position, data_type "
    ...         "from information_schema.columns "
    ...         "where table_name = 'departments' "
    ...         "order by column_name")
    >>> pprint([str(r) for r in connection.execute(sa.text(stmt))])
    ["('departments', 'code', 3, 'integer')",
     "('departments', 'id', 1, 'text')",
     "('departments', 'name', 2, 'text')"]


Drop tables
-----------

In order to delete all tables reference within the ORM schema, invoke
``Base.metadata.drop_all()``. To delete a single table, use
``drop(...)``, as shown below:

    >>> Base.metadata.tables['departments'].drop(engine)

    >>> engine.dialect.has_table(connection, table_name='departments')
    False


.. hidden: Disconnect from database

    >>> session.close()
    >>> connection.close()
    >>> engine.dispose()


.. _URL: https://en.wikipedia.org/wiki/Uniform_Resource_Locator
