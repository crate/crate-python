.. _sqlalchemy-support:
.. _using-sqlalchemy:

==================
SQLAlchemy support
==================

.. rubric:: Table of contents

.. contents::
    :local:
    :depth: 2


Introduction
============

`SQLAlchemy`_ is the most popular `Object-Relational Mapping`_ (ORM) library
for Python.

The CrateDB Python client library provides support for SQLAlchemy. An
:ref:`SQLAlchemy dialect <sa:dialect_toplevel>` for CrateDB is registered at
installation time and can be used without further configuration.

The CrateDB SQLAlchemy dialect is validated to work with SQLAlchemy versions
``1.3``, ``1.4``, and ``2.0``.

.. SEEALSO::

    For general help using SQLAlchemy, consult the :ref:`SQLAlchemy tutorial
    <sa:unified_tutorial>` or the `SQLAlchemy library`_.

    Supplementary information about the CrateDB SQLAlchemy dialect can be found
    in the :ref:`data types appendix <data-types-sqlalchemy>`.

    Code examples for using the CrateDB SQLAlchemy dialect can be found at
    :ref:`sqlalchemy-by-example`.


.. _connecting:

Connecting
==========

.. _database-urls:

Database URLs
-------------

In an SQLAlchemy context, database addresses are represented by *Uniform Resource
Locators* (URL_) called :ref:`sa:database_urls`.

The simplest database URL for CrateDB looks like this::

    crate://<HOST>/[?option=value]

Here, ``<HOST>`` is the node *host string*. After the host, additional query
parameters can be specified to adjust some connection settings.

A host string looks like this::

    [<USERNAME>:<PASSWORD>@]<HOST_ADDR>:<PORT>

Here, ``<HOST_ADDR>`` is the hostname or IP address of the CrateDB node and
``<PORT>`` is a valid :ref:`crate-reference:psql.port` number.

When authentication is needed, the credentials can be optionally supplied using
``<USERNAME>:<PASSWORD>@``. For connecting to an SSL-secured HTTP endpoint, you
can add the query parameter ``?ssl=true`` to the database URI.

Example database URIs:

- ``crate://localhost:4200``
- ``crate://crate-1.vm.example.com:4200``
- ``crate://username:password@crate-2.vm.example.com:4200/?ssl=true``
- ``crate://198.51.100.1:4200``

