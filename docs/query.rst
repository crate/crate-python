.. _query:

=============
Query CrateDB
=============

.. NOTE::

   This page documents the CrateDB `Database API`_ client.

   For help using the `SQLAlchemy`_ dialect, consult
   :ref:`the SQLAlchemy dialect documentation <using-sqlalchemy>`.

.. SEEALSO::

   Supplementary information about the CrateDB Database API client can be found
   in the :ref:`data types appendix <data-types-db-api>`.

   For general help using the Database API, consult `PEP 0249`_.

.. rubric:: Table of contents

.. contents::
   :local:

.. _cursor:

Using a cursor
==============

After :ref:`connecting to CrateDB <connect>`, you can execute queries via a
`database cursor`_.

Open a cursor like so::

    >>> cursor = connection.cursor()

.. _inserts:

Inserting data
==============

Regular inserts
---------------

Regular inserts are possible with the ``execute()`` method, like so:

    >>> cursor.execute(
    ...     """INSERT INTO locations (name, date, kind, position)
    ...             VALUES (?, ?, ?, ?)""",
    ...     ("Einstein Cross", "2007-03-11", "Quasar", 7))

Here, the values of the `tuple`_  (the second argument) are safely interpolated
into the query string (the first argument) where the ``?`` characters appear,
in the order they appear.

.. WARNING::

   Never use string concatenation to build query strings.

   Always use the string interpolation feature of the client library (per the
   above example) to guard against malicious input.

Bulk inserts
------------

`Bulk inserts`_ are possible with the ``executemany()`` method, which takes a
`list`_ of tuples to insert::

    >>> cursor.executemany(
    ...     """INSERT INTO locations (name, date, kind, position)
    ...             VALUES (?, ?, ?, ?)""",
    ...     [('Cloverleaf', '2007-03-11', 'Quasar', 7),
    ...      ('Old Faithful', '2007-03-11', 'Quasar', 7)])
    [{'rowcount': 1}, {'rowcount': 1}]

The ``executemany()`` method returns a result `dictionary`_ for every tuple.
This dictionary always has a ``rowcount`` key, indicating how many rows were
inserted. If an error occures the ``rowcount`` value is ``-2`` and the
dictionary may additionally have an ``error_message`` key.

.. _selects:

Selecting data
==============

Executing a query
-----------------

Selects can be performed with the ``execute()`` method, like so::

    >>> cursor.execute("SELECT name FROM locations WHERE name = ?", ("Algol",))

Like with :ref:`inserts <inserts>`, here, the single value of the tuple (the
second argument) is safely interpolated into the query string (the first
argument) where the ``?`` character appears.

.. WARNING::

   As with :ref:`inserts <inserts>`, always use string interpolation.

After executing a query, you can fetch the results using one of three fetch
methods, detailed below.

Fetching results
----------------

.. _fetchone:

``fetchone()``
..............

After executing a query, a ``fetchone()`` call on the cursor returns an list
representing the next row from the result set:

    >>> result = cursor.fetchone()
    ['Algol']

You can call ``fetchone()`` multiple times to return multiple rows.

If no more rows are available, ``None`` is returned.

.. TIP::

   The ``cursor`` object is an `iterator`_, and the ``fetchone()`` method is an
   alias for ``next()``.

.. _fetchmany:

``fetchmany()``
...............

After executing a query, a ``fetch_many()`` call with a numeric argument
returns the specified number of result rows:

    >>> cursor.execute("SELECT name FROM locations order by name")
    >>> result = cursor.fetchmany(2)
    >>> pprint(result)
    [['Aldebaran'], ['Algol']]

If a number is not given as an argument, ``fetch_many()`` will return a result
list with one result row:

    >>> cursor.fetchmany()
    [['Allosimanius Syneca']]

.. _fetchall:

``fetchall()``
..............

After executing a query, a ``fetchall()`` call on the cursor returns all
remaining rows::

    >>> cursor.execute("SELECT name FROM locations ORDER BY name")
    >>> cursor.fetchall()
    [['Aldebaran'],
     ['Algol'],
     ['Allosimanius Syneca'],
    ...
     ['Old Faithful'],
     ['Outer Eastern Rim']]

Accessing column names
======================

Result rows are lists, not dictionaries. Which means that they do use contain
column names for keys. If you want to access column names, you must use
``cursor.description``.

The `DB API 2.0`_ specification `defines`_ seven description attributes per
column, but only the first one (column name) is supported by this library. All
other attributes are ``None``.

Let's say you have a query like this:

    >>> cursor.execute("SELECT * FROM locations ORDER BY name")
    >>> cursor.fetchone()
    [1373932800000,
     None,
     'Max Quordlepleen claims that the only thing left ...',
    ...
     None,
     1]

The cursor ``description`` might look like this:

    >>> cursor.description
    (('date', None, None, None, None, None, None),
     ('datetime_tz', None, None, None, None, None, None),
     ('datetime_notz', None, None, None, None, None, None),
     ('description', None, None, None, None, None, None),
    ...
     ('nullable_datetime', None, None, None, None, None, None),
     ('position', None, None, None, None, None, None))

You can turn this into something more manageable with a `list comprehension`_::

    >>> [column[0] for column in cursor.description]
    ['date', 'datetime_tz', 'datetime_notz', ..., 'nullable_datetime', 'position']


