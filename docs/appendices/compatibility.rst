.. _compatibility:

=============
Compatibility
=============

.. rubric:: Table of contents

.. contents::
   :local:

.. _versions:

Version notes
=============

.. _python-versions:

Python
------

Python 3.7 and the latest client library version is recommended.

However, if you are running an older version of Python, older versions of the
CrateDB Python client library can be used.

.. CAUTION::

    The documentation is written for Python 3.

    If you are using older versions of this client library with Python 2, you
    may find that you need to make adaptations to the instructions and sample
    code to get things working.

Consult the following table for compatibility notes:

+----------------+----------------+--------------------------------------------+
| Python Version | Client Version | Notes                                      |
+================+================+============================================+
| Any            | < 0.16         | Not supported:                             |
|                |                |                                            |
|                |                | - Serialisation of `date`_ and `datetime`_ |
|                |                |   objects                                  |
|                |                | - Serialisation of `Decimal`_ objects      |
+----------------+----------------+--------------------------------------------+
| 2.6.x          | >= 0.15        | Not supported.                             |
+----------------+----------------+--------------------------------------------+
| 2.7.x          | >= 0.22        | Not supported.                             |
+----------------+----------------+--------------------------------------------+
| 3.3.x          | >= 0.22        | Not supported.                             |
+----------------+----------------+--------------------------------------------+
| 3.4.x          | >= 0.22        | Supported.                                 |
+----------------+----------------+--------------------------------------------+

.. NOTE::

   If you :ref:`install <getting-started>` via `PyPI`_, a compatible library
   version is selected automatically.

   So, for instance, if you use ``pip`` with Python 2.7, version 0.21.x of the
   client library will be installed.

.. _sqlalchemy-versions:

SQLAlchemy
----------

Consult the following table for SQLAlchemy version compatibility notes:

+----------------+---------------------------+----------------+
| Client Version | SQLAlchemy |nbsp| Version | Notes          |
+================+===========================+================+
| Any            | 1.0                       | Supported.     |
+----------------+---------------------------+----------------+
| >= 0.16.5      | 1.1                       | Supported.     |
+----------------+---------------------------+----------------+
| >= 0.17        | < 1.0                     | Not supported. |
+----------------+---------------------------+----------------+

.. _cratedb-versions:

CrateDB
-------

Consult the following table for CrateDB version compatibility notes:

+----------------+-----------------+-------------------------------------------+
| Client Version | CrateDB Version | Notes                                     |
+================+=================+===========================================+
| >= 0.15        | Any             | Client SSL certificates are supported.    |
+----------------+-----------------+-------------------------------------------+
| >= 0.20        | Any             | Username authentication is supported.     |
+----------------+-----------------+-------------------------------------------+
| >= 0.21        | Any             | Password authentication is supported.     |
+----------------+-----------------+-------------------------------------------+
| >= 0.22        | Any             | Default schema selection is supported.    |
+----------------+-----------------+-------------------------------------------+
| Any            | < 0.55          | Default schema selection is not           |
|                |                 | supported.                                |
+----------------+-----------------+-------------------------------------------+
| Any            | >= 2.1.x        | Client needs to connect with a valid      |
|                |                 | database user to access CrateDB.          |
|                |                 |                                           |
|                |                 | The default CrateDB user is ``crate`` and |
|                |                 | has no password is set.                   |
|                |                 |                                           |
|                |                 | The `enterprise edition`_ of CrateDB      |
|                |                 | allows you to `create your own users`_.   |
|                |                 |                                           |
|                |                 | Prior versions of CrateDB do not support  |
|                |                 | this feature.                             |
+----------------+-----------------+-------------------------------------------+

.. _implementations:

Implementation notes
====================

.. _sqlalchemy-implementation:

SQLAlchemy
----------

.. _sqlalchemy-features:

Supported features
..................

Currently, CrateDB only implements a subset of the SQL standard. Additionally,
because CrateDB is distributed database that uses `eventual consistency`_, some
features typical of a more strongly consistent database are not available.

Because of this, some SQLAlchemy operations are not supported.

Consult the following table for specifics:

+------------+-----------------------------+-----------------------------------+
|  Category  | Methods                     | Notes                             |
+============+=============================+===================================+
| `DQL`_     | - `filter()`_               | Supported.                        |
|            | - `filter_by()`_            |                                   |
|            | - `limit()`_                |                                   |
|            | - `offset()`_               |                                   |
|            | - `group_by()`_             |                                   |
|            | - `order_by()`_             |                                   |
|            +-----------------------------+-----------------------------------+
|            | - `count()`_                | Partially supported.              |
|            |                             |                                   |
|            |                             | Consult the section on            |
|            |                             | :ref:`aggregate functions         |
|            |                             | <aggregate-functions>`.           |
|            +-----------------------------+-----------------------------------+
|            | - `join()`_, etc.           | Joins and subqueries are should   |
|            | - `subquery()`_             | be work, but tests have not been  |
|            |                             | written, so consider this an      |
|            |                             | an experimental feature for now.  |
+------------+-----------------------------+-----------------------------------+
| `DML`_     | - `insert()`_               | Supported.                        |
|            | - `from_select()`_          |                                   |
|            | - `update()`_ (including    |                                   |
|            |   `correlated updates`_)    |                                   |
|            | - `delete()`_               |                                   |
+------------+-----------------------------+-----------------------------------+
| `Session`_ | - `rollback()`_, etc.       | CrateDB does not support          |
|            |                             | transactions, so this method and  |
|            |                             | other methods that work with      |
|            |                             | transactions will not do          |
|            |                             | anything.                         |
+            +-----------------------------+-----------------------------------+
|            | - `commit()`_               | Per the previous note, this       |
|            |                             | method will only `flush()`_.      |
+------------+-----------------------------+-----------------------------------+

