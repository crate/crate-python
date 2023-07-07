.. _sqlalchemy-working-with-types:

==============================================
SQLAlchemy: Working with special CrateDB types
==============================================

This section of the documentation shows how to work with special data types
from the CrateDB SQLAlchemy dialect. Currently, these are:

- Container types ``ObjectType`` and ``ObjectArray``.
- Geospatial types ``Geopoint`` and ``Geoshape``.


.. rubric:: Table of Contents

.. contents::
   :local:


Introduction
============

Import the relevant symbols:

    >>> import sqlalchemy as sa
    >>> from datetime import datetime
    >>> from geojson import Point, Polygon
    >>> from sqlalchemy import delete, func, text
    >>> from sqlalchemy.orm import sessionmaker
    >>> from sqlalchemy.sql import operators
    >>> try:
    ...     from sqlalchemy.orm import declarative_base
    ... except ImportError:
    ...     from sqlalchemy.ext.declarative import declarative_base
    >>> from uuid import uuid4
    >>> from crate.client.sqlalchemy.types import ObjectType, ObjectArray
    >>> from crate.client.sqlalchemy.types import Geopoint, Geoshape

Establish a connection to the database, see also :ref:`sa:engines_toplevel`
and :ref:`connect`:

    >>> engine = sa.create_engine(f"crate://{crate_host}")
    >>> connection = engine.connect()

Create an SQLAlchemy :doc:`Session <sa:orm/session_basics>`:

    >>> session = sessionmaker(bind=engine)()
    >>> Base = declarative_base()


Introduction to container types
===============================

In a document oriented database, it is a common pattern to store objects within
a single field. For such cases, the CrateDB SQLAlchemy dialect provides the
``ObjectType`` and ``ObjectArray`` types.

The ``ObjectType`` type effectively implements a dictionary- or map-like type. The
``ObjectArray`` type maps to a Python list of dictionaries.

For exercising those features, let's define a schema using SQLAlchemy's
:ref:`sa:orm_declarative_mapping`:

    >>> def gen_key():
    ...     return str(uuid4())

    >>> class Character(Base):
    ...     __tablename__ = 'characters'
    ...     id = sa.Column(sa.String, primary_key=True, default=gen_key)
    ...     name = sa.Column(sa.String)
    ...     quote = sa.Column(sa.String)
    ...     details = sa.Column(ObjectType)
    ...     more_details = sa.Column(ObjectArray)

In CrateDB's SQL dialect, those container types map to :ref:`crate-reference:type-object`
and :ref:`crate-reference:type-array`.


``ObjectType``
==============

Let's add two records which have additional items within the ``details`` field.
Note that item keys have not been defined in the DDL schema, effectively
demonstrating the :ref:`DYNAMIC column policy <crate-reference:type-object-columns-dynamic>`.

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

After ``INSERT`` statements are submitted to the database, the newly inserted
records aren't immediately available for retrieval because the index is only
updated periodically (default: each second). In order to synchronize that,
refresh the table:

    >>> _ = connection.execute(text("REFRESH TABLE characters"))

A subsequent select query will see all the records:

    >>> query = session.query(Character).order_by(Character.name)
    >>> [(c.name, c.details['gender']) for c in query]
    [('Arthur Dent', 'male'), ('Tricia McMillan', 'female')]

It is also possible to just select a part of the document, even inside the
``ObjectType`` type:

    >>> sorted(session.query(Character.details['gender']).all())
    [('female',), ('male',)]

In addition, filtering on the attributes inside the ``details`` column is also
possible:

    >>> query = session.query(Character.name)
    >>> query.filter(Character.details['gender'] == 'male').all()
    [('Arthur Dent',)]

Update dictionary
-----------------

The SQLAlchemy CrateDB dialect supports change tracking deep down the nested
levels of a ``ObjectType`` type field. For example, the following query will only
update the ``gender`` key. The ``species`` key which is on the same level will
be left untouched.

    >>> char = session.query(Character).filter_by(name='Arthur Dent').one()
    >>> char.details['gender'] = 'manly man'
    >>> session.commit()
    >>> session.refresh(char)

    >>> char.details['gender']
    'manly man'

    >>> char.details['species']
    'human'

