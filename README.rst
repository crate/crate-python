=====================
CrateDB Python Client
=====================

.. image:: https://dev.azure.com/cratedb/crate-python/_apis/build/status/crate.crate-python?branchName=master
   :target: https://dev.azure.com/cratedb/crate-python/_build/latest?definitionId=2&branchName=master
   :alt: Azure Pipeline

.. image:: https://img.shields.io/pypi/v/crate.svg
   :target: https://pypi.python.org/pypi/crate/
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/crate.svg
   :target: https://pypi.python.org/pypi/crate/
   :alt: Python Version

.. image:: https://img.shields.io/pypi/dw/crate.svg
    :target: https://pypi.python.org/pypi/crate/
    :alt: PyPI Downloads

.. image:: https://img.shields.io/pypi/wheel/crate.svg
    :target: https://pypi.python.org/pypi/crate/
    :alt: Wheel

.. image:: https://coveralls.io/repos/github/crate/crate-python/badge.svg?branch=master
    :target: https://coveralls.io/github/crate/crate-python?branch=master
    :alt: Coverage

|

A Python client library for CrateDB_.

This library:

- Implements the Python `DB API 2.0`_ specification
- Includes support for SQLAlchemy_ (>= 1.0.0)

Prerequisites
=============

Recent versions of this library require **Python 3** (>= 3.4) to run.

Use version ``0.21.x`` if you are running Python 2.7/3.3 or version ``0.14.x``
if you are running Python 2.6.

Installation
============

The CrateDB Python client is available as a pip_ package.

To install, run::

    $ pip install crate

To update, run::

    $ pip install -U crate

If you use Python 2.7 or 3.3 with a recent version of pip_, it will install
only version ``0.21.x`` by default, because newer versions of this package are
not compatible with Python 2.7/3.3 any more.

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
.. _Crate.io: http://crate.io/
.. _CrateDB: https://github.com/crate/crate
.. _DB API 2.0: http://www.python.org/dev/peps/pep-0249/
.. _developer docs: DEVELOP.rst
.. _pip: https://pypi.python.org/pypi/pip
.. _SQLAlchemy: http://www.sqlalchemy.org
.. _StackOverflow: https://stackoverflow.com/tags/crate
.. _support channels: https://crate.io/support/
.. _project docs: https://crate.io/docs/reference/python/
