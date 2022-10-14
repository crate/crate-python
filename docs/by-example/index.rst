##########
By example
##########


*****
About
*****

This part of the documentation contains examples how to use the CrateDB Python
client, exercising different options and scenarios.


DBAPI, HTTP, and BLOB interfaces
================================

The examples in this section are all about CrateDB's `Python DBAPI`_ interface,
the plain HTTP API interface, and a convenience interface for working with
`blob tables`_. It also details attributes, methods, and behaviors of the
``Connection`` and ``Cursor`` objects.

.. toctree::
    :maxdepth: 1

    client
    http
    https
    blob
    connection
    cursor


.. _sqlalchemy-by-example:

SQLAlchemy interface
====================

The examples in this section are all about CrateDB's `SQLAlchemy`_ dialect, and
its corresponding API interfaces, see also :ref:`sqlalchemy-support`.

.. toctree::
    :maxdepth: 1

    sqlalchemy/getting-started
    sqlalchemy/cru
    sqlalchemy/inspection-reflection


.. _blob tables: https://crate.io/docs/crate/reference/en/latest/general/blobs.html
.. _Python DBAPI: https://peps.python.org/pep-0249/
.. _SQLAlchemy: https://www.sqlalchemy.org/