Update nested dictionary
------------------------

    >>> char_nested = Character(id='1234id')
    >>> char_nested.details = {"name": {"first": "Arthur", "last": "Dent"}}
    >>> session.add(char_nested)
    >>> session.commit()

    >>> char_nested = session.query(Character).filter_by(id='1234id').one()
    >>> char_nested.details['name']['first'] = 'Trillian'
    >>> char_nested.details['size'] = 45
    >>> session.commit()

Refresh and query "characters" table:

    >>> _ = connection.execute(text("REFRESH TABLE characters"))
    >>> session.refresh(char_nested)

    >>> char_nested = session.query(Character).filter_by(id='1234id').one()
    >>> pprint(char_nested.details)
    {'name': {'first': 'Trillian', 'last': 'Dent'}, 'size': 45}


``ObjectArray``
===============

Note that opposed to the ``ObjectType`` type, the ``ObjectArray`` type isn't smart
and doesn't have intelligent change tracking. Therefore, the generated
``UPDATE`` statement will affect the whole list:

    >>> char.more_details = [{'foo': 1, 'bar': 10}, {'foo': 2}]
    >>> session.commit()

    >>> char.more_details.append({'foo': 3})
    >>> session.commit()

This will generate an ``UPDATE`` statement which looks roughly like this::

    "UPDATE characters SET more_details = ? ...", ([{'foo': 1, 'bar': 10}, {'foo': 2}, {'foo': 3}],)

.. hidden:

    >>> _ = connection.execute(text("REFRESH TABLE characters"))
    >>> session.refresh(char)

To run queries against fields of ``ObjectArray`` types, use the
``.any(value, operator=operators.eq)`` method on a subscript, because accessing
fields of object arrays (e.g. ``Character.more_details['foo']``) returns an
array of the field type.

Only one of the objects inside the array has to match in order for the result
to be returned:

    >>> query = session.query(Character.name)
    >>> query.filter(Character.more_details['foo'].any(1, operator=operators.eq)).all()
    [('Arthur Dent',)]

Querying a field of an object array will result in an array of
all values of that field of all objects in that object array:

    >>> query = session.query(Character.more_details['foo']).order_by(Character.name)
    >>> query.all()
    [([1, 2, 3],), (None,), (None,)]


Geospatial types
================

CrateDB's geospatial types, such as :ref:`crate-reference:type-geo_point`
and :ref:`crate-reference:type-geo_shape`, can also be used within an
SQLAlchemy declarative schema:

    >>> class City(Base):
    ...    __tablename__ = 'cities'
    ...    name = sa.Column(sa.String, primary_key=True)
    ...    coordinate = sa.Column(Geopoint)
    ...    area = sa.Column(Geoshape)

One way of inserting these types is using the `geojson`_ library, to create
points or shapes:

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
    >>> point = Point(coordinates=(139.76, 35.68))

These two objects can then be added to an SQLAlchemy model and added to the
session:

    >>> tokyo = City(coordinate=point, area=area, name='Tokyo')
    >>> session.add(tokyo)
    >>> session.commit()
    >>> _ = connection.execute(text("REFRESH TABLE cities"))

When reading them back, they are retrieved as the corresponding `geojson`_
objects:

    >>> query = session.query(City.name, City.coordinate, City.area)
    >>> query.all()
     [('Tokyo', (139.75999999791384, 35.67999996710569), {"coordinates": [[[139.806, 35.515], [139.919, 35.703], [139.768, 35.817], [139.575, 35.76], [139.584, 35.619], [139.806, 35.515]]], "type": "Polygon"})]


.. hidden: Disconnect from database

    >>> session.close()
    >>> connection.close()
    >>> engine.dispose()


.. _geojson: https://pypi.org/project/geojson/
