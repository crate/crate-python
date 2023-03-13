.. _other-options:

#####################################
Other connectivity options for Python
#####################################


************
Introduction
************

Using the :ref:`crate-reference:interface-postgresql` interface of `CrateDB`_,
there are a few other connectivity options for Python. This section enumerates
the verified drivers, together with some example and test case code using them.


*******
Details
*******

- `asyncpg`_, see `testing CrateDB with asyncpg`_.

- `psycopg2`_

  The `CrateDB Astronomer/Airflow tutorials`_ repository includes a few
  orchestration examples implemented using `Apache Airflow`_ DAGs for different
  import and export tasks, and for automating recurrent queries. It accompanies
  a series of articles starting with `CrateDB and Apache Airflow » Automating
  Data Export to S3`_.

- `psycopg3`_, see `testing CrateDB with psycopg3`_.

- ODBC connectivity is offered by `pyodbc`_ and `turbodbc`_, see
  `testing CrateDB with pyodbc`_ and `using CrateDB with turbodbc`_.

- `connector-x`_ promises to be the fastest library to load data from DB to
  DataFrames in Rust and Python. It is the designated database connector
  library for `Apache Arrow DataFusion`_.


.. _asyncpg: https://github.com/MagicStack/asyncpg
.. _Apache Airflow: https://github.com/apache/airflow
.. _Apache Arrow DataFusion: https://github.com/apache/arrow-datafusion
.. _connector-x: https://github.com/sfu-db/connector-x
.. _CrateDB: https://github.com/crate/crate
.. _CrateDB Astronomer/Airflow tutorials: https://github.com/crate/crate-airflow-tutorial
.. _CrateDB and Apache Airflow » Automating Data Export to S3: https://community.crate.io/t/cratedb-and-apache-airflow-automating-data-export-to-s3/901
.. _pyodbc: https://github.com/mkleehammer/pyodbc
.. _psycopg2: https://github.com/psycopg/psycopg2
.. _psycopg3: https://github.com/psycopg/psycopg
.. _Testing CrateDB with asyncpg: https://github.com/crate/crate-qa/blob/master/tests/client_tests/python/asyncpg/test_asyncpg.py
.. _Testing CrateDB with psycopg3: https://github.com/crate/crate-qa/blob/master/tests/client_tests/python/psycopg3/test_psycopg3.py
.. _Testing CrateDB with pyodbc: https://github.com/crate/crate-qa/blob/master/tests/client_tests/odbc/test_pyodbc.py
.. _turbodbc: https://github.com/blue-yonder/turbodbc
.. _Using CrateDB with turbodbc: https://github.com/crate/cratedb-examples/pull/18
