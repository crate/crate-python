.. _index:

#####################
CrateDB Python Client
#####################

.. rubric:: Table of contents

.. contents::
    :local:
    :depth: 1


************
Introduction
************

The Python client library for `CrateDB`_ implements the Python Database API
Specification v2.0 (`PEP 249`_).

The Python driver can be used to connect to both `CrateDB`_ and `CrateDB
Cloud`_, and is verified to work on Linux, macOS, and Windows. It is used by
the `Crash CLI`_, as well as other libraries and applications connecting to
CrateDB from the Python ecosystem. It is verified to work with CPython, but
it has also been tested successfully with `PyPy`_.

Please make sure to also visit the section about :ref:`other-options`, using
the :ref:`crate-reference:interface-postgresql` interface of `CrateDB`_.


*************
Documentation
*************

For general help about the Python Database API, please consult `PEP 249`_.
For more detailed information about how to install the client driver, how to
connect to a CrateDB cluster, and how to run queries, consult the resources
referenced below.

.. toctree::
    :titlesonly:

    getting-started
    connect
    query
    blobs


DB API
======

Install package from PyPI.

.. code-block:: shell

    pip install crate

Connect to CrateDB instance running on ``localhost``.

.. code-block:: python

    # Connect using DB API.
    from crate import client
    from pprint import pp

    query = "SELECT country, mountain, coordinates, height FROM sys.summits ORDER BY country;"
    
    with client.connect("localhost:4200", username="crate") as connection:
        cursor = connection.cursor()
        cursor.execute(query)
        pp(cursor.fetchall())
        cursor.close()

Connect to `CrateDB Cloud`_.

.. code-block:: python

    # Connect using DB API.
    from crate import client
    connection = client.connect(
        servers="https://example.aks1.westeurope.azure.cratedb.net:4200",
        username="admin",
        password="<PASSWORD>")


Data types
==========

The DB API driver supports :ref:`CrateDB's data types
<crate-reference:data-types>` to different degrees. For more information,
please consult the :ref:`data-types` documentation page.

.. toctree::
    :maxdepth: 2

    data-types


Migration Notes
===============

The :ref:`CrateDB dialect <using-sqlalchemy>` for `SQLAlchemy`_ is provided
by the `sqlalchemy-cratedb`_ package.

If you are migrating from previous versions of ``crate[sqlalchemy]<1.0.0``, you
will find that the newer releases ``crate>=1.0.0`` no longer include the
SQLAlchemy dialect for CrateDB.

See `migrate to sqlalchemy-cratedb`_ for relevant guidelines about how to
successfully migrate to the `sqlalchemy-cratedb`_ package.


Examples
========

- The :ref:`by-example` section enumerates concise examples demonstrating the
  different API interfaces of the CrateDB Python client library. Those are
  DB API, HTTP, and BLOB interfaces.

- Executable code examples are maintained within the `cratedb-examples repository`_.
  `sqlalchemy-cratedb`_, `python-dataframe-examples`_, and `python-sqlalchemy-examples`_
  provide relevant code snippets about how to connect to CrateDB using
  `SQLAlchemy`_, `pandas`_, or `Dask`_, and how to load and export data.

- The `sample application`_ and the corresponding `sample application
  documentation`_ demonstrate the use of the driver on behalf of an example
  "guestbook" application, using Flask.


.. toctree::
    :maxdepth: 2

    by-example/index


*******************
Project information
*******************

Resources
=========
- `Source code <https://github.com/crate/crate-python>`_
- `Documentation <https://crate.io/docs/python/>`_
- `Python Package Index (PyPI) <https://pypi.org/project/crate/>`_

Contributions
=============
The CrateDB Python client library is an open source project, and is `managed on
GitHub`_.
Every kind of contribution, feedback, or patch, is much welcome. `Create an
issue`_ or submit a patch if you think we should include a new feature, or to
report or fix a bug.

Development
===========
In order to setup a development environment on your workstation, please head
over to the `development sandbox`_ documentation. When you see the software
tests succeed, you should be ready to start hacking.

Page index
==========
The full index for all documentation pages can be inspected at :ref:`index-all`.

License
=======
The project is licensed under the terms of the Apache 2.0 license, like
`CrateDB itself <CrateDB source_>`_, see `LICENSE`_.


.. _Apache Superset: https://github.com/apache/superset
.. _Crash CLI: https://crate.io/docs/crate/crash/
.. _CrateDB: https://crate.io/products/cratedb
.. _CrateDB Cloud: https://console.cratedb.cloud/
.. _CrateDB source: https://github.com/crate/crate
.. _Create an issue: https://github.com/crate/crate-python/issues
.. _Dask: https://en.wikipedia.org/wiki/Dask_(software)
.. _development sandbox: https://github.com/crate/crate-python/blob/main/DEVELOP.rst
.. _cratedb-examples repository: https://github.com/crate/cratedb-examples
.. _FIWARE QuantumLeap data historian: https://github.com/orchestracities/ngsi-timeseries-api
.. _GeoJSON: https://geojson.org/
.. _GeoJSON geometry objects: https://tools.ietf.org/html/rfc7946#section-3.1
.. _LICENSE: https://github.com/crate/crate-python/blob/main/LICENSE
.. _managed on GitHub: https://github.com/crate/crate-python
.. _migrate to sqlalchemy-cratedb: https://cratedb.com/docs/sqlalchemy-cratedb/migrate-from-crate-client.html
.. _pandas: https://en.wikipedia.org/wiki/Pandas_(software)
.. _PEP 249: https://peps.python.org/pep-0249/
.. _PyPy: https://www.pypy.org/
.. _python-dataframe-examples: https://github.com/crate/cratedb-examples/tree/main/by-dataframe
.. _python-sqlalchemy-examples: https://github.com/crate/cratedb-examples/tree/main/by-language/python-sqlalchemy
.. _sample application: https://github.com/crate/crate-sample-apps/tree/main/python-flask
.. _sample application documentation: https://github.com/crate/crate-sample-apps/blob/main/python-flask/documentation.md
.. _SQLAlchemy: https://en.wikipedia.org/wiki/Sqlalchemy
.. _sqlalchemy-cratedb: https://github.com/crate/sqlalchemy-cratedb
.. _Use CrateDB with pandas: https://github.com/crate/crate-qa/pull/246
