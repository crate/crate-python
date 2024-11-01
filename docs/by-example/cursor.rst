=================
The Cursor object
=================

This documentation section outlines different attributes, methods, and
behaviors of the ``crate.client.cursor.Cursor`` object.

The example code uses ``ClientMocked`` and ``set_next_response`` for
demonstration purposes, so they don't need a real database connection.

.. rubric:: Table of Contents

.. contents::
   :local:


Introduction
============

This section sets up a cursor object, inspects some of its attributes, and sets
up the response for subsequent cursor operations.

    >>> from crate.client import connect
    >>> from crate.client.converter import DefaultTypeConverter
    >>> from crate.client.cursor import Cursor
    >>> from crate.testing.util import ClientMocked

    >>> connection = connect(client=ClientMocked())
    >>> cursor = connection.cursor()

The ``rowcount`` and ``duration`` attributes are ``-1``, in case no ``execute()`` has
been performed on the cursor yet.

    >>> cursor.rowcount
    -1

    >>> cursor.duration
    -1

Define the response of the mocked connection client. It will be returned on
request without needing to execute an SQL statement.

    >>> connection.client.set_next_response({
    ...     "rows":[ [ "North West Ripple", 1 ], [ "Arkintoofle Minor", 3 ], [ "Alpha Centauri", 3 ] ],
    ...     "cols":[ "name", "position" ],
    ...     "rowcount":3,
    ...     "duration":123
    ... })

fetchone()
==========

Calling ``fetchone()`` on the cursor object the first time after an execute returns the first row:

    >>> cursor.execute('')

    >>> cursor.fetchone()
    ['North West Ripple', 1]

Each call to ``fetchone()`` increments the cursor and returns the next row:

    >>> cursor.fetchone()
    ['Arkintoofle Minor', 3]

One more iteration:

    >>> cursor.next()
    ['Alpha Centauri', 3]

The iteration is stopped after the last row is returned.
A further call to ``fetchone()`` returns an empty result:

    >>> cursor.fetchone()

Using ``fetchone()`` on a cursor before issuing a database statement results
in an error:

    >>> new_cursor = connection.cursor()
    >>> new_cursor.fetchone()
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: No result available. execute() or executemany() must be called first.


fetchmany()
===========

``fetchmany()`` takes an argument which specifies the number of rows we want to fetch:

    >>> cursor.execute('')

    >>> cursor.fetchmany(2)
    [['North West Ripple', 1], ['Arkintoofle Minor', 3]]

If the specified number of rows not being available, fewer rows may returned:

    >>> cursor.fetchmany(2)
    [['Alpha Centauri', 3]]

    >>> cursor.execute('')

If no number of rows are specified it defaults to the current ``cursor.arraysize``:

    >>> cursor.arraysize
    1

    >>> cursor.fetchmany()
    [['North West Ripple', 1]]

    >>> cursor.execute('')
    >>> cursor.arraysize = 2
    >>> cursor.fetchmany()
    [['North West Ripple', 1], ['Arkintoofle Minor', 3]]

If zero number of rows are specified, all rows left are returned:

    >>> cursor.fetchmany(0)
    [['Alpha Centauri', 3]]

fetchall()
==========

``fetchall()`` fetches all (remaining) rows of a query result:

    >>> cursor.execute('')

    >>> cursor.fetchall()
    [['North West Ripple', 1], ['Arkintoofle Minor', 3], ['Alpha Centauri', 3]]

Since all data was fetched 'None' is returned by ``fetchone()``:

    >>> cursor.fetchone()

And each other call returns an empty sequence:

    >>> cursor.fetchmany(2)
    []

    >>> cursor.fetchmany()
    []

    >>> cursor.fetchall()
    []

iteration
=========

The cursor supports the iterator interface and can be iterated upon:

    >>> cursor.execute('')
    >>> [row for row in cursor]
    [['North West Ripple', 1], ['Arkintoofle Minor', 3], ['Alpha Centauri', 3]]

When no other call to execute has been done, it will raise StopIteration on
subsequent iterations:

    >>> next(cursor)
    Traceback (most recent call last):
    ...
    StopIteration

    >>> cursor.execute('')
    >>> for row in cursor:
    ...     row
    ['North West Ripple', 1]
    ['Arkintoofle Minor', 3]
    ['Alpha Centauri', 3]