Data type conversion
====================

The cursor object can optionally convert database types to native Python data
types. There is a default implementation for the CrateDB data types ``IP`` and
``TIMESTAMP`` on behalf of the ``DefaultTypeConverter``.

::

    >>> from crate.client.converter import DefaultTypeConverter
    >>> from crate.client.cursor import Cursor
    >>> cursor = connection.cursor(converter=DefaultTypeConverter())

    >>> cursor.execute("SELECT datetime_tz, datetime_notz FROM locations ORDER BY name")

    >>> cursor.fetchone()
    [datetime.datetime(2022, 7, 18, 18, 10, 36, 758000), datetime.datetime(2022, 7, 18, 18, 10, 36, 758000)]


Custom data type conversion
===========================

By providing a custom converter instance, you can define your own data type
conversions. For investigating the list of available data types, please either
inspect the ``DataType`` enum, or the documentation about the list of available
`CrateDB data type identifiers for the HTTP interface`_.

This example creates and applies a simple custom converter for converging
CrateDB's ``BOOLEAN`` type to Python's ``str`` type. It is using a simple
converter function defined as ``lambda``, which assigns ``yes`` for boolean
``True``, and ``no`` otherwise.

::

    >>> from crate.client.converter import Converter, DataType

    >>> converter = Converter()
    >>> converter.set(DataType.BOOLEAN, lambda value: value is True and "yes" or "no")
    >>> cursor = connection.cursor(converter=converter)

    >>> cursor.execute("SELECT flag FROM locations ORDER BY name")

    >>> cursor.fetchone()
    ['no']


``TIMESTAMP`` conversion with time zone
=======================================

Based on the data type converter functionality, the driver offers a convenient
interface to make it return timezone-aware ``datetime`` objects, using the
desired time zone.

For your reference, in the following examples, epoch 1658167836758 is
``Mon, 18 Jul 2022 18:10:36 GMT``.

::

    >>> import datetime
    >>> tz_mst = datetime.timezone(datetime.timedelta(hours=7), name="MST")
    >>> ccursor = connection.cursor(time_zone=tz_mst)

    >>> ccursor.execute("SELECT datetime_tz FROM locations ORDER BY name")

    >>> cursor.fetchone()
    [datetime.datetime(2022, 7, 19, 1, 10, 36, 758000, tzinfo=datetime.timezone(datetime.timedelta(seconds=25200), 'MST'))]

For the ``time_zone`` keyword argument, different data types are supported.
The available options are:

- ``datetime.timezone.utc``
- ``datetime.timezone(datetime.timedelta(hours=7), name="MST")``
- ``pytz.timezone("Australia/Sydney")``
- ``zoneinfo.ZoneInfo("Australia/Sydney")``
- ``+0530`` (UTC offset in string format)

Let's exercise all of them.

::

    >>> ccursor.time_zone = datetime.timezone.utc
    >>> ccursor.execute("SELECT datetime_tz FROM locations ORDER BY name")
    >>> ccursor.fetchone()
    [datetime.datetime(2022, 7, 18, 18, 10, 36, 758000, tzinfo=datetime.timezone.utc)]

    >>> import pytz
    >>> ccursor.time_zone = pytz.timezone("Australia/Sydney")
    >>> ccursor.execute("SELECT datetime_tz FROM locations ORDER BY name")
    >>> ccursor.fetchone()
    ['foo', datetime.datetime(2022, 7, 19, 4, 10, 36, 758000, tzinfo=<DstTzInfo 'Australia/Sydney' AEST+10:00:00 STD>)]

    >>> import zoneinfo
    >>> ccursor.time_zone = zoneinfo.ZoneInfo("Australia/Sydney")
    >>> ccursor.execute("SELECT datetime_tz FROM locations ORDER BY name")
    >>> ccursor.fetchone()
    [datetime.datetime(2022, 7, 19, 4, 10, 36, 758000, tzinfo=zoneinfo.ZoneInfo(key='Australia/Sydney'))]

    >>> ccursor.time_zone = "+0530"
    >>> ccursor.execute("SELECT datetime_tz FROM locations ORDER BY name")
    >>> ccursor.fetchone()
    [datetime.datetime(2022, 7, 18, 23, 40, 36, 758000, tzinfo=datetime.timezone(datetime.timedelta(seconds=19800), '+0530'))]


.. _Bulk inserts: https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#bulk-operations
.. _CrateDB data type identifiers for the HTTP interface: https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#column-types
.. _Database API: http://www.python.org/dev/peps/pep-0249/
.. _database cursor: https://en.wikipedia.org/wiki/Cursor_(databases)
.. _DB API 2.0: http://www.python.org/dev/peps/pep-0249/
.. _defines: https://legacy.python.org/dev/peps/pep-0249/#description
.. _dictionary: https://docs.python.org/2/tutorial/datastructures.html#dictionaries
.. _iterator: https://wiki.python.org/moin/Iterator
.. _list comprehension: https://docs.python.org/2/tutorial/datastructures.html#list-comprehensions
.. _list: https://docs.python.org/2/library/stdtypes.html#sequence-types-str-unicode-list-tuple-bytearray-buffer-xrange
.. _PEP 0249: http://www.python.org/dev/peps/pep-0249/
.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _tuple: https://docs.python.org/2/tutorial/datastructures.html#tuples-and-sequences
