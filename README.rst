=====================
CrateDB Python Client
=====================

.. image:: https://github.com/crate/crate-python/workflows/Tests/badge.svg
    :target: https://github.com/crate/crate-python/actions?workflow=Tests
    :alt: Build status

.. image:: https://codecov.io/gh/crate/crate-python/branch/main/graph/badge.svg
    :target: https://app.codecov.io/gh/crate/crate-python
    :alt: Coverage

.. image:: https://readthedocs.org/projects/crate-python/badge/
    :target: https://cratedb.com/docs/python/
    :alt: Build status (documentation)

.. image:: https://img.shields.io/pypi/v/crate.svg
    :target: https://pypi.org/project/crate/
    :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/crate.svg
    :target: https://pypi.org/project/crate/
    :alt: Python Version

.. image:: https://static.pepy.tech/badge/crate/month
    :target: https://pepy.tech/project/crate
    :alt: PyPI Downloads

.. image:: https://img.shields.io/pypi/wheel/crate.svg
    :target: https://pypi.org/project/crate/
    :alt: Wheel

.. image:: https://img.shields.io/pypi/status/crate.svg
    :target: https://pypi.org/project/crate/
    :alt: Status

.. image:: https://img.shields.io/pypi/l/crate.svg
    :target: https://pypi.org/project/crate/
    :alt: License


|

A Python client library for `CrateDB`_, implementing the Python `DB API 2.0`_
specification.

The CrateDB dialect for `SQLAlchemy`_ is provided by the `sqlalchemy-cratedb`_
package, see also `sqlalchemy-cratedb documentation`_.


Installation
============

The CrateDB Python client is available as package `crate`_ on `PyPI`_.

To install the most recent driver version, run::

    $ pip install --upgrade crate


Migration Notes
===============

If you are migrating from previous versions of ``crate[sqlalchemy]<1.0.0``, you
will find that the newer releases ``crate>=1.0.0`` no longer include the
SQLAlchemy dialect for CrateDB.

See `migrate to sqlalchemy-cratedb`_ for relevant guidelines about how to
successfully migrate to the `sqlalchemy-cratedb`_ package.


Documentation and Help
======================

- `CrateDB Python Client documentation`_
- `CrateDB reference documentation`_
- `Developer documentation`_
- `Contributing`_
- Other `support channels`_


Contributions
=============

The CrateDB Python client library is an open source project, and is `managed on
GitHub`_. We appreciate contributions of any kind.


.. _Contributing: CONTRIBUTING.rst
.. _crate: https://pypi.org/project/crate/
.. _Crate.io: https://cratedb.com/
.. _CrateDB: https://github.com/crate/crate
.. _CrateDB Python Client documentation: https://cratedb.com/docs/python/
.. _CrateDB reference documentation: https://crate.io/docs/reference/
.. _DB API 2.0: https://peps.python.org/pep-0249/
.. _Developer documentation: DEVELOP.rst
.. _managed on GitHub: https://github.com/crate/crate-python
.. _migrate to sqlalchemy-cratedb: https://cratedb.com/docs/sqlalchemy-cratedb/migrate-from-crate-client.html
.. _PyPI: https://pypi.org/
.. _SQLAlchemy: https://www.sqlalchemy.org/
.. _sqlalchemy-cratedb: https://github.com/crate/sqlalchemy-cratedb
.. _sqlalchemy-cratedb documentation: https://cratedb.com/docs/sqlalchemy-cratedb/
.. _StackOverflow: https://stackoverflow.com/tags/cratedb
.. _support channels: https://cratedb.com/support/