Iterating over a new cursor without results will immediately raise a ProgrammingError:

    >>> new_cursor = connection.cursor()
    >>> next(new_cursor)
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: No result available. execute() or executemany() must be called first.

description
===========

    >>> cursor.description
    (('name', None, None, None, None, None, None), ('position', None, None, None, None, None, None))

rowcount
========

The ``rowcount`` property specifies the number of rows that the last ``execute()`` produced:

    >>> cursor.execute('')
    >>> cursor.rowcount
    3

The attribute is ``-1``, in case the cursor has been closed:

    >>> cursor.close()
    >>> cursor.rowcount
    -1

If the last response does not contain the rowcount attribute, ``-1`` is returned:

    >>> cursor = connection.cursor()
    >>> connection.client.set_next_response({
    ...     "rows":[],
    ...     "cols":[],
    ...     "duration":123
    ... })

    >>> cursor.execute('')
    >>> cursor.rowcount
    -1

    >>> connection.client.set_next_response({
    ...     "rows":[ [ "North West Ripple", 1 ], [ "Arkintoofle Minor", 3 ], [ "Alpha Centauri", 3 ] ],
    ...     "cols":[ "name", "position" ],
    ...     "rowcount":3,
    ...     "duration":123
    ... })

duration
========

The ``duration`` property specifies the server-side duration in milliseconds of the last query
issued by ``execute()``:

    >>> cursor = connection.cursor()
    >>> cursor.execute('')
    >>> cursor.duration
    123

The attribute is ``-1``, in case the cursor has been closed:

    >>> cursor.close()
    >>> cursor.duration
    -1

    >>> connection.client.set_next_response({
    ...     "results": [
    ...         {
    ...             "rowcount": 3
    ...         },
    ...         {
    ...             "rowcount": 2
    ...         }
    ...     ],
    ...     "duration":123,
    ...     "cols":[ "name", "position" ],
    ... })

executemany()
=============

``executemany()`` allows to execute a single sql statement against a sequence
of parameters:

    >>> cursor = connection.cursor()

    >>> cursor.executemany('', (1,2,3))
    [{'rowcount': 3}, {'rowcount': 2}]

    >>> cursor.rowcount
    5
    >>> cursor.duration
    123

``executemany()`` is not intended to be used with statements returning result
sets. The result will always be empty:

    >>> cursor.fetchall()
    []

For completeness' sake the cursor description is updated nonetheless:

    >>> [ desc[0] for desc in cursor.description ]
    ['name', 'position']

    >>> connection.client.set_next_response({
    ...     "rows":[ [ "North West Ripple", 1 ], [ "Arkintoofle Minor", 3 ], [ "Alpha Centauri", 3 ] ],
    ...     "cols":[ "name", "position" ],
    ...     "rowcount":3,
    ...     "duration":123
    ... })


close()
=======

After closing a cursor the connection will be unusable. If any operation is attempted with the
closed connection an ``ProgrammingError`` exception will be raised:

    >>> cursor = connection.cursor()
    >>> cursor.execute('')
    >>> cursor.fetchone()
    ['North West Ripple', 1]

    >>> cursor.close()
    >>> cursor.fetchone()
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Cursor closed

    >>> cursor.fetchmany()
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Cursor closed

    >>> cursor.fetchall()
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Cursor closed

    >>> cursor.next()
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Cursor closed


Python data type conversion
===========================

The cursor object can optionally convert database types to native Python data
types. Currently, this is implemented for the CrateDB data types ``IP`` and
``TIMESTAMP`` on behalf of the ``DefaultTypeConverter``.

    >>> cursor = connection.cursor(converter=DefaultTypeConverter())

    >>> connection.client.set_next_response({
    ...     "col_types": [4, 5, 11],
    ...     "rows":[ [ "foo", "10.10.10.1", 1658167836758 ] ],
    ...     "cols":[ "name", "address", "timestamp" ],
    ...     "rowcount":1,
    ...     "duration":123
    ... })

    >>> cursor.execute('')

    >>> cursor.fetchone()
    ['foo', IPv4Address('10.10.10.1'), datetime.datetime(2022, 7, 18, 18, 10, 36, 758000, tzinfo=datetime.timezone.utc)]


