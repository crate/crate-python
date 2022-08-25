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

- Implements the Python `DB API 2.0`_ specification
- Includes support for SQLAlchemy_ (>= 1.3.0)

Prerequisites
=============

Recent versions of this library are validated on Python 3 (>= 3.7).
It may also work on earlier versions of Python.


Installation
============

The CrateDB Python client is available as a pip_ package.

To install the most recent driver version, including the SQLAlchemy dialect
extension, run::

    $ pip install "crate[sqlalchemy]" --upgrade


Contributing
============

This project is primarily maintained by Crate.io_, but we welcome community
contributions!

See the `developer docs`_ and the `contribution docs`_ for more information.

Help
====

Looking for more help?

- Read the `project docs`_
- Check out our `support channels`_

.. _contribution docs: CONTRIBUTING.rst
.. _Crate.io: https://crate.io/
.. _CrateDB: https://github.com/crate/crate
.. _DB API 2.0: http://www.python.org/dev/peps/pep-0249/
.. _developer docs: DEVELOP.rst
.. _pip: https://pypi.python.org/pypi/pip
.. _SQLAlchemy: https://www.sqlalchemy.org
.. _StackOverflow: https://stackoverflow.com/tags/cratedb
.. _support channels: https://crate.io/support/
.. _project docs: https://crate.io/docs/python/
