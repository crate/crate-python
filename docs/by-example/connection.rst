=====================
The Connection object
=====================

This documentation section outlines different attributes, methods, and
behaviors of the ``crate.client.connection.Connection`` object.

To improve focus and reduce boilerplate, the example code uses both
``ClientMocked``. It is required for demonstration purposes, so the example
does not need a real database connection.

.. rubric:: Table of Contents

.. contents::
   :local:


connect()
=========

This section sets up a connection object, and inspects some of its attributes.

    >>> from crate.client import connect
    >>> from crate.client.test_util import ClientMocked

    >>> connection = connect(client=ClientMocked())
    >>> connection.lowest_server_version.version
    (2, 0, 0)

cursor()
========

Calling the ``cursor()`` function on the connection will
return a cursor object::

    >>> cursor = connection.cursor()

Now we are able to perform any operation provided by the
cursor object::

    >>> cursor.rowcount
    -1

close()
=======

Now we close the connection::

    >>> connection.close()

The connection will be unusable from this point. Any
operation attempted with the closed connection will
raise a ``ProgrammingError``::

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
