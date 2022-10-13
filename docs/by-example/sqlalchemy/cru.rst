========================================
SQLAlchemy: Create, retrieve, and update
========================================

This section of the documentation, related to CrateDB's SQLAlchemy integration,
focuses on showing specific details when querying, inserting, and updating
records. It covers filtering and limiting, insert and update default values,
and updating complex data types with nested Python dictionaries.

.. rubric:: Table of Contents

.. contents::
   :local:


Introduction
============

Import the relevant symbols:

    >>> import sqlalchemy as sa
    >>> from datetime import datetime
    >>> from sqlalchemy.ext.declarative import declarative_base
    >>> from sqlalchemy.orm import sessionmaker
    >>> from sqlalchemy.sql import text
    >>> from crate.client.sqlalchemy.types import ObjectArray

Establish a connection to the database:

    >>> engine = sa.create_engine(f"crate://{crate_host}")
    >>> connection = engine.connect()

Define the ORM schema for the ``Location`` entity:

    >>> Base = declarative_base(bind=engine)

    >>> class Location(Base):
    ...     __tablename__ = 'locations'
    ...     name = sa.Column(sa.String, primary_key=True)
    ...     kind = sa.Column(sa.String)
    ...     date = sa.Column(sa.Date, default=lambda: datetime.utcnow().date())
    ...     datetime_tz = sa.Column(sa.DateTime, default=datetime.utcnow)
    ...     datetime_notz = sa.Column(sa.DateTime, default=datetime.utcnow)
    ...     nullable_datetime = sa.Column(sa.DateTime)
    ...     nullable_date = sa.Column(sa.Date)
    ...     flag = sa.Column(sa.Boolean)
    ...     details = sa.Column(ObjectArray)

Create a session with SQLAlchemy:

    >>> session = sessionmaker(bind=engine)()

Retrieve
========

Using the connection to execute a select statement:

    >>> result = connection.execute('select name from locations order by name')
    >>> result.rowcount
    13

    >>> result.first()
    ('Aldebaran',)

Using the ORM to query the locations:

    >>> locations = session.query(Location).order_by('name')
    >>> [l.name for l in locations if l is not None][:2]
    ['Aldebaran', 'Algol']

With limit and offset:

    >>> locations = session.query(Location).order_by('name').offset(1).limit(2)
    >>> [l.name for l in locations if l is not None]
    ['Algol', 'Allosimanius Syneca']

With filter:

    >>> location = session.query(Location).filter_by(name='Algol').one()
    >>> location.name
    'Algol'

Order by:

    >>> locations = session.query(Location).filter(Location.name != None).order_by(sa.desc(Location.name))
    >>> locations = locations.limit(2)
    >>> [l.name for l in locations]
    ['Outer Eastern Rim', 'North West Ripple']


Create
======

Insert a new location:

    >>> location = Location()
    >>> location.name = 'Earth'
    >>> location.kind = 'Planet'
    >>> location.flag = True

    >>> session.add(location)
    >>> session.flush()

Refresh "locations" table:

    >>> _ = connection.execute("REFRESH TABLE locations")

Inserted location is available:

    >>> location = session.query(Location).filter_by(name='Earth').one()
    >>> location.name
    'Earth'

Retrieve the location from the database:

    >>> session.refresh(location)
    >>> location.name
    'Earth'

Date should have been set at the insert due to default value via Python method:

    >>> from datetime import datetime
    >>> now = datetime.utcnow()
    >>> dt = location.date

    >>> dt.year == now.year
    True

    >>> dt.month == now.month
    True

    >>> dt.day == now.day
    True

    >>> (now - location.datetime_tz).seconds < 4
    True

Verify the return type of date and datetime:

    >>> type(location.date)
    <class 'datetime.date'>

    >>> type(location.datetime_tz)
    <class 'datetime.datetime'>

    >>> type(location.datetime_notz)
    <class 'datetime.datetime'>

The location also has a date and datetime property which both are nullable and
aren't set when the row is inserted as there is no default method:

    >>> location.nullable_datetime is None
    True

    >>> location.nullable_date is None
    True


Update
======

The datetime and date can be set using a update statement:

    >>> location.nullable_date = datetime.utcnow().date()
    >>> location.nullable_datetime = datetime.utcnow()
    >>> session.flush()

Refresh "locations" table:

    >>> _ = connection.execute("REFRESH TABLE locations")

Boolean values get set natively:

    >>> location.flag
    True

Reload the object from the db:

    >>> session.refresh(location)

And verify that the date and datetime was persisted:

    >>> location.nullable_datetime is not None
    True

    >>> location.nullable_date is not None
    True

Update a record using SQL:

    >>> result = connection.execute("update locations set kind='Heimat' where name='Earth'")
    >>> result.rowcount
    1

Update multiple records:

    >>> for x in range(10):
    ...     loc = Location()
    ...     loc.name = 'Ort %d' % x
    ...     loc.kind = 'Update'
    ...     session.add(loc)
    ...     session.flush()

Refresh table:

    >>> _ = connection.execute("REFRESH TABLE locations")

Query database:

    >>> result = connection.execute("update locations set flag=true where kind='Update'")
    >>> result.rowcount
    10

Check that number of affected documents of update without ``where-clause`` matches number of all
documents in the table:

    >>> result = connection.execute(u"update locations set kind='Überall'")
    >>> result.rowcount == connection.execute("select * from locations limit 100").rowcount
    True

    >>> session.commit()

Refresh "locations" table:

    >>> _ = connection.execute("REFRESH TABLE locations")

Test that objects can be used as list too:

    >>> location = session.query(Location).filter_by(name='Folfanga').one()
    >>> location.details = [{'size': 'huge'}, {'clima': 'cold'}]

    >>> session.commit()
    >>> session.refresh(location)

    >>> location.details
    [{'size': 'huge'}, {'clima': 'cold'}]

Update the record:

    >>> location.details[1] = {'clima': 'hot'}

    >>> session.commit()
    >>> session.refresh(location)

    >>> location.details
    [{'size': 'huge'}, {'clima': 'hot'}]

Reset the record:

    >>> location.details = []
    >>> session.commit()
    >>> session.refresh(location)

    >>> location.details
    []

Update nested dictionary:

    >>> from crate.client.sqlalchemy.types import Craty
    >>> class Character(Base):
    ...     __tablename__ = 'characters'
    ...     id = sa.Column(sa.String, primary_key=True)
    ...     details = sa.Column(Craty)
    >>> char = Character(id='1234id')
    >>> char.details = {"name": {"first": "Arthur", "last": "Dent"}}
    >>> session.add(char)
    >>> session.commit()

    >>> char = session.query(Character).filter_by(id='1234id').one()
    >>> char.details['name']['first'] = 'Trillian'
    >>> char.details['size'] = 45
    >>> session.commit()

Refresh "characters" table:

    >>> _ = connection.execute("REFRESH TABLE characters")

    >>> session.refresh(char)
    >>> pprint(char.details)
    {'name': {'first': 'Trillian', 'last': 'Dent'}, 'size': 45}

.. Hidden: close connection

    >>> connection.close()
