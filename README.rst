=====================
CrateDB Python Client
=====================

.. image:: https://github.com/crate/crate-python/workflows/Tests/badge.svg
    :target: https://github.com/crate/crate-python/actions?workflow=Tests
    :alt: Build status

.. image:: https://codecov.io/gh/crate/crate-python/branch/master/graph/badge.svg
    :target: https://app.codecov.io/gh/crate/crate-python
    :alt: Coverage

.. image:: https://readthedocs.org/projects/crate-python/badge/
    :target: https://crate.io/docs/python/
    :alt: Build status (documentation)

.. image:: https://img.shields.io/pypi/v/crate.svg
    :target: https://pypi.org/project/crate/
    :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/crate.svg
    :target: https://pypi.org/project/crate/
    :alt: Python Version

.. image:: https://img.shields.io/pypi/dw/crate.svg
    :target: https://pypi.org/project/crate/
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

A Python client library for CrateDB_.

This library:

- Implements the Python `DB API 2.0`_ specification.
- Includes support for SQLAlchemy_ in form of an `SQLAlchemy dialect`_.


Installation
============

The CrateDB Python client is available as package `crate`_ on `PyPI`_.

To install the most recent driver version, including the SQLAlchemy dialect
extension, run::

    $ pip install "crate[sqlalchemy]" --upgrade


Documentation and help
======================

- `CrateDB Python Client documentation`_
- `CrateDB reference documentation`_
- `Developer documentation`_
- `Contributing`_
- Other `support channels`_


Contributing
============

The CrateDB Python client library is an open source project, and is `managed on
GitHub`_. We appreciate contributions of any kind.


.. _Contributing: CONTRIBUTING.rst
.. _crate: https://pypi.org/project/crate/
.. _Crate.io: https://crate.io/
.. _CrateDB: https://github.com/crate/crate
.. _CrateDB Python Client documentation: https://crate.io/docs/python/
.. _CrateDB reference documentation: https://crate.io/docs/reference/
.. _DB API 2.0: https://peps.python.org/pep-0249/
.. _Developer documentation: DEVELOP.rst
.. _managed on GitHub: https://github.com/crate/crate-python
.. _PyPI: https://pypi.org/
.. _SQLAlchemy: https://www.sqlalchemy.org
.. _SQLAlchemy dialect: https://docs.sqlalchemy.org/dialects/
.. _StackOverflow: https://stackoverflow.com/tags/cratedb
.. _support channels: https://crate.io/support/
