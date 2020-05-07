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
   in the :ref:`data types appendix <data-types-db-api>` and the
   :ref:`compatibility notes <compatibility>`.

   For general help using the Database API, consult `PEP 0249`_.

.. rubric:: Table of contents

.. contents::
   :local:

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
     ('datetime', None, None, None, None, None, None),
     ('description', None, None, None, None, None, None),
    ...
     ('nullable_datetime', None, None, None, None, None, None),
     ('position', None, None, None, None, None, None))

You can turn this into something more manageable with a `list comprehension`_::

    >>> [column[0] for column in cursor.description]
    ['date', 'datetime', 'description', ..., 'nullable_datetime', 'position']

.. _Bulk inserts: https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#bulk-operations
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