.. _sqlalchemy-version-notes:

Version notes
.............

+----------------+-----------------+-------------------------------------------+
| Client Version | CrateDB Version | Notes                                     |
+================+=================+===========================================+
| >= 0.17        | Any             | Supported:                                |
|                |                 |                                           |
|                |                 | - `types.ARRAY`_                          |
+----------------+-----------------+-------------------------------------------+
| >= 0.18        | Any             | Supported:                                |
|                |                 |                                           |
|                |                 | - `from_select()`_                        |
|                |                 | - `get_columns()`_                        |
|                |                 | - `get_pk_constraint()`_                  |
+----------------+-----------------+-------------------------------------------+
| >= 0.22        | >= 3.0          | Supported:                                |
|                |                 |                                           |
|                |                 | - `get_table_names()`_                    |
+----------------+-----------------+-------------------------------------------+

.. _earlier-versions:

Older versions
==============

For information about older versions of the client, consult `the 0.14.2
changelog`_.

.. _commit(): http://docs.sqlalchemy.org/en/latest/orm/session_api.html#sqlalchemy.orm.session.Session.commit
.. _correlated updates: http://docs.sqlalchemy.org/en/latest/core/tutorial.html#correlated-updates
.. _count(): http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.count
.. _create your own users: https://crate.io/docs/crate/reference/en/latest/admin/user-management.html
.. _date: https://docs.python.org/3/library/datetime.html#date-objects
.. _datetime: https://docs.python.org/3/library/datetime.html#datetime-objects
.. _Decimal: https://docs.python.org/2/library/decimal.html#module-decimal
.. _delete(): http://docs.sqlalchemy.org/en/latest/core/tutorial.html#inserts-and-updates
.. _DML: http://docs.sqlalchemy.org/en/latest/core/dml.html
.. _DQL: http://docs.sqlalchemy.org/en/latest/orm/query.html
.. _enterprise edition: https://crate.io/products/cratedb-enterprise/
.. _eventual consistency: https://crate.io/docs/crate/guide/en/latest/architecture/storage-consistency.html
.. _filter_by(): http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.filter_by
.. _filter(): http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.filter
.. _flush(): http://docs.sqlalchemy.org/en/latest/orm/session_basics.html#flushing
.. _from_select(): http://docs.sqlalchemy.org/en/latest/core/dml.html#sqlalchemy.sql.expression.Insert.from_select
.. _get_columns(): http://docs.sqlalchemy.org/en/latest/core/reflection.html#sqlalchemy.engine.reflection.Inspector.get_columns
.. _get_pk_constraint(): http://docs.sqlalchemy.org/en/latest/core/reflection.html#sqlalchemy.engine.reflection.Inspector.get_pk_constraint
.. _get_table_names(): http://docs.sqlalchemy.org/en/latest/core/reflection.html#sqlalchemy.engine.reflection.Inspector.get_table_names
.. _group_by(): http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.group_by
.. _insert(): http://docs.sqlalchemy.org/en/latest/core/tutorial.html#inserts-and-updates
.. _join(): http://docs.sqlalchemy.org/en/latest/orm/query.html?sqlalchemy.orm.query.Query.join
.. _limit(): http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.limit
.. _offset(): http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.offset
.. _order_by(): http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.order_by
.. _PyPI: https://pypi.org/
.. _rollback(): http://docs.sqlalchemy.org/en/latest/orm/session_api.html#sqlalchemy.orm.session.Session.rollback
.. _Session: http://docs.sqlalchemy.org/en/latest/orm/session_api.html
.. _subquery(): http://docs.sqlalchemy.org/en/latest/orm/query.html?sqlalchemy.orm.query.Query.subquery
.. _the 0.14.2 changelog: https://github.com/crate/crate-python/blob/415ee6d1eb3de2fe55a342e57f46841b769f1d44/CHANGES.txt
.. _types.ARRAY: http://docs.sqlalchemy.org/en/latest/core/type_basics.html#sqlalchemy.types.ARRAY
.. _update(): http://docs.sqlalchemy.org/en/latest/core/tutorial.html#inserts-and-updates