Custom data type conversion
===========================

By providing a custom converter instance, you can define your own data type
conversions. For investigating the list of available data types, please either
inspect the ``DataType`` enum, or the documentation about the list of available
:ref:`CrateDB data type identifiers for the HTTP interface
<crate-reference:http-column-types>`.

To create a simple converter for converging CrateDB's ``BIT`` type to Python's
``int`` type.

    >>> from crate.client.converter import Converter, DataType

    >>> converter = Converter({DataType.BIT: lambda value: int(value[2:-1], 2)})
    >>> cursor = connection.cursor(converter=converter)

Proof that the converter works correctly, ``B\'0110\'`` should be converted to
``6``. CrateDB's ``BIT`` data type has the numeric identifier ``25``.

    >>> connection.client.set_next_response({
    ...     "col_types": [25],
    ...     "rows":[ [ "B'0110'" ] ],
    ...     "cols":[ "value" ],
    ...     "rowcount":1,
    ...     "duration":123
    ... })

    >>> cursor.execute('')

    >>> cursor.fetchone()
    [6]


``TIMESTAMP`` conversion with time zone
=======================================

Based on the data type converter functionality, the driver offers a convenient
interface to make it return ``datetime`` objects using the desired time zone.

For your reference, in the following examples, epoch 1658167836758 is
``Mon, 18 Jul 2022 18:10:36 GMT``.

    >>> import datetime
    >>> tz_mst = datetime.timezone(datetime.timedelta(hours=7), name="MST")
    >>> cursor = connection.cursor(time_zone=tz_mst)

    >>> connection.client.set_next_response({
    ...     "col_types": [4, 11],
    ...     "rows":[ [ "foo", 1658167836758 ] ],
    ...     "cols":[ "name", "timestamp" ],
    ...     "rowcount":1,
    ...     "duration":123
    ... })

    >>> cursor.execute('')

    >>> cursor.fetchone()
    ['foo', datetime.datetime(2022, 7, 19, 1, 10, 36, 758000, tzinfo=datetime.timezone(datetime.timedelta(seconds=25200), 'MST'))]

For the ``time_zone`` keyword argument, different data types are supported.
The available options are:

- ``datetime.timezone.utc``
- ``datetime.timezone(datetime.timedelta(hours=7), name="MST")``
- ``pytz.timezone("Australia/Sydney")``
- ``zoneinfo.ZoneInfo("Australia/Sydney")``
- ``+0530`` (UTC offset in string format)

Let's exercise all of them:

    >>> cursor.time_zone = datetime.timezone.utc
    >>> cursor.execute('')
    >>> cursor.fetchone()
    ['foo', datetime.datetime(2022, 7, 18, 18, 10, 36, 758000, tzinfo=datetime.timezone.utc)]

    >>> import pytz
    >>> cursor.time_zone = pytz.timezone("Australia/Sydney")
    >>> cursor.execute('')
    >>> cursor.fetchone()
    ['foo', datetime.datetime(2022, 7, 19, 4, 10, 36, 758000, tzinfo=<DstTzInfo 'Australia/Sydney' AEST+10:00:00 STD>)]

    >>> try:
    ...     import zoneinfo
    ... except ImportError:
    ...     from backports import zoneinfo
    >>> cursor.time_zone = zoneinfo.ZoneInfo("Australia/Sydney")
    >>> cursor.execute('')
    >>> record = cursor.fetchone()
    >>> record
    ['foo', datetime.datetime(2022, 7, 19, 4, 10, 36, 758000, ...zoneinfo.ZoneInfo(key='Australia/Sydney'))]

    >>> record[1].tzname()
    'AEST'

    >>> cursor.time_zone = "+0530"
    >>> cursor.execute('')
    >>> cursor.fetchone()
    ['foo', datetime.datetime(2022, 7, 18, 23, 40, 36, 758000, tzinfo=datetime.timezone(datetime.timedelta(seconds=19800), '+0530'))]


.. Hidden: close connection

    >>> connection.close()
