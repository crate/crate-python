.. _query:

=============
Query CrateDB
=============

.. NOTE::

    This page documents the CrateDB client, implementing the
    `Python Database API Specification v2.0`_ (PEP 249).

    For help using the `SQLAlchemy`_ dialect, consult
    :ref:`the SQLAlchemy dialect documentation <using-sqlalchemy>`.

.. SEEALSO::

    Supplementary information about the CrateDB Database API client can be found
    in the :ref:`data types appendix <data-types-db-api>`.

.. rubric:: Table of contents

.. contents::
   :local:

.. _cursor:

Using a cursor
==============

After :ref:`connecting to CrateDB <connect>`, you can execute queries via a
`database cursor`_.

Open a cursor like so:

    >>> cursor = connection.cursor()

.. _inserts:

Inserting data
==============

Regular inserts
---------------

Regular inserts are possible with the ``execute()`` method, like so:

    >>> cursor.execute(
    ...     "INSERT INTO locations (name, date, kind, position) VALUES (?, ?, ?, ?)",
    ...     ("Einstein Cross", "2007-03-11", "Quasar", 7))

Here, the values of the :class:`py:tuple` (the second argument) are safely
interpolated into the query string (the first argument) where the ``?``
characters appear, in the order they appear.

.. WARNING::

    Never use string concatenation to build query strings.

    Always use the parameter interpolation feature of the client library to
    guard against malicious input, as demonstrated in the example above.

Bulk inserts
------------

:ref:`Bulk inserts <crate-reference:http-bulk-ops>` are possible with the
``executemany()`` method, which takes a :class:`py:list` of tuples to insert:

    >>> cursor.executemany(
    ...     "INSERT INTO locations (name, date, kind, position) VALUES (?, ?, ?, ?)",
    ...     [('Cloverleaf', '2007-03-11', 'Quasar', 7),
    ...      ('Old Faithful', '2007-03-11', 'Quasar', 7)])
    [{'rowcount': 1}, {'rowcount': 1}]

The ``executemany()`` method returns a result :class:`dictionary <py:dict>`
for every tuple. This dictionary always has a ``rowcount`` key, indicating
how many rows were inserted. If an error occurs, the ``rowcount`` value is
``-2``, and the dictionary may additionally have an ``error_message`` key.

.. _selects:

Selecting data
==============

Executing a query
-----------------

Selects can be performed with the ``execute()`` method, like so:

    >>> cursor.execute("SELECT name FROM locations WHERE name = ?", ("Algol",))

Like with :ref:`inserts <inserts>`, here, the single value of the tuple (the
second argument) is safely interpolated into the query string (the first
argument) where the ``?`` character appears.

.. WARNING::

    As with :ref:`inserts <inserts>`, always use parameter interpolation.

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

    The ``cursor`` object is an :term:`py:iterator`, and the ``fetchone()``
    method is an alias for ``next()``.

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
remaining rows:

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

The `Python Database API Specification v2.0`_ `defines`_ seven description
attributes per column, but only the first one (column name) is supported by
this library. All other attributes are ``None``.

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

You can turn this into something more manageable with :ref:`py:tut-listcomps`:

    >>> [column[0] for column in cursor.description]
    ['date', 'datetime_tz', 'datetime_notz', ..., 'nullable_datetime', 'position']


Data type conversion
====================

The cursor object can optionally convert database types to native Python data
types. There is a default implementation for the CrateDB data types ``IP`` and
``TIMESTAMP`` on behalf of the ``DefaultTypeConverter``.

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
:ref:`CrateDB data type identifiers for the HTTP interface
<crate-reference:http-column-types>`.

This example creates and applies a simple custom converter for converging
CrateDB's ``BOOLEAN`` type to Python's ``str`` type. It is using a simple
converter function defined as ``lambda``, which assigns ``yes`` for boolean
``True``, and ``no`` otherwise.

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
interface to make it return ``datetime`` objects using the desired time zone.

For your reference, in the following examples, epoch 1658167836758 is
``Mon, 18 Jul 2022 18:10:36 GMT``.

    >>> import datetime
    >>> tz_mst = datetime.timezone(datetime.timedelta(hours=7), name="MST")
    >>> cursor = connection.cursor(time_zone=tz_mst)

    >>> cursor.execute("SELECT datetime_tz FROM locations ORDER BY name")

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

    >>> cursor.time_zone = datetime.timezone.utc
    >>> cursor.execute("SELECT datetime_tz FROM locations ORDER BY name")
    >>> cursor.fetchone()
    [datetime.datetime(2022, 7, 18, 18, 10, 36, 758000, tzinfo=datetime.timezone.utc)]

    >>> import pytz
    >>> cursor.time_zone = pytz.timezone("Australia/Sydney")
    >>> cursor.execute("SELECT datetime_tz FROM locations ORDER BY name")
    >>> cursor.fetchone()
    ['foo', datetime.datetime(2022, 7, 19, 4, 10, 36, 758000, tzinfo=<DstTzInfo 'Australia/Sydney' AEST+10:00:00 STD>)]

    >>> try:
    ...     import zoneinfo
    ... except ImportError:
    ...     from backports import zoneinfo

    >>> cursor.time_zone = zoneinfo.ZoneInfo("Australia/Sydney")
    >>> cursor.execute("SELECT datetime_tz FROM locations ORDER BY name")
    >>> cursor.fetchone()
    [datetime.datetime(2022, 7, 19, 4, 10, 36, 758000, tzinfo=zoneinfo.ZoneInfo(key='Australia/Sydney'))]

    >>> cursor.time_zone = "+0530"
    >>> cursor.execute("SELECT datetime_tz FROM locations ORDER BY name")
    >>> cursor.fetchone()
    [datetime.datetime(2022, 7, 18, 23, 40, 36, 758000, tzinfo=datetime.timezone(datetime.timedelta(seconds=19800), '+0530'))]


.. _database cursor: https://en.wikipedia.org/wiki/Cursor_(databases)
.. _defines: https://legacy.python.org/dev/peps/pep-0249/#description
.. _Python Database API Specification v2.0: https://www.python.org/dev/peps/pep-0249/
.. _SQLAlchemy: https://www.sqlalchemy.org/
