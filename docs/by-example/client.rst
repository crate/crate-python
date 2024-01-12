===============
Database client
===============

``crate.client.connect`` is the primary method to connect to CrateDB using
Python. This section of the documentation outlines different methods to connect
to the database cluster, as well as how to run basic inquiries to the database,
and closing the connection again.

.. rubric:: Table of Contents

.. contents::
   :local:


Connect to a database
=====================

Before we can start we have to import the client:

    >>> from crate import client

The client provides a ``connect()`` function which is used to establish a
connection, the first argument is the url of the server to connect to:

    >>> connection = client.connect(crate_host)
    >>> connection.close()

CrateDB is a clustered database providing high availability through
replication. In order for clients to make use of this property it is
recommended to specify all hosts of the cluster. This way if a server does not
respond, the request is automatically routed to the next server:

    >>> invalid_host = 'http://not_responding_host:4200'
    >>> connection = client.connect([invalid_host, crate_host])
    >>> connection.close()

If no ``servers`` are given, the default one ``http://127.0.0.1:4200`` is used:

    >>> connection = client.connect()
    >>> connection.client._active_servers
    ['http://127.0.0.1:4200']
    >>> connection.close()

If the option ``error_trace`` is set to ``True``, the client will print a whole
traceback if a server error occurs:

    >>> connection = client.connect([crate_host], error_trace=True)
    >>> connection.close()

Network Timeouts
----------------

It's possible to define a default timeout value in seconds for all servers
using the optional parameter ``timeout``. In this case, it will serve as a
total timeout (connect and read):

    >>> connection = client.connect([crate_host, invalid_host], timeout=5)
    >>> connection.close()

If you want to adjust the connect- vs. read-timeout values individually,
please use the ``urllib3.Timeout`` object like:

    >>> import urllib3
    >>> connection = client.connect(
    ...     [crate_host, invalid_host],
    ...     timeout=urllib3.Timeout(connect=5, read=None))
    >>> connection.close()

Authentication
--------------

Users that are trusted as by definition of the ``auth.host_based.config``
setting do not need a password, but only require the ``username`` argument to
connect:

    >>> connection = client.connect([crate_host],
    ...                             username='trusted_me')
    >>> connection.client.username
    'trusted_me'
    >>> connection.client.password
    >>> connection.close()

The username for trusted users can also be provided in the URL:

    >>> connection = client.connect(['http://trusted_me@' + crate_host])
    >>> connection.client.username
    'trusted_me'
    >>> connection.client.password
    >>> connection.close()

To connect to CrateDB with as a user that requires password authentication, you
also need to provide ``password`` as argument for the ``connect()`` call:

    >>> connection = client.connect([crate_host],
    ...                             username='me',
    ...                             password='my_secret_pw')
    >>> connection.client.username
    'me'
    >>> connection.client.password
    'my_secret_pw'
    >>> connection.close()

The authentication credentials can also be provided in the URL:

    >>> connection = client.connect(['http://me:my_secret_pw@' + crate_host])
    >>> connection.client.username
    'me'
    >>> connection.client.password
    'my_secret_pw'
    >>> connection.close()


Default Schema
--------------

To connect to CrateDB and use a different default schema than ``doc``, you can
provide the ``schema`` keyword argument in the ``connect()`` method, like so:

    >>> connection = client.connect([crate_host],
    ...                             schema='custom_schema')
    >>> connection.close()

Inserting Data
==============

Use user "crate" for rest of the tests:

    >>> connection = client.connect([crate_host])

Before executing any statement, a cursor has to be opened to perform
database operations:

    >>> cursor = connection.cursor()
    >>> cursor.execute("""INSERT INTO locations
    ... (name, date, kind, position) VALUES (?, ?, ?, ?)""",
    ...                ('Einstein Cross', '2007-03-11', 'Quasar', 7))

To bulk insert data you can use the ``executemany`` function:

    >>> cursor.executemany("""INSERT INTO locations
    ... (name, date, kind, position) VALUES (?, ?, ?, ?)""",
    ...                [('Cloverleaf', '2007-03-11', 'Quasar', 7),
    ...                 ('Old Faithful', '2007-03-11', 'Quasar', 7)])
    [{'rowcount': 1}, {'rowcount': 1}]

``executemany`` returns a list of results for every parameter. Each result
contains a rowcount. If an error occurs, the rowcount is ``-2`` and the result
may contain an ``error_message`` depending on the error.

Refresh locations:

    >>> cursor.execute("REFRESH TABLE locations")

Updating Data
=============

