=================
Changes for crate
=================

Unreleased
==========

2025/01/30 2.0.0
================

- Switched JSON encoder to use the `orjson`_ library, to improve JSON
  marshalling performance. Thanks, @widmogrod.

  orjson is fast and in some spots even more correct when compared against
  Python's stdlib ``json`` module. Contrary to the stdlib variant, orjson
  will serialize to ``bytes`` instead of ``str``. When sending data to CrateDB,
  ``crate-python`` uses a custom encoder to add support for additional data
  types.

  - Python's ``Decimal`` type will be serialized to ``str``.
  - Python's ``dt.datetime`` and ``dt.date`` types will be serialized to
    ``int`` (``LONG``) after converting to milliseconds since epoch, to
    optimally accommodate CrateDB's `TIMESTAMP`_ representation.
  - NumPy's data types will be handled by ``orjson`` without any ado.

.. _orjson: https://github.com/ijl/orjson
.. _TIMESTAMP: https://cratedb.com/docs/crate/reference/en/latest/general/ddl/data-types.html#type-timestamp

2024/11/23 1.0.1
================

- Python: Fixed "implicit namespace packages" migration by omitting
  ``__init__.py`` from ``crate`` namespace package, see `PEP 420`_
  and `Package Discovery and Namespace Package » Finding namespace packages`_.


2024/11/05 1.0.0
================

- BREAKING CHANGE: The SQLAlchemy dialect has been split off into
  the `sqlalchemy-cratedb`_ package, see notice below.
- Feature: Returned Python ``datetime`` objects are now always timezone-aware,
  using UTC by default.
  It may be a breaking change for some users of the library that don't expect
  to receive "aware" instead of "naive" Python ``datetime`` objects from now
  on, i.e. instances with or without the ``tzinfo`` attribute set.
  When no ``time_zone`` information is specified when creating a database
  connection or cursor, ``datetime`` objects will now use Coordinated
  Universal Time (UTC), like CrateDB is storing timestamp values in this
  format.
  This update is coming from a deprecation of Python's
  ``datetime.utcfromtimestamp()``, which is effectively also phasing out
  the use of "naive" timestamp objects in Python, in favor of using
  timezone-aware objects, also to represent datetimes in UTC.
- Feature: Configured DB API interface attribute ``threadsafety = 1``,
  which signals "Threads may share the module, but not connections."
- Feature: Added ``error_trace`` to string representation of an Error,
  to relay server stacktraces into exception messages.
- Refactoring: The module namespace ``crate.client.test_util`` has been
  renamed to ``crate.testing.util``.
- Error handling: At two spots in cursor / value converter handling, where
  ``assert`` statements have been used, ``ValueError`` exceptions are raised
  now.
- Python: Migrated to use "implicit namespace packages" instead of "declared
  namespaces" for the ``crate`` namespace package, see `PEP 420`_.


.. note::

    For learning about the transition to `sqlalchemy-cratedb`_,
    we recommend to read the enumeration of necessary migration steps
    at `Migrate from crate.client to sqlalchemy-cratedb`_.


.. _Migrate from crate.client to sqlalchemy-cratedb: https://cratedb.com/docs/sqlalchemy-cratedb/migrate-from-crate-client.html
.. _Package Discovery and Namespace Package » Finding namespace packages: https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#namespace-packages
.. _PEP 420: https://peps.python.org/pep-0420/
.. _sqlalchemy-cratedb: https://pypi.org/project/sqlalchemy-cratedb/


2024/01/18 0.35.2
=================

- Test compatibility: Permit installation of pandas 2.1.


2024/01/18 0.35.1
=================

- Compatibility: Re-add ``crate.client._pep440.Version`` from ``verlib2``.
  It is needed the prevent breaking ``crash``.


2024/01/17 0.35.0
=================

- Permit ``urllib3.Timeout`` instances for defining timeout values.
  This way, both ``connect`` and ``read`` socket timeout settings can be
  configured. The unit is seconds.


2023/09/29 0.34.0
=================

- Properly handle Python-native UUID types in SQL parameters. Thanks,
  @SStorm.
- SQLAlchemy: Fix handling URL parameters ``timeout`` and ``pool_size``
- Permit installation with urllib3 v2, see also `urllib3 v2.0 roadmap`_
  and `urllib3 v2.0 migration guide`_. You can optionally retain support
  for TLS 1.0 and TLS 1.1, but a few other outdated use-cases of X.509
  certificate details are immanent, like no longer accepting the long
  deprecated ``commonName`` attribute. Instead, going forward, only the
  ``subjectAltName`` attribute will be used.
