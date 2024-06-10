.. _by-example:

##########
By example
##########

This part of the documentation enumerates different kinds of examples how to
use the CrateDB Python DBAPI HTTP client for standards-based database
conversations, and the proprietary BLOB interfaces.

The examples in this section are all about CrateDB's `Python DB API`_ interface,
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


.. _Python DB API: https://peps.python.org/pep-0249/
