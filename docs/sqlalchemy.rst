.. _using-sqlalchemy:

============================
Using the SQLAlchemy dialect
============================

`SQLAlchemy`_ is a popular `Object-Relational Mapping`_ (ORM) tool for Python.

The CrateDB Python client library provides support for SQLAlchemy. A CrateDB
`dialect`_ is registered at installation time and can be used without further
configuration.

The CrateDB Python client library works with SQLAlchemy versions ``1.0``,
``1.1`` and ``1.2``.

.. NOTE::

   This page documents the CrateDB SQLAlchemy dialect.

   For help using the CrateDB `Database API`_ client, consult :ref:`the client
   documentation <connect>`.

.. SEEALSO::

   Supplementary information about the CrateDB SQLAlchemy dialect can be found
   in the :ref:`data types appendix <data-types-sqlalchemy>` and the
   :ref:`compatibility notes <compatibility>`.

   For general help using SQLAlchemy, consult the `SQLAlchemy tutorial`_ or the
   `SQLAlchemy library`_ .

.. rubric:: Table of contents

.. contents::
   :local:

.. _connecting:

Connecting
==========

.. _database-urls:

Database URLs
-------------

An SQLAlchemy database is represented by special type of *Uniform Resource
Locator* (URL) called a `database URL`_.

The simplest database URL for CrateDB looks like this::

    crate://<HOST>

Here, ``<HOST>`` is the node *host string*.

A host string looks like this::

    <HOST_ADDR>:<PORT>

Here, ``<HOST_ADDR>`` is the hostname or IP address of the CrateDB node and
``<PORT>`` is a valid `psql.port`_ number.

Example host strings:

- ``localhost:4200``
- ``crate-1.vm.example.com:4200``
- ``198.51.100.1:4200``