- SQLAlchemy: Improve DDL compiler to ignore foreign key and uniqueness
  constraints.
- DBAPI: Properly raise ``IntegrityError`` exceptions instead of
  ``ProgrammingError``, when CrateDB raises a ``DuplicateKeyException``.
- SQLAlchemy: Ignore SQL's ``FOR UPDATE`` clause. Thanks, @surister.

.. _urllib3 v2.0 migration guide: https://urllib3.readthedocs.io/en/latest/v2-migration-guide.html
.. _urllib3 v2.0 roadmap: https://urllib3.readthedocs.io/en/stable/v2-roadmap.html


2023/07/17 0.33.0
=================

- SQLAlchemy: Rename leftover occurrences of ``Object``. The new symbol to represent
  CrateDB's ``OBJECT`` column type is now ``ObjectType``.

- SQLAlchemy DQL: Use CrateDB's native ``ILIKE`` operator instead of using SA's
  generic implementation ``lower() LIKE lower()``. Thanks, @hlcianfagna.


2023/07/06 0.32.0
=================

- SQLAlchemy DDL: Allow turning off column store using ``crate_columnstore=False``.
  Thanks, @fetzerms.

- SQLAlchemy DDL: Allow setting ``server_default`` on columns to enable
  server-generated defaults. Thanks, @JanLikar.

- Allow handling datetime values tagged with time zone info when inserting or updating.

- SQLAlchemy: Fix SQL statement caching for CrateDB's ``OBJECT`` type. Thanks, @faymarie.

- SQLAlchemy: Refactor ``OBJECT`` type to use SQLAlchemy's JSON type infrastructure.

- SQLAlchemy: Added ``insert_bulk`` fast-path ``INSERT`` method for pandas, in
  order to support efficient batch inserts using CrateDB's "bulk operations" endpoint.

- SQLAlchemy: Add documentation and software tests for usage with Dask


2023/04/18 0.31.1
=================

- SQLAlchemy Core: Re-enable support for ``INSERT/UPDATE...RETURNING`` in
  SQLAlchemy 2.0 by adding the new ``insert_returning`` and ``update_returning`` flags
  in the CrateDB dialect.


2023/03/30 0.31.0
=================

- SQLAlchemy Core: Support ``INSERT...VALUES`` with multiple value sets by enabling
  ``supports_multivalues_insert`` on the CrateDB dialect, it is used by pandas'
  ``method="multi"`` option

- SQLAlchemy Core: Enable the ``insertmanyvalues`` feature, which lets you control
  the batch size of ``INSERT`` operations using the ``insertmanyvalues_page_size``
  engine-, connection-, and statement-options.

- SQLAlchemy ORM: Remove support for the legacy ``session.bulk_save_objects`` API
  on SQLAlchemy 2.0, in favor of the new ``insertmanyvalues`` feature. Performance
  optimizations from ``bulk_save()`` have been made inherently part of ``add_all()``.
  Note: The legacy mode will still work on SQLAlchemy 1.x, while SQLAlchemy 2.x users
  MUST switch to the new method now.


2023/03/02 0.30.1
=================

- Fixed SQLAlchemy 2.0 incompatibility with ``CrateDialect.{has_schema,has_table}``


2023/02/16 0.30.0
=================

- Added deprecation warning about dropping support for SQLAlchemy 1.3 soon, it
  is effectively EOL.

- Added support for SQLAlchemy 2.0. See also `What's New in SQLAlchemy 2.0`_
  and `SQLAlchemy 2.0 migration guide`_.

- Updated to geojson 3.0.0.

.. _SQLAlchemy 2.0 migration guide: https://docs.sqlalchemy.org/en/20/changelog/migration_20.html
.. _What's New in SQLAlchemy 2.0: https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html


2022/12/08 0.29.0
=================

- SQLAlchemy: Added support for ``crate_index`` and ``nullable`` attributes in
  ORM column definitions.

- Added support for converting ``TIMESTAMP`` columns to timezone-aware
  ``datetime`` objects, using the new ``time_zone`` keyword argument.


2022/12/02 0.28.0
=================

- Added a generic data type converter to the ``Cursor`` object, for converting
  fetched data from CrateDB data types to Python data types.

- Fixed generating appropriate syntax for OFFSET/LIMIT clauses. It was possible
  that SQL statement clauses like ``LIMIT -1`` could have been generated. Both
  PostgreSQL and CrateDB only accept ``LIMIT ALL`` instead.

