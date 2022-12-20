##########
By example
##########


*****
About
*****

This part of the documentation contains examples how to use the CrateDB Python
client.


DBAPI, HTTP, and BLOB interfaces
================================

The examples in this section are all about CrateDB's `Python DBAPI`_ interface,
the plain HTTP API interface, and a convenience interface for working with
:ref:`blob tables <crate-reference:blob_support>`. It details attributes,
methods, and behaviors of the ``Connection`` and ``Cursor`` objects.

.. toctree::
    :maxdepth: 1

    client
    connection
    cursor
    http
    https
    blob


.. _sqlalchemy-by-example:

SQLAlchemy by example
=====================

The examples in this section are all about CrateDB's `SQLAlchemy`_ dialect, and
its corresponding API interfaces, see also :ref:`sqlalchemy-support`.

.. toctree::
    :maxdepth: 1

    sqlalchemy/getting-started
    sqlalchemy/crud
    sqlalchemy/working-with-types
    sqlalchemy/advanced-querying
    sqlalchemy/inspection-reflection


.. _Python DBAPI: https://peps.python.org/pep-0249/
.. _SQLAlchemy: https://www.sqlalchemy.org/
