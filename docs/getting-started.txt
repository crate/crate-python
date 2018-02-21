===============
Getting Started
===============

This page shows you how to get started with the :ref:`Python client library for
CrateDB <index>`.

Prerequisites
=============

Recent versions of this library require Python 3 (>= 3.4) to run.

Use version 0.21.x if you are running Python 2.7/3.3 or version 0.14.x if you
are running Python 2.6.

Install
=======

The CrateDB Python client is available as a `pip`_ package.

To install, run:

.. code-block:: sh

   sh$ pip install crate

To update, run:

.. code-block:: sh

   sh$ pip install -U crate

If you use Python 2.7 or 3.3 with a recent version of pip, it will install only
version 0.21.x by default, because newer versions of this package are not
compatible with Python 2.7/3.3 any more.

Connect to CrateDB
==================

Import the client module from the ``crate`` package:

.. code-block:: python

   from crate import client

Use the ``client`` module to create a connection:

.. code-block:: python

   connection = client.connect(SERVER_IP)

Open a cursor to the database to enable queries.

.. code-block:: python

   cursor = connection.cursor()

Learning More
=============

Crate.io maintains a `sample Python application`_ that uses this library, which
may be a good starting point as you learn to use it for the first time. And be
sure to check out out the `application documentation`_.

Browse the rest of the Python client :ref:`reference documentation <index>` for
more information.

.. _sample Python application: https://github.com/crate/crate-sample-apps/tree/master/python
.. _application documentation: https://github.com/crate/crate-sample-apps/blob/master/python/documentation.md
.. _pip: https://pypi.python.org/pypi/pip