.. TIP::

    If ``<HOST>`` is blank (i.e. the database URI is just ``crate://``), then
    ``localhost:4200`` will be assumed.

Getting a connection
--------------------

Create an engine
................

You can connect to CrateDB using the ``create_engine`` method. This method
takes a :ref:`database URL <sa:database_urls>`.

Import the ``sa`` module, like so:

    >>> import sqlalchemy as sa

To connect to ``localhost:4200``, you can do this:

    >>> engine = sa.create_engine('crate://')

To connect to ``crate-1.vm.example.com:4200``, you would do this:

    >>> engine = sa.create_engine('crate://crate-1.vm.example.com:4200')

If your CrateDB cluster has multiple nodes, however, we recommend that you
configure all of them. You can do that by specifying the ``crate://`` database
URL and passing in a list of :ref:`host strings <database-urls>` passed using
the ``connect_args`` argument, like so:

    >>> engine = sa.create_engine('crate://', connect_args={
    ...     'servers': ['198.51.100.1:4200', '198.51.100.2:4200']
    ... })

When you do this, the Database API layer will use its :ref:`round-robin
<multiple-nodes>` implementation.

The client validates :ref:`SSL server certificates <crate-reference:admin_ssl>`
by default. For further adjusting this behaviour, SSL verification options can
be passed in by using the ``connect_args`` dictionary.

For example, use ``ca_cert`` for providing a path to the CA certificate used
for signing the server certificate:

    >>> engine = sa.create_engine(
    ...     'crate://',
    ...     connect_args={
    ...         'servers': ['198.51.100.1:4200', '198.51.100.2:4200'],
    ...         'ca_cert': '<PATH_TO_CA_CERT>',
    ...     }
    ... )

In order to disable SSL verification, use ``verify_ssl_cert = False``, like:

    >>> engine = sa.create_engine(
    ...     'crate://',
    ...     connect_args={
    ...         'servers': ['198.51.100.1:4200', '198.51.100.2:4200'],
    ...         'verify_ssl_cert': False,
    ...     }
    ... )


Get a session
.............

Once you have an CrateDB ``engine`` set up, you can create and use an SQLAlchemy
``Session`` object to execute queries:

    >>> from sqlalchemy.orm import sessionmaker

    >>> Session = sessionmaker(bind=engine)
    >>> session = Session()

.. SEEALSO::

    SQLAlchemy has more documentation about this topic on :doc:`sa:orm/session_basics`.


.. _cloud-connect:

Connecting to CrateDB Cloud
...........................

Connecting to `CrateDB Cloud`_ works like this. Please note the ``?ssl=true``
query parameter at the end of the database URI.

    >>> import sqlalchemy as sa
    >>> dburi = "crate://admin:<PASSWORD>@example.aks1.westeurope.azure.cratedb.net:4200?ssl=true"
    >>> engine = sa.create_engine(dburi, echo=True)


.. _tables:

Tables
======

.. _table-definition:

Table definition
----------------

Here is an example SQLAlchemy table definition using the :ref:`declarative
system <sa:orm_declarative_mapping>`:

    >>> from sqlalchemy.ext import declarative
    >>> from crate.client.sqlalchemy import types
    >>> from uuid import uuid4

    >>> def gen_key():
    ...     return str(uuid4())

    >>> Base = declarative.declarative_base(bind=engine)

    >>> class Character(Base):
    ...
    ...     __tablename__ = 'characters'
    ...     __table_args__ = {
    ...         'crate_number_of_shards': 3
    ...     }
    ...
    ...     id = sa.Column(sa.String, primary_key=True, default=gen_key)
    ...     name = sa.Column(sa.String, crate_index=False)
    ...     name_normalized = sa.Column(sa.String, sa.Computed("lower(name)"))
    ...     quote = sa.Column(sa.String, nullable=False)
    ...     details = sa.Column(types.ObjectType)
    ...     more_details = sa.Column(types.ObjectArray)
    ...     name_ft = sa.Column(sa.String)
    ...     quote_ft = sa.Column(sa.String)
    ...     even_more_details = sa.Column(sa.String, crate_columnstore=False)
    ...     created_at = sa.Column(sa.DateTime, server_default=sa.func.now())
    ...     uuid = sa.Column(sa.String, crate_autogenerate_uuid=True)
    ...
    ...     __mapper_args__ = {
    ...         'exclude_properties': ['name_ft', 'quote_ft']
    ...     }

In this example, we:

- Define a ``gen_key`` function that produces :py:mod:`UUIDs <py:uuid>`
- Set up a ``Base`` class for the table
- Create the ``Characters`` class for the ``characters`` table
- Use the ``gen_key`` function to provide a default value for the ``id`` column
  (which is also the primary key)
- Use standard SQLAlchemy types for the ``id``, ``name``, and ``quote`` columns
- Use ``nullable=False`` to define a ``NOT NULL`` constraint
- Disable indexing of the ``name`` column using ``crate_index=False``
- Define a computed column ``name_normalized`` (based on ``name``) that
  translates into a generated column
- Use the `ObjectType`_ extension type for the ``details`` column
- Use the `ObjectArray`_ extension type for the ``more_details`` column
- Set up the ``name_ft`` and ``quote_ft`` fulltext indexes, but exclude them from
  the mapping (so SQLAlchemy doesn't try to update them as if they were columns)
- Disable the columnstore of the ``even_more_details`` column using ``crate_columnstore=False``
- Add a ``created_at`` column whose default value is set by CrateDB's ``now()`` function.
- Add a ``uuid`` column whose default value is generated by CrateDB's ``gen_random_text_uuid``
  can also be used with ``primary_key=True`` as an alternative of ``default=gen_key``

.. TIP::

    This example table is used throughout the rest of this document.

.. SEEALSO::

    The SQLAlchemy documentation has more information about
    :ref:`sa:metadata_describing`.


Additional ``__table_args__``
.............................


The example also shows the optional usage of ``__table_args__`` to configure
table-wide attributes. The following attributes can optionally be configured:

- ``crate_number_of_shards``: The number of primary shards the table will be
  split into
- ``crate_clustered_by``: The routing column to use for sharding
- ``crate_number_of_replicas``: The number of replicas to allocate for each
  primary shard
- ``crate_partitioned_by``: One or more columns to use as a partition key

.. SEEALSO::

    The :ref:`CREATE TABLE <crate-reference:sql-create-table>` documentation
    contains more information on each of the attributes.


``_id`` as primary key
......................

As with version 4.2 CrateDB supports the ``RETURNING`` clause, which makes it
possible to use the ``_id`` column as fetched value for the ``PRIMARY KEY``
constraint, since the SQLAlchemy ORM always **requires** a primary key.

A table schema like this

.. code-block:: sql

   CREATE TABLE "doc"."logs" (
     "ts" TIMESTAMP WITH TIME ZONE NOT NULL,
     "level" TEXT,
     "message" TEXT
   )

would translate into the following declarative model:

    >>> from sqlalchemy.schema import FetchedValue

    >>> class Log(Base):
    ...
    ...     __tablename__ = 'logs'
    ...     __mapper_args__ = {
    ...         'exclude_properties': ['id']
    ...     }
    ...
    ...     id = sa.Column("_id", sa.String, server_default=FetchedValue(), primary_key=True)
    ...     ts = sa.Column(sa.DateTime, server_default=sa.func.current_timestamp())
    ...     level = sa.Column(sa.String)
    ...     message = sa.Column(sa.String)

    >>> log = Log(level="info", message="Hello World")
    >>> session.add(log)
    >>> session.commit()
    >>> log.id
    ...

.. _using-extension-types:

Extension types
---------------

In the :ref:`example SQLAlchemy table definition <table-definition>` above, we
are making use of the two extension data types that the CrateDB SQLAlchemy
dialect provides.

.. SEEALSO::

    The appendix has a full :ref:`data types reference <data-types-sqlalchemy>`.

.. _object:
.. _objecttype:

``ObjectType``
..............

Objects are a common, and useful, data type when using CrateDB, so the CrateDB
SQLAlchemy dialect provides a custom ``Object`` type extension for working with
these values.

Here's how you use the :doc:`SQLAlchemy Session <sa:orm/session_basics>` to
insert two records:

    >>> # use the crate engine from earlier examples
    >>> Session = sessionmaker(bind=crate)
    >>> session = Session()

    >>> arthur = Character(name='Arthur Dent')
    >>> arthur.details = {}
    >>> arthur.details['gender'] = 'male'
    >>> arthur.details['species'] = 'human'
    >>> session.add(arthur)

    >>> trillian = Character(name='Tricia McMillan')
    >>> trillian.details = {}
    >>> trillian.quote = "We're on a space ship Arthur. In space."
    >>> trillian.details['gender'] = 'female'
    >>> trillian.details['species'] = 'human'
    >>> trillian.details['female_only_attribute'] = 1
    >>> session.add(trillian)
    >>> session.commit()

.. NOTE::

    The information we supply via the ``details`` column isn't defined in the
    :ref:`original SQLAlchemy table definition <table-definition>` schema.
    These details can be specified as *object column policy* when you create
    the column in CrateDB, you can either use the :ref:`STRICT column policy
    <crate-reference:type-object-columns-strict>`, or the :ref:`DYNAMIC column
    policy <crate-reference:type-object-columns-dynamic>`.

.. NOTE::

    Behind the scenes, if you update an ``ObjectType`` property, and ``commit`` that
    change, the :ref:`UPDATE <crate-reference:dml-updating-data>` statement sent
    to CrateDB will only include the data necessary to update the changed
    sub-columns.

.. _objectarray:

``ObjectArray``
...............

In addition to the `ObjectType`_ type, the CrateDB SQLAlchemy dialect also provides
an ``ObjectArray`` type, which is structured as a :class:`py:list` of
:class:`dictionaries <py:dict>`.

Here's how you might set the value of an ``ObjectArray`` column:

    >>> arthur.more_details = [{'foo': 1, 'bar': 10}, {'foo': 2}]
    >>> session.commit()

If you append an object, like this:

    >>> arthur.more_details.append({'foo': 3})
    >>> session.commit()

The resulting object will look like this:

    >>> arthur.more_details
    [{'foo': 1, 'bar': 10}, {'foo': 2}, {'foo': 3}]

.. CAUTION::

    Behind the scenes, if you update an ``ObjectArray``, and ``commit`` that
    change, the :ref:`UPDATE <crate-reference:dml-updating-data>` statement
    sent to CrateDB will include all of the ``ObjectArray`` data.

.. _geopoint:
.. _geoshape:

``Geopoint`` and ``Geoshape``
.............................

The CrateDB SQLAlchemy dialect provides two geospatial types:

- ``Geopoint``, which represents a longitude and latitude coordinate
- ``Geoshape``, which is used to store geometric `GeoJSON geometry objects`_

To use these types, you can create columns, like so:

    >>> class City(Base):
    ...
    ...    __tablename__ = 'cities'
    ...    name = sa.Column(sa.String, primary_key=True)
    ...    coordinate = sa.Column(types.Geopoint)
    ...    area = sa.Column(types.Geoshape)

A geopoint can be created in multiple ways. Firstly, you can define it as a
:py:class:`py:tuple` of ``(longitude, latitude)``:

    >>> point = (139.76, 35.68)

Secondly, you can define it as a geojson ``Point`` object:

    >>> from geojson import Point
    >>> point = Point(coordinates=(139.76, 35.68))

To create a geoshape, you can use a geojson shape object, such as a ``Polygon``:

    >>> from geojson import Point, Polygon
    >>> area = Polygon(
    ...     [
    ...         [
    ...             (139.806, 35.515),
    ...             (139.919, 35.703),
    ...             (139.768, 35.817),
    ...             (139.575, 35.760),
    ...             (139.584, 35.619),
    ...             (139.806, 35.515),
    ...         ]
    ...     ]
    ... )

You can then set the values of the ``Geopoint`` and ``Geoshape`` columns:

    >>> tokyo = City(name="Tokyo", coordinate=point, area=area)
    >>> session.add(tokyo)
    >>> session.commit()

Querying
========

When the ``commit`` method is called, two ``INSERT`` statements are sent to
CrateDB. However, the newly inserted rows aren't immediately available for
querying because the table index is only updated periodically (one second, by
default, which is a short time for me and you, but a long time for your code).

You can request a :ref:`table refresh <crate-reference:refresh_data>` to update
the index manually:

    >>> connection = engine.connect()
    >>> _ = connection.execute(text("REFRESH TABLE characters"))

.. NOTE::

    Newly inserted rows can still be queried immediately if a lookup by primary
    key is done.

Here's what a regular select might look like:

    >>> query = session.query(Character).order_by(Character.name)
    >>> [(c.name, c.details['gender']) for c in query]
    [('Arthur Dent', 'male'), ('Tricia McMillan', 'female')]

You can also select a portion of each record, and this even works inside
`ObjectType`_ columns:

    >>> sorted(session.query(Character.details['gender']).all())
    [('female',), ('male',)]

You can also filter on attributes inside the `ObjectType`_ column:

    >>> query = session.query(Character.name)
    >>> query.filter(Character.details['gender'] == 'male').all()
    [('Arthur Dent',)]

To filter on an `ObjectArray`_, you have to do something like this:

    >>> from sqlalchemy.sql import operators

    >>> query = session.query(Character.name)
    >>> query.filter(Character.more_details['foo'].any(1, operator=operators.eq)).all()
    [(u'Arthur Dent',)]

Here, we're using SQLAlchemy's :py:meth:`any <sa:sqlalchemy.types.ARRAY.Comparator.any>`
method along with Python's :py:func:`py:operator.eq` function, in order to
match the value ``1`` against the key ``foo`` of any dictionary in the
``more_details`` list.

Only one of the keys has to match for the row to be returned.

This works, because ``ObjectArray`` keys return a list of all values for that
key, like so:

    >>> arthur.more_details['foo']
    [1, 2, 3]

Querying a key of an ``ObjectArray`` column will return all values for that key
for all matching rows:

    >>> query = session.query(Character.more_details['foo']).order_by(Character.name)
    >>> query.all()
    [([1, 2, 3],), (None,)]

.. _aggregate-functions:

Aggregate functions
-------------------

SQLAlchemy supports different ways to `count result rows`_. However, because
CrateDB doesn't support subqueries, counts must be written in one of the
following two ways.

This counts the number of character records by counting the number of ``id``
values in the table:

    >>> session.query(sa.func.count(Character.id)).scalar()
    2

.. NOTE::

    If you're doing it like this, the column you select must be the primary
    key.

And this counts the number of character records by selecting all columns, and
then counting the number of rows:

    >>> session.query(sa.func.count('*')).select_from(Character).scalar()
    2

You can layer in calls to ``group_by`` and ``order_by`` when you use one of
these methods, like so:

    >>> session.query(sa.func.count(Character.id), Character.name) \
    ...     .group_by(Character.name) \
    ...     .order_by(sa.desc(sa.func.count(Character.id))) \
    ...     .order_by(Character.name).all()
    [(1, u'Arthur Dent'), (1, u'Tricia McMillan')]

Fulltext search
---------------

Matching
........

Fulltext Search in CrateDB is done with the :ref:`crate-reference:predicates_match`.

The CrateDB SQLAlchemy dialect provides a ``match`` function in the
``predicates`` module, which can be used to search one or multiple fields.

Here's an example use of the ``match`` function:

    >>> from crate.client.sqlalchemy.predicates import match

    >>> session.query(Character.name) \
    ...     .filter(match(Character.name_ft, 'Arthur')) \
    ...     .all()
    [('Arthur Dent',)]

In this example, we're selecting character ``name`` values, and returning all
rows where the ``name_ft`` index matches the string ``Arthur``.

.. NOTE::

    To use fulltext searches on a column, an explicit fulltext index with an
    analyzer must be created on the column. Consult the documentation about
    :ref:`crate-reference:fulltext-indices` for more information.

The ``match`` function takes the following options::

    match(column, term, match_type=None, options=None)

:``column``:

  A reference to a column or an index::

      match(Character.name_ft, 'Trillian')

  Or a subcolumn::

      match(Character.details['name']['first'], 'Trillian')

  Or a dictionary of the same, with `boost values`_::

      match({Character.name_ft: 0.5,
             Character.details['name']['first']: 0.8,
             Character.details['name']['last']: 0.2},
            'Trillian')

  .. SEEALSO::

      The `arguments reference`_ of the :ref:`crate-reference:predicates_match`
      has more in-depth information.

:``term``:

  The term to match against.

  This string is analyzed and the resulting tokens are compared to the index.

:``match_type``: *(optional)*

  The :ref:`crate-reference:predicates_match_types`.

  Determine how the ``term`` is applied and the :ref:`_score
  <crate-reference:sql_administration_system_column_score>` gets calculated.
  See also `score usage`_.

  Here's an example::

      match({Character.name_ft: 0.5,
             Character.details['name']['first']: 0.8,
             Character.details['name']['last']: 0.2},
            'Trillian',
            match_type='phrase')

:``options``: *(optional)*

  The `match options`_.

  Specify match type behaviour. (Not possible without a specified match type.)

  Match options must be supplied as a dictionary::

      match({Character.name_ft: 0.5,
             Character.details['name']['first']: 0.8,
             Character.details['name']['last']: 0.2},
            'Trillian',
            match_type='phrase'
            options={
                'fuzziness': 3,
                'analyzer': 'english'})

Relevance
.........

To get the relevance of a matching row, the row :ref:`_score
<crate-reference:sql_administration_system_column_score>` can be used.
See also `score usage`_.

The score is relative to other result rows produced by your query. The higher
the score, the more relevant the result row.

  .. COMMENT

     Keep this anonymous link in place so it doesn't get lost. We have to use
     this link format because of the leading underscore.

The score is made available via the ``_score`` column, which is a virtual
column, meaning that it doesn't exist on the source table, and in most cases,
should not be included in your :ref:`table definition <table-definition>`.

You can select ``_score`` as part of a query, like this:

    >>> session.query(Character.name, '_score') \
    ...     .filter(match(Character.quote_ft, 'space')) \
    ...     .all()
    [('Tricia McMillan', ...)]

Here, we're matching the term ``space`` against the ``quote_ft`` fulltext
index. And we're selecting the ``name`` column of the character by using the
table definition But notice that we select the associated score by passing in
the virtual column name as a string (``_score``) instead of using a defined
column on the ``Character`` class.


.. _arguments reference: https://crate.io/docs/crate/reference/en/latest/general/dql/fulltext.html#arguments
.. _boost values: https://crate.io/docs/crate/reference/en/latest/general/dql/fulltext.html#arguments
.. _count result rows: https://docs.sqlalchemy.org/en/14/orm/tutorial.html#counting
.. _CrateDB Cloud: https://console.cratedb.cloud/
.. _Database API: https://www.python.org/dev/peps/pep-0249/
.. _geojson geometry objects: https://www.rfc-editor.org/rfc/rfc7946#section-3.1
.. _match options: https://crate.io/docs/crate/reference/en/latest/general/dql/fulltext.html#options
.. _Object-Relational Mapping: https://en.wikipedia.org/wiki/Object-relational_mapping
.. _score usage: https://crate.io/docs/crate/reference/en/latest/general/dql/fulltext.html#usage
.. _SQLAlchemy: https://www.sqlalchemy.org/
.. _SQLAlchemy library: https://www.sqlalchemy.org/library.html
.. _URL: https://en.wikipedia.org/wiki/Uniform_Resource_Locator
