=====================
The Connection object
=====================

This documentation section outlines different attributes, methods, and
behaviors of the ``crate.client.connection.Connection`` object.

The examples use an instance of ``ClientMocked`` instead of a real ``Client``
instance. This allows us to verify the examples without needing a real database
connection.

.. rubric:: Table of Contents

.. contents::
   :local:


connect()
=========

This section sets up a connection object, and inspects some of its attributes.

    >>> from crate.client import connect
    >>> from crate.testing.util import ClientMocked

    >>> connection = connect(client=ClientMocked())
    >>> connection.lowest_server_version.version
    (2, 0, 0)

cursor()
========

Calling the ``cursor()`` function on the connection will
return a cursor object:

    >>> cursor = connection.cursor()

Now we are able to perform any operation provided by the
cursor object:

    >>> cursor.rowcount
    -1

close()
=======

Now we close the connection:

    >>> connection.close()

The connection will be unusable from this point. Any
operation attempted with the closed connection will
raise a ``ProgrammingError``:

    >>> cursor = connection.cursor()
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Connection closed

    >>> cursor.execute('')
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Connection closed

    >>> connection.commit()
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Connection closed