- Added support for computed columns in the SQLAlchemy ORM

2022/10/10 0.27.2
=================

- Improved SQLAlchemy's ``CrateDialect.get_pk_constraint`` to be compatible
  with breaking changes in CrateDB >=5.1.0.


2022/07/04 0.27.1
=================

- Fixed regression introduced by ``0.27.0`` resulting in unavailable servers if
  all configured servers aren't reachable once.


2022/06/02 0.27.0
=================

- Added support for Python 3.9 and 3.10.

- Dropped support for Python 3.4, 3.5 and 3.6.

- Dropped support for SQLAlchemy 1.1 and 1.2.

- Dropped support for CrateDB < 2.0.0.

- BREAKING CHANGE: The driver now verifies SSL certificates when connecting via
  HTTP by default. Previously, this setting defaulted to false. This setting
  can be changed via the ``verify_ssl_cert`` connection parameter.

- Adjusted connect arguments to accept credentials within the HTTP URI.

- Added support for enabling SSL using SQLAlchemy DB URI with parameter
  ``?ssl=true``.

- Added support for SQLAlchemy 1.4

.. note::

    For learning about the transition to SQLAlchemy 1.4, we recommend the
    corresponding documentation `What’s New in SQLAlchemy 1.4?`_.



Breaking changes
----------------

Textual column expressions
''''''''''''''''''''''''''

SQLAlchemy 1.4 became stricter on some details. It requires to wrap `CrateDB
system columns`_ like ``_score`` in a `SQLAlchemy literal_column`_ type.
Before, it was possible to use a query like this::

    session.query(Character.name, '_score')

It must now be written like::

    session.query(Character.name, sa.literal_column('_score'))

Otherwise, SQLAlchemy will complain like::

    sqlalchemy.exc.ArgumentError: Textual column expression '_score' should be
    explicitly declared with text('_score'), or use column('_score') for more
    specificity


.. _CrateDB system columns: https://crate.io/docs/crate/reference/en/4.8/general/ddl/system-columns.html
.. _SQLAlchemy literal_column: https://docs.sqlalchemy.org/en/14/core/sqlelement.html#sqlalchemy.sql.expression.literal_column
.. _What’s New in SQLAlchemy 1.4?: https://docs.sqlalchemy.org/en/14/changelog/migration_14.html


2020/09/28 0.26.0
=================

- Enabled TCP keepalive on socket level and support for setting socket options
  when creating the connection. The supported options are:

  - ``TCP_KEEPIDLE`` (overriding ``net.ipv4.tcp_keepalive_time``)
  - ``TCP_KEEPINTVL`` (overriding ``net.ipv4.tcp_keepalive_intvl``)
  - ``TCP_KEEPCNT`` (overriding ``net.ipv4.tcp_keepalive_probes``)

- Propagate connect parameter ``pool_size`` to urllib3 as ``maxsize`` parameter
  in order to make the connection pool size configurable.

2020/08/05 0.25.0
=================

- Added support for the ``RETURNING`` clause to the SQLAlchemy dialect. This
  requires CrateDB 4.2 or greater. In case you use any server side generated
  columns in your primary key constraint with earlier CrateDB versions, you can
  turn this feature off by passing ``implicit_returning=False`` in the
  ``create_engine()`` call.

- Added support for ``geo_point`` and ``geo_json`` types to the SQLAlchemy
  dialect.

2020/05/27 0.24.0
=================

- Upgraded SQLAlchemy support to 1.3.

- Added ``backoff_factor`` in connection to configure retry interval.

- Added official Python 3.8 support.

- Made it so that the SQLAlchemy dialect is now aware of the return type of the
  ``date_trunc`` function.

- Added driver attribute, as SQLAlchemy relies on interfaces having that string for identification.

2019/09/19 0.23.2
=================

- Fixed a bug in the ``CrateLayer`` which caused ``CrateDB`` not to start up,
  in case the ``JAVA_HOME`` environment variable was not set.

2019/08/01 0.23.1
=================

- Extended the type mapping for SQLAlchemy for the upcoming type name changes
  in CrateDB 4.0.

- Added support for Python 3.7 and made that version the recommended one.

2019/03/05 0.23.0
=================

- Fixed a resource leak in ``CrateLayer``

- Added ability to specify chunk size when getting a blob from the blob container

2018/08/08 0.22.1
=================

- Client no longer removes servers from the active server list when encountering a
  connection reset or a broken pipe error.