.. TIP::

    If ``<HOST>`` is blank (i.e. just ``crate://``) then ``localhost:4200`` will
    be assumed.

Getting a connection
--------------------

Create an engine
................


You can connect to CrateDB using the ``create_engine`` method. This method
takes a `database URL`_.

Import the ``sa`` module, like so:

    >>> import sqlalchemy as sa

To connect to ``localhost:4200``, you can do this::

    >>> engine = sa.create_engine('crate://')

To connect to ``crate-1.vm.example.com:4200``, you would do this:

    >>> engine = sa.create_engine('crate://crate-1.vm.example.com:4200')

If your CrateDB cluster has multiple nodes, however, we recommend that you
configure all of them. You can do that by specifying the ``crate://`` database
URL and passing in a list of :ref:`host strings <database-urls>` passed using
the ``connect_args`` argument, like so::

    >>> engine = sa.create_engine('crate://', connect_args={
    ...     'servers': ['198.51.100.1:4200', '198.51.100.2:4200']
    ... })

When you do this, the Database API layer will use its :ref:`round-robin
<multiple-nodes>` implementation.

The client validates `SSL server certificates`_ by default. To configure
this behaviour, SSL verification options can be passed in via ``connect_args``
too::

    >>> engine = sa.create_engine(
    ...     'crate://',
    ...     connect_args={
    ...         'servers': ['198.51.100.1:4200', '198.51.100.2:4200'],
    ...         'verify_ssl_cert': True,
    ...         'ca_cert': '<PATH_TO_CA_CERT>',
    ...     }
    ... )

Here, ``<PATH_TO_CA_CERT>`` should be replaced with the path to the correct CA
certificate.

Get a session
.............

Once you have an CrateDB ``engine`` set up, you can create and use an SQLAlchemy
``Session`` object to execute queries::

    >>> from sqlalchemy.orm import sessionmaker

    >>> Session = sessionmaker(bind=engine)
    >>> session = Session()

.. SEEALSO::

    The SQLAlchemy has more documentation on `sessions`_.

.. _sessions: http://docs.sqlalchemy.org/en/latest/orm/session_basics.html

.. _tables:

Tables
======

.. _table-definition:

Table definition
----------------

Here is an example SQLAlchemy table definition using the `declarative
system`_::

    >>> from sqlalchemy.ext import declarative
    >>> from crate.client.sqlalchemy import types
    >>> from uuid import uuid4

    >>> def gen_key():
    ...     return str(uuid4())

    >>> Base = declarative.declarative_base(bind=engine)

    >>> class Character(Base):
    ...
    ...     __tablename__ = 'characters'
    ...
    ...     id = sa.Column(sa.String, primary_key=True, default=gen_key)
    ...     name = sa.Column(sa.String)
    ...     quote = sa.Column(sa.String)
    ...     details = sa.Column(types.Object)
    ...     more_details = sa.Column(ObjectArray)
    ...     name_ft = sa.Column(sa.String)
    ...     quote_ft = sa.Column(sa.String)
    ...
    ...     __mapper_args__ = {
    ...         'exclude_properties': ['name_ft', 'quote_ft']
    ...     }

In this example, we:

- Define a ``gen_key`` function that produces `UUIDs`_
- Set up a ``Base`` class for the table
- Create the ``Characters`` class for the ``characters`` table
- Use the ``gen_key`` function to provide a default value for the ``id`` column
  (which is also the primary key)
- Use standard SQLAlchemy types for the ``id``, ``name``, and ``quote`` columns
- Use the `Object`_ extension type for the ``details`` column
- Use the `ObjectArray`_ extension type for the ``more_details`` column
- Set up the ``name_ft`` and ``quote_ft`` fulltext indexes, but exclude them from
  the mapping (so SQLAlchemy doesn't try to update them as if they were columns)

.. TIP::

    This example table is used throughout the rest of this document.

.. SEEALSO::

    The SQLAlchemy documentation has more information about `working with
    tables`_.

``_id`` as primary key
......................

As with version 4.2 CrateDB supports the ``RETURNING`` clause, which makes it
possible to use the ``_id`` column as fetched value for the ``PRIMARY KEY``
constraint, since the SQLAlchemy ORM always **requires** a primary key.

A table schema like this

.. code-block:: sql

   CREATE TABLE "doc"."logs" (
     "ts" TIMESTAMP WITH TIME ZONE,
     "level" TEXT,
     "message" TEXT
   )

would translate into the following declarative model::

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

``Object``
..........

Objects are a common, and useful, data type when using CrateDB, so the CrateDB
SQLAlchemy dialect provides a custom ``Object`` type extension for working with
these values.

Here's how you might use the SQLAlchemy `Session`_ object to insert two
characters::

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
    :ref:`original SQLAlchemy table definition <table-definition>`. These
    details can be `specified`_ when you create the column in CrateDB, or you
    can configure the column to support `dynamic values`_.

.. NOTE::

    Behind the scenes, if you update an ``Object`` property and ``commit`` that
    change, the `UPDATE`_ statement sent to CrateDB will only include the data
    necessary to update the changed subcolumns.

.. _objectarray:

``ObjectArray``
...............

In addition to the `Object`_ type, the CrateDB SQLAlchemy dialect also provides
a ``ObjectArray`` type, which is structured as a `list`_ of `dictionaries`_.

Here's how you might set the value of an ``ObjectArray`` column::

    >>> arthur.more_details = [{'foo': 1, 'bar': 10}, {'foo': 2}]
    >>> session.commit()

If you append an object, like this::

    >>> arthur.more_details.append({'foo': 3})
    >>> session.commit()

The resulting object will look like this::

    >>> arthur.more_details
    [{'foo': 1, 'bar': 10}, {'foo': 2}, {'foo': 3}]

.. CAUTION::

    Behind the scenes, if you update an ``ObjectArray`` and ``commit`` that
    change, the `UPDATE`_ statement sent to CrateDB will include all of the
    ``ObjectArray`` data.

.. _geopoint:
.. _geoshape:

``Geopoint`` and ``Geoshape``
.............................

The CrateDB SQLAlchemy dialect provides two geospatial types:

- ``Geopoint``, which represents a longitude and latitude coordinate
- ``Geoshape``, which is used to store geometric `GeoJSON geometry objects`_

To use these types, you can create columns, like so::

    >>> class City(Base):
    ...
    ...    __tablename__ = 'cities'
    ...    name = sa.Column(sa.String, primary_key=True)
    ...    coordinate = sa.Column(types.Geopoint)
    ...    area = sa.Column(types.Geoshape)

There are multiple ways of creating a geopoint. Firstly, you can define it as
a tuple of ``(longitude, latitude)``::

    >>> point = (139.76, 35.68)

Secondly, you can define it as a geojson ``Point`` object::

    >>> from geojson import Point
    >>> point = Point(coordinates=(139.76, 35.68))

To create a geoshape, you can use a geojson shape object, such as a ``Polygon``::

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

You can then set the values of the ``Geopoint`` and ``Geoshape`` columns::

    >>> tokyo = City(name="Tokyo", coordinate=point, area=area)
    >>> session.add(tokyo)
    >>> session.commit()

Querying
========

When the ``commit`` method is called, two ``INSERT`` statements are sent to
CrateDB. However, the newly inserted rows aren't immediately available for
querying because the table index is only updated periodically (one second, by
default, which is a short time for me and you, but a long time for your code).

You can request a `table refresh`_ to update the index manually::

    >>> refresh("characters")

.. NOTE::

    Newly inserted rows can still be queried immediately if a lookup by primary
    key is done.

Here's what a regular select might look like::

    >>> query = session.query(Character).order_by(Character.name)
    >>> [(c.name, c.details['gender']) for c in query]
    [('Arthur Dent', 'male'), ('Tricia McMillan', 'female')]

You can also select a portion of each record, and this even works inside
`Object`_ columns::

    >>> sorted(session.query(Character.details['gender']).all())
    [('female',), ('male',)]

You can also filter on attributes inside the `Object`_ column:

    >>> query = session.query(Character.name)
    >>> query.filter(Character.details['gender'] == 'male').all()
    [('Arthur Dent',)]

To filter on an `ObjectArray`_, you have to do something like this::

    >>> from sqlalchemy.sql import operators

    >>> query = session.query(Character.name)
    >>> query.filter(Character.more_details['foo'].any(1, operator=operators.eq)).all()
    [(u'Arthur Dent',)]

Here, we're using the `any`_ method along with the `eq`_ Python `operator`_  to
match the value ``1`` against the ``foo`` key of any dictionary in the
``more_details`` list.

Only one of the keys has to match for the row to be returned.

This works, because ``ObjectArray`` keys return a list of all values for that
key, like so:

    >>> arthur.more_details['foo']
    [1, 2, 3]

Querying a key of an ``ObjectArray`` column will return all values for that key
for all matching rows::

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

Fulltext Search in CrateDB is done with the `MATCH predicate`_.

The CrateDB SQLAlchemy dialect provides a ``match`` function in the
``predicates`` module, which can be used to search one or multiple fields.

Here's an example use of the ``match`` function::

    >>> from crate.client.sqlalchemy.predicates import match

    >>> session.query(Character.name) \
    ...     .filter(match(Character.name_ft, 'Arthur')) \
    ...     .all()
    [('Arthur Dent',)]

In this example, we're selecting character ``name`` values, and returning all
rows where the ``name_ft`` index matches the string ``Arthur``.

.. NOTE::

    To use fulltext searches on a column, an explicit fulltext index with an
    analyzer must be created on the column. Consult the `fulltext indices
    reference`_ for more information.

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

      The ``MATCH`` predicate `arguments reference`_ has more in-depth
      information.

:``term``:

  The term to match against.

  This string is analyzed and the resulting tokens are compared to the index.

:``match_type``: *(optional)*

  The `match type`_.

  Determine how the ``term`` is applied and the `score`_ calculated.

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

To get the relevance of a matching row, the row `score`_ can be used.

The score is relative to other result rows produced by your query. The higher
the score, the more relevant the result row.

  .. COMMENT

     Keep this anonymous link in place so it doesn't get lost. We have to use
     this link format because of the leading underscore.

The score is made available via the ``_score`` column, which is a virtual
column, meaning that it doesn't exist on the source table, and in most cases,
should not be included in your :ref:`table definition <table-definition>`.

You can select ``_score`` as part of a query, like this::

    >>> session.query(Character.name, '_score') \
    ...     .filter(match(Character.quote_ft, 'space')) \
    ...     .all()
    [('Tricia McMillan', ...)]

Here, we're matching the term ``space`` against the ``quote_ft`` fulltext
index. And we're selecting the ``name`` column of the character by using the
table definition But notice that we select the associated score by passing in
the virtual column name as a string (``_score``) instead of using a defined
column on the ``Character`` class.


.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _Object-Relational Mapping: https://en.wikipedia.org/wiki/Object-relational_mapping
.. _dialect: http://docs.sqlalchemy.org/en/latest/dialects/
.. _SQLAlchemy tutorial: http://docs.sqlalchemy.org/en/latest/orm/tutorial.html
.. _database URL: http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
.. _psql.port: https://crate.io/docs/crate/reference/en/latest/config/node.html#ports
.. _SSL server certificates: https://crate.io/docs/crate/reference/en/latest/admin/ssl.html
.. _SQLAlchemy library: http://www.sqlalchemy.org/library.html
.. _Database API: http://www.python.org/dev/peps/pep-0249/
.. _declarative system: http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/
.. _Session: http://docs.sqlalchemy.org/en/latest/orm/session.html
.. _specified: https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#strict
.. _dynamic values: https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#dynamic
.. _table refresh: https://crate.io/docs/crate/reference/en/latest/general/dql/refresh.html
.. _list: https://docs.python.org/3/library/stdtypes.html#lists
.. _dictionaries: https://docs.python.org/3/library/stdtypes.html?highlight=lists#dict
.. _UPDATE: https://crate.io/docs/crate/reference/en/latest/general/dml.html#updating-data
.. _eq: https://docs.python.org/2/library/operator.html#operator.eq
.. _operator: https://docs.python.org/2/library/operator.html
.. _any: http://docs.sqlalchemy.org/en/latest/core/type_basics.html#sqlalchemy.types.ARRAY.Comparator.any
.. _tuple: https://docs.python.org/3/library/stdtypes.html#sequence-types-list-tuple-range
.. _count result rows: http://docs.sqlalchemy.org/en/latest/orm/tutorial.html#counting
.. _MATCH predicate: https://crate.io/docs/crate/reference/en/latest/general/dql/fulltext.html#match-predicate
.. _arguments reference: https://crate.io/docs/crate/reference/en/latest/general/dql/fulltext.html#arguments
.. _boost values: https://crate.io/docs/crate/reference/en/latest/general/dql/fulltext.html?highlight=fulltext#arguments
.. _match type: https://crate.io/docs/crate/reference/en/latest/general/dql/fulltext.html#predicates-match-types
.. _match options: https://crate.io/docs/stable/sql/fulltext.html#options
.. _fulltext indices reference: https://crate.io/docs/crate/reference/en/latest/general/ddl/fulltext-indices.html
.. _score: https://crate.io/docs/crate/reference/en/latest/general/dql/fulltext.html#usage
.. _working with tables: http://docs.sqlalchemy.org/en/latest/core/metadata.html
.. _UUIDs: https://docs.python.org/3/library/uuid.html
.. _geojson geometry objects: https://tools.ietf.org/html/rfc7946#section-3.1
