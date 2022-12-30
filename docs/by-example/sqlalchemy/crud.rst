.. _sqlalchemy-crud:

================================================
SQLAlchemy: Create, retrieve, update, and delete
================================================

This section of the documentation shows how to query, insert, update and delete
records using CrateDB's SQLAlchemy integration, it includes common scenarios
like:

- Filtering records
- Limiting result sets
- Inserts and updates with default values


.. rubric:: Table of Contents

.. contents::
   :local:


Introduction
============

Import the relevant symbols:

    >>> import sqlalchemy as sa
    >>> from datetime import datetime
    >>> from sqlalchemy import delete, func, text
    >>> from sqlalchemy.orm import sessionmaker
    >>> try:
    ...     from sqlalchemy.orm import declarative_base
    ... except ImportError:
    ...     from sqlalchemy.ext.declarative import declarative_base
    >>> from crate.client.sqlalchemy.types import ObjectArray

Establish a connection to the database, see also :ref:`sa:engines_toplevel`
and :ref:`connect`:

    >>> engine = sa.create_engine(f"crate://{crate_host}")
    >>> connection = engine.connect()

Define the ORM schema for the ``Location`` entity using SQLAlchemy's
:ref:`sa:orm_declarative_mapping`:

    >>> Base = declarative_base()

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

Create an SQLAlchemy :doc:`Session <sa:orm/session_basics>`:

    >>> session = sessionmaker(bind=engine)()


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

    >>> _ = connection.execute(text("REFRESH TABLE locations"))

Inserted location is available:

    >>> location = session.query(Location).filter_by(name='Earth').one()
    >>> location.name
    'Earth'

Retrieve the location from the database:

    >>> session.refresh(location)
    >>> location.name
    'Earth'

Three ``date``/``datetime`` columns are defined with default values, so
creating a new record will automatically set them:

    >>> type(location.date)
    <class 'datetime.date'>

    >>> type(location.datetime_tz)
    <class 'datetime.datetime'>

    >>> type(location.datetime_notz)
    <class 'datetime.datetime'>

The location instance also has other ``date`` and ``datetime`` attributes which
are nullable. Because there is no default value defined in the ORM schema for
them, they are not set when the record is inserted:

    >>> location.nullable_datetime is None
    True

    >>> location.nullable_date is None
    True

.. hidden:

    >>> from datetime import datetime, timedelta
    >>> now = datetime.utcnow()

    >>> (now - location.datetime_tz).seconds < 4
    True

    >>> (now.date() - location.date) == timedelta(0)
    True


Retrieve
========

Using the connection to execute a select statement:

    >>> result = connection.execute(text('select name from locations order by name'))
    >>> result.rowcount
    14

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

    >>> locations = session.query(Location).filter(Location.name is not None).order_by(sa.desc(Location.name))
    >>> locations = locations.limit(2)
    >>> [l.name for l in locations]
    ['Outer Eastern Rim', 'North West Ripple']


Update
======

Back to our original object ``Location(Earth)``.

    >>> location = session.query(Location).filter_by(name='Earth').one()

The datetime and date can be set using an update statement:

    >>> location.nullable_date = datetime.utcnow().date()
    >>> location.nullable_datetime = datetime.utcnow()
    >>> session.flush()

Refresh "locations" table:

    >>> _ = connection.execute(text("REFRESH TABLE locations"))

Boolean values get set natively:

    >>> location.flag
    True

Reload the object from the database:

    >>> session.refresh(location)

And verify that the date and datetime was persisted:

    >>> location.nullable_datetime is not None
    True

    >>> location.nullable_date is not None
    True

Update a record using SQL:

    >>> with engine.begin() as conn:
    ...     result = conn.execute(text("update locations set kind='Heimat' where name='Earth'"))
    ...     result.rowcount
    1

Update multiple records:

    >>> for x in range(10):
    ...     loc = Location()
    ...     loc.name = 'Ort %d' % x
    ...     loc.kind = 'Update'
    ...     session.add(loc)
    >>> session.flush()

Refresh table:

    >>> _ = connection.execute(text("REFRESH TABLE locations"))

Update multiple records using SQL:

    >>> with engine.begin() as conn:
    ...     result = conn.execute(text("update locations set flag=true where kind='Update'"))
    ...     result.rowcount
    10

Update all records using SQL, and check that the number of documents affected
of an update without ``where-clause`` matches the number of all documents in
the table:

    >>> with engine.begin() as conn:
    ...     result = conn.execute(text(u"update locations set kind='Überall'"))
    ...     result.rowcount == conn.execute(text("select * from locations limit 100")).rowcount
    True

    >>> session.commit()

Refresh "locations" table:

    >>> _ = connection.execute(text("REFRESH TABLE locations"))

Objects can be used within lists, too:

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

.. seealso::

    The documentation section :ref:`sqlalchemy-working-with-types` has more
    details about this topic.


Delete
======

Deleting a record with SQLAlchemy works like this.

    >>> session.query(Location).count()
    24

    >>> location = session.query(Location).first()
    >>> session.delete(location)
    >>> session.commit()
    >>> session.flush()

    >>> _ = connection.execute(text("REFRESH TABLE locations"))

    >>> session.query(Location).count()
    23


.. hidden: Disconnect from database

    >>> session.close()
    >>> connection.close()
    >>> engine.dispose()