2018/05/02 0.22.0
=================

- BREAKING: Dropped support for Python 2.7 and 3.3
  If you are using this package with Python 2.7 or 3.3 already, you will not be
  able to install newer versions of this package.

- Add support for SQLAlchemy 1.2

- The client now allows to define a different default schema when connecting to
  CrateDB with the ``schema`` keyword argument. This causes all statements and
  queries that do not specify a schema explicitly to use the provided schema.

- Updated ``get_table_names()`` method in SQLAlchemy dialect to only return
  tables but not views. This enables compatibility with CrateDB 3.0 and newer.

2018/03/14 0.21.3
=================

- Fixed an issue that caused ``metadata.create_all(bind=engine)`` to fail
  creating tables that contain an ``ObjectArray`` column.

2018/02/15 0.21.2
=================

- BREAKING: In the testing layer, the custom setting of
  `cluster.routing.allocation.disk.watermark.low` (1b) and
  `cluster.routing.allocation.disk.watermark.high` (1b) has been removed.
  These now default to 85% and 90%, respectively.

2018/01/03 0.21.1
=================

- Fixed an issue that prevented the usage of SQLAlchemy types ``NUMERIC`` and
  ``DECIMAL`` as column types.

2017/12/07 0.21.0
=================

- Added new parameter ``password`` used to authenticate the user in CrateDB.

- Prepared SQL Alchemy primary key retrieval for CrateDB 2.3.0. Preserved
  backwards-compatibility for lower versions.

2017/08/18 0.20.1
=================

- Fixed deprecation warnings logged in CrateDB server on every REST request.

2017/06/26 0.20.0
=================

- Added new parameter ``username`` used to authenticate the user in CrateDB.

2017/06/23 0.19.5
=================

- Enforced cert check when verify_ssl_cert=True

2017/06/20 0.19.4
=================

- Testing: Fixed issue that caused the test layer to hang after it failed to
  start a CrateDB instance in time.

2017/05/18 0.19.3
=================

- Fix bulk updates which were broken due to query rewrites.


2017/04/28 0.19.2
=================

- Output logs in test-layer in case when CrateDB instance does not start in
  time.

- Increased the default timeout for the test-layer startup to avoid timeouts
  on slow hosts.

2017/02/27 0.19.1
=================

- Testing: Prevent the process.stdout buffer from filling up in the test layer
  which in turn would cause the process to block

- Raise more meaningful `BlobLocationNotFoundException` error when
  trying to upload a file to an invalid blob table.


2017/02/17 0.19.0
=================

- Testing: Added support for setting environment variables.

2017/02/02 0.18.0
=================

- BREAKING: Dropped Crate version < 1.0.0 support for Crate test layer

  - Testing: Dropped ``multicast`` support for Crate test layer

  - Added support for ``Insert`` from select to the SQLAlchemy dialect

  - sqlalchemy: support `get_columns` and `get_pk_constraint`

2016/12/19 0.17.0
=================

- BREAKING: Dropped support for SQLAlchemy < 1.0.0

- Fix sqlalchemy: crate dialect didn't work properly with alpha and beta
  versions of sqlalchemy due to a wrong version check
  (e.g.: sandman2 depends on 1.1.0b3)

- sqlalchemy: added support for native Arrays

- Fix sqlalchemy: ``sa.inspect(engine).get_table_names`` failed due
  to an attribute error

2016/11/21 0.16.5
=================

- Added compatibility for SQLAlchemy version 1.1

2016/10/18 0.16.4
=================

- Fix sqlalchemy: updates in nested object columns have been ignored

2016/08/16 0.16.3
=================

- Fix: Avoid invalid keyword argument error when fetching blobs from cluster
  by removing certificate keywords before creating non-https server in pool.

- Testing: Made Crate test layer logging less verbose (hide Crate startup logs)
  and added ``verbose keyword`` argument to layer to control its verbosity.

2016/07/22 0.16.2
=================

- Increased ``urllib3`` version requirement to >=1.9 to prevent from
  compatibility issues.

- Testing: Do not rely on startup log if static http port is defined in test
  layer.

2016/06/23 0.16.1
=================

- Fix: ``Date`` column type is now correctly created as ``TIMESTAMP`` column
  when creating the table

2016/06/09 0.16.0
=================

- Added a ``from_uri`` factory method to the ``CrateLayer``

- The ``Connection`` class now supports the context management protocol and
  can therefore be used with the ``with`` statement.