Values for ``TIMESTAMP`` columns can be obtained as a string literal, ``date``,
or ``datetime`` object. If it contains timezone information, it is converted to
UTC, and the timezone information is discarded.

    >>> import datetime as dt
    >>> timestamp_full = "2023-06-26T09:24:00.123+02:00"
    >>> timestamp_date = "2023-06-26"
    >>> datetime_aware = dt.datetime.fromisoformat("2023-06-26T09:24:00.123+02:00")
    >>> datetime_naive = dt.datetime.fromisoformat("2023-06-26T09:24:00.123")
    >>> datetime_date = dt.date.fromisoformat("2023-06-26")
    >>> cursor.execute("UPDATE locations SET date=? WHERE name='Cloverleaf'", (timestamp_full, ))
    >>> cursor.execute("UPDATE locations SET date=? WHERE name='Cloverleaf'", (timestamp_date, ))
    >>> cursor.execute("UPDATE locations SET date=? WHERE name='Cloverleaf'", (datetime_aware, ))
    >>> cursor.execute("UPDATE locations SET date=? WHERE name='Cloverleaf'", (datetime_naive, ))
    >>> cursor.execute("UPDATE locations SET date=? WHERE name='Cloverleaf'", (datetime_date, ))

Selecting Data
==============

To perform the select operation simply execute the statement on the
open cursor:

    >>> cursor.execute("SELECT name FROM locations where name = ?", ('Algol',))

To retrieve a row we can use one of the cursor's fetch functions (described below).

fetchone()
----------

``fetchone()`` with each call returns the next row from the results:

    >>> result = cursor.fetchone()
    >>> pprint(result)
    ['Algol']

If no more data is available, an empty result is returned:

    >>> while cursor.fetchone():
    ...     pass
    >>> cursor.fetchone()

fetchmany()
-----------

``fetch_many()`` returns a list of all remaining rows, containing no more than
the specified size of rows:

    >>> cursor.execute("SELECT name FROM locations order by name")
    >>> result = cursor.fetchmany(2)
    >>> pprint(result)
    [['Aldebaran'], ['Algol']]

If a size is not given, the cursor's arraysize, which defaults to '1',
determines the number of rows to be fetched:

    >>> cursor.fetchmany()
    [['Allosimanius Syneca']]

It's also possible to change the cursors arraysize to an other value:

    >>> cursor.arraysize = 3
    >>> cursor.fetchmany()
    [['Alpha Centauri'], ['Altair'], ['Argabuthon']]

fetchall()
----------

``fetchall()`` returns a list of all remaining rows:

    >>> cursor.execute("SELECT name FROM locations order by name")
    >>> result = cursor.fetchall()
    >>> pprint(result)
    [['Aldebaran'],
     ['Algol'],
     ['Allosimanius Syneca'],
     ['Alpha Centauri'],
     ['Altair'],
     ['Argabuthon'],
     ['Arkintoofle Minor'],
     ['Bartledan'],
     ['Cloverleaf'],
     ['Einstein Cross'],
     ['Folfanga'],
     ['Galactic Sector QQ7 Active J Gamma'],
     ['Galaxy'],
     ['North West Ripple'],
     ['Old Faithful'],
     ['Outer Eastern Rim']]

Cursor Description
==================

The ``description`` property of the cursor returns a sequence of 7-item
sequences containing the column name as first parameter. Just the name field is
supported, all other fields are 'None':

    >>> cursor.execute("SELECT * FROM locations order by name")
    >>> result = cursor.fetchone()
    >>> pprint(result)
    ['Aldebaran',
     1658167836758,
     1658167836758,
     1658167836758,
     None,
     None,
     'Star System',
     None,
     1,
     'Max Quordlepleen claims that the only thing left after the end of the '
     'Universe will be the sweets trolley and a fine selection of Aldebaran '
     'liqueurs.',
     None]

    >>> result = cursor.description
    >>> pprint(result)
    (('name', None, None, None, None, None, None),
     ('date', None, None, None, None, None, None),
     ('datetime_tz', None, None, None, None, None, None),
     ('datetime_notz', None, None, None, None, None, None),
     ('nullable_datetime', None, None, None, None, None, None),
     ('nullable_date', None, None, None, None, None, None),
     ('kind', None, None, None, None, None, None),
     ('flag', None, None, None, None, None, None),
     ('position', None, None, None, None, None, None),
     ('description', None, None, None, None, None, None),
     ('details', None, None, None, None, None, None))

Closing the Cursor
==================

The following command closes the cursor:

    >>> cursor.close()

If a cursor is closed, it will be unusable from this point forward.

If any operation is attempted to a closed cursor an ``ProgrammingError`` will
be raised.

    >>> cursor.execute("SELECT * FROM locations")
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Cursor closed

Closing the Connection
======================

The following command closes the connection:

    >>> connection.close()

If a connection is closed, it will be unusable from this point forward. If any
operation using the connection is attempted to a closed connection an
``ProgrammingError`` will be raised:

    >>> cursor.execute("SELECT * FROM locations")
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Connection closed

    >>> cursor = connection.cursor()
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Connection closed
