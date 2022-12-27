.. _index:

=====================
CrateDB Python Client
=====================

A Python client library for `CrateDB`_.

This client library implements the `Python Database API Specification v2.0`_
(PEP 249), which defines a common interface for accessing databases in Python.

It also includes the :ref:`CrateDB dialect <using-sqlalchemy>` for `SQLAlchemy`_.

.. NOTE::

    This is a basic CrateDB driver reference.

    Check out the `sample application`_ (and the corresponding `documentation`_)
    for a practical demonstration of this driver in use.

    For general help using the Python Database API or SQLAlchemy, please consult
    `PEP 249`_, the `SQLAlchemy tutorial`_, or the `SQLAlchemy documentation`_.

.. SEEALSO::

   The CrateDB Python client library is an open source project and is `hosted
   on GitHub`_.

.. rubric:: Table of contents

.. toctree::
   :maxdepth: 2

   getting-started
   connect
   query
   blobs
   sqlalchemy
   by-example/index
   appendices/index

.. _CrateDB: https://crate.io/products/cratedb/
.. _documentation: https://github.com/crate/crate-sample-apps/blob/master/python/documentation.md
.. _hosted on GitHub: https://github.com/crate/crate-python
.. _PEP 249: https://www.python.org/dev/peps/pep-0249/
.. _Python Database API Specification v2.0: https://www.python.org/dev/peps/pep-0249/
.. _sample application: https://github.com/crate/crate-sample-apps/tree/master/python
.. _SQLAlchemy: https://www.sqlalchemy.org/
.. _SQLAlchemy documentation: https://docs.sqlalchemy.org/
.. _SQLAlchemy tutorial: https://docs.sqlalchemy.org/en/latest/orm/tutorial.html