- Sockets are now properly closed if a connection is closed.

- Added support for serialization of Decimals

2016/05/17 0.15.0
=================

- Added support for client certificates

- Dropped support for Python 2.6

2016/03/18 0.14.2
=================

- Fix: Never retry on http read errors (so never send SQL statements twice)

2016/03/10 0.14.1
=================

- test-layer: Removed options that are going to be removed from Crate

2016/02/05 0.14.0
=================

- Added support for serialization of date and datetime objects

2015/10/21 0.13.6
=================

- fix in crate test layer: wait for layer to completely start up node

2015/10/12 0.13.5
=================

- fix: use proper CLUSTERED clause syntax in SQLAlchemy's create table statement

2015/08/12 0.13.4
=================

- Fix urllib3 error with invalid kwargs for ``HTTPConnectionPool``
  when ``REQUESTS_CA_BUNDLE`` is set

2015/06/29 0.13.3
=================

- Fix: allow ObjectArrays to be set to None

2015/06/15 0.13.2
=================

- wait until master of test cluster is elected before starting tests

2015/05/29 0.13.1
=================

- fixed compatibility issues with SQLAlchemy 1.0.x

- map SQLAlchemy's text column type to Crate's ``STRING`` type

2015/03/10 0.13.0
=================

- add support for table creation using the SQLAlchemy ORM functionality.

- fix: match predicate now properly handles term literal

2015/02/13 0.12.5
=================

- changed SQLAlchemy update statement generation to be compatible with crate
  0.47.X

2015/02/04 0.12.4
=================

- added missing functionality in CrateDialect, containing:
  default schema name, server version info,
  check if table/schema exists, list all tables/schemas

- updated crate to version 0.46.1

2014/10/27 0.12.3
=================

- support iterator protocol on cursor

2014/10/20 0.12.2
=================

- added match predicate in sqlalchemy to support fulltext
  search

2014/10/02 0.12.1
=================

- send application/json Accept header when requesting crate

2014/09/11 0.12.0
=================

- add new options to CrateLayer in order to build test clusters

2014/09/19 0.11.2
=================

- improved server failover

2014/08/26 0.11.1
=================

- more reliable failover mechanism

2014/08/26 0.11.0
=================

- improved server failover / retry behaviour

- use bulk_args in executemany to increase performance:
   With crate server >= 0.42.0 executemany uses bulk_args
   and returns a list of results.
   With crate server < 0.42.0 executemany still issues
   a request for every parameter and doesn't return
   any results.

- improved docs formatting of field lists

2014/07/25 0.10.7
=================

- fix: ``cursor.executemany()`` now correctly sets the cursor description

2014/07/18 0.10.6
=================

- fix: correctly attach server error trace to crate client exceptions

2014/07/16 0.10.5
=================

- fix: only send ``error_trace`` when it is explicitly set

2014/07/16 0.10.4
=================

- expose the ``error_trace`` option to give a full traceback of server exceptions

2014/07/14 0.10.3
=================

- fix: Columns that have an onupdate definition are now correctly updated

2014/06/03 0.10.2
=================

- fix: return -1 for rowcount if rowcount attribute is missing in crate
  response

2014/05/21 0.10.1
=================

- fixed redirect handling for blob downloads and uploads.

2014/05/16 0.10.0
=================

- implemented ANY operator on object array containment checks
  for SQLAlchemy

- updated crate to 0.37.1

2014/05/13 0.9.5
================

- bugfix: updates of complex types will only be rewritten if the dialect is
  set to 'crate' in SQLAlchemy.

2014/05/09 0.9.4
================

- bugfix: raise correct error if fetching infos is not possible because server
  is not fully started

2014/05/09 0.9.3
================

- bugfix: old versions of `six` caused import errors

- updated crate doc theme config

2014/05/07 0.9.2
================

- fixed python3.3 compatibility issue in sphinx script

2014/05/07 0.9.1
================

- use new crate doc theme

2014/04/01 0.9.0
================

- replaced requests with urllib3 to improve performance

- add ``verify_ssl_cert`` and ``ca_cert`` as kwargs to ``Connection``,
  ``connect`` and as SQLAlchemy ``connect_args``

2014/04/04 0.8.1
================

- client: fix error handling in ``client.server_infos()``

2014/03/21 0.8.0
================

- updated crate to 0.32.3

- client: adding keyword arguments ``verify_ssl_cert`` and ``ca_cert``
          to enable ssl server certificate validation

- client: disable ssl server certificate validation by default

2014/03/14 0.7.1
================

- updated crate to 0.31.0

- client: fixed error handling on wrong content-type and bad status codes (on connect)

2014/03/13 0.7.0
================

- removed the crate shell ``crash`` from this package. it will live
  now under the name ``crate-shell`` on pypi.

2014/03/12 0.6.0
================

- updated crate to 0.30.0

- crash: added support for ``ALTER`` statements.

- crash: added support for ``REFRESH`` statements.

- crash: added support for multi-statements for stdin and ``--command`` parameter

- crash: renamed cli parameter ``--statement/-s`` to ``--command/-c``

2014/03/12 0.5.0
================

- updated crate to 0.29.0. This release contains backward incompatible changes
  related to blob support.

- updated crash autocompletion keywords

2014/03/11 0.4.0
================

- fix a bug where setting an empty list on a multi valued field results in returning ``None``
  after refreshing the session.

- the test layer now uses the '/' crate endpoint in order to wait for crate to
  be available.

- updated crate to 0.28.0. This release contains backward incompatible changes.

- changed the test layer to no longer use the `-f`
  option. Note that this breaks the test layer for all previous crate
  versions.

2014/03/05 0.3.4
================

- fix readline bug in windows bundle

2014/03/05 0.3.3
================

- readline support for windows

- updated crate to 0.26.0

2014/03/04 0.3.2
================

- added single-file crash bundle ``crash.zip.py``

2014/02/27 0.3.1
================

- minor documentation syntax fix

2014/01/27 0.3.0
================

- added the `ObjectArray` type to the sqlalchemy dialect.

- renamed `Craty` type to `Object`.
  `Craty` can still be imported to maintain backward compatibility

2014/01/15 0.2.0
================

- adapted for compatibility with SQLAlchemy >= 0.9.x

- changed default port to 4200

2013/12/17 0.1.10
=================

- allow to specify https urls in client and crash cli

2013/12/06 0.1.9
================

- sqlalchemy dialect supports native booleans

2013/12/02 0.1.8
================

- Fix: Date columns return date objects

2013/11/25 0.1.7
================

- Added ``duration`` property to the cursor displaying the server-side duration.
  Show this value at the `crash` crate cli now instead of client-side duration.

- Added `readline` as a requirement package on OS X (Darwin), fixes umlauts problem.

- Fix sqlalchemy: raise exception if timezone aware datetime is saved

- Fix: raise concrete exception while uploading blobs to an index with disabled blobs support

- crash: check if given servers are available
  and retrieve some basic information on connect command

2013/11/13 0.1.6
================

- Fix: show rows affected at `crash` on ``copy`` command

- crash: Added persistent history stored in platform dependent app-dir

- crash: Added support for multiple hosts for ``crash --hosts ...`` and the connect cmd

2013/11/11 0.1.5
================

- Added SQL ``copy`` command support to `crash` crate cli

2013/11/11 0.1.4
================

- crate layer: set working directory on layer instantiation instead of start hook

2013/11/08 0.1.3
================

- fixed sqlalchemy datetime parsing that didn't work with crate >= 0.18.4 due
  to the fixed datetime mapping.

2013/11/08 0.1.2
================

- documented SQLAlchemy count() and group_by() support.

2013/11/07 0.1.1
================

- http keepalive support

- uppercase command support for crash

- fixed python3.3 compatibility issue in crash

2013/10/23 0.1.0
================

- the `crash` crate cli supports multiple line commands and auto-completion now,
  commands are delimited by a semi-colon.

- the `crash` crate cli displays the status and, if related, the row count on every command now.

2013/10/09 0.0.9
================

- SQLAlchemy `DateTime` and `Date` can now be nullable

2013/10/04 0.0.8
================

- fixed an error with the `Craty` type and SQLAlchemy's ORM where the `update`
  statement wasn't correctly generated.

2013/10/02 0.0.7
================

- rowcount in results of update-requests gives affected rows

- the `Date` and `DateTime` sqlalchemy types are now supported.

- make http-client thread-safe

2013/10/01 0.0.6
================

- add support for sqlalchemy including complex types

- error handling improvements in crash

2013/09/18 0.0.5
================

- added qmark parameter substitution support

- basic Blob-Client-API implemented

2013/09/16 0.0.4
================

- the `crash` crate cli is now included with the client library

- the client library is now compatible with python 3

2013/09/09 0.0.3
================

- text files are now also included in binary egg distributions

2013/09/05 0.0.2
================

- initial release
