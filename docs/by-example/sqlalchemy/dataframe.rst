.. _sqlalchemy-pandas:
.. _sqlalchemy-dataframe:

================================
SQLAlchemy: DataFrame operations
================================

About
=====

This section of the documentation demonstrates support for efficient batch/bulk
``INSERT`` operations with `pandas`_ and `Dask`_, using the CrateDB SQLAlchemy dialect.

Efficient bulk operations are needed for typical `ETL`_ batch processing and
data streaming workloads, for example to move data in- and out of OLAP data
warehouses, as contrasted to interactive online transaction processing (OLTP)
applications. The strategies of `batching`_ together series of records for
improving performance are also referred to as `chunking`_.


Introduction
============

The :ref:`pandas DataFrame <pandas:api.dataframe>` is a structure that contains
two-dimensional data and its corresponding labels. DataFrames are widely used
in data science, machine learning, scientific computing, and many other
data-intensive fields.

DataFrames are similar to SQL tables or the spreadsheets that you work with in
Excel or Calc. In many cases, DataFrames are faster, easier to use, and more
powerful than tables or spreadsheets because they are an integral part of the
`Python`_ and `NumPy`_ ecosystems.

The :ref:`pandas I/O subsystem <pandas:api.io>` for `relational databases`_
using `SQL`_ is based on `SQLAlchemy`_.


.. rubric:: Table of Contents

.. contents::
   :local:


Efficient ``INSERT`` operations with pandas
===========================================

The package provides a ``bulk_insert`` function to use the
:meth:`pandas:pandas.DataFrame.to_sql` method more efficiently, based on the
`CrateDB bulk operations`_ endpoint. It will effectively split your insert
workload across multiple batches, using a defined chunk size.

    >>> import sqlalchemy as sa
    >>> from pandas._testing import makeTimeDataFrame
    >>> from crate.client.sqlalchemy.support import insert_bulk
    ...
    >>> # Define number of records, and chunk size.
    >>> INSERT_RECORDS = 42
    >>> CHUNK_SIZE = 8
    ...
    >>> # Create a pandas DataFrame, and connect to CrateDB.
    >>> df = makeTimeDataFrame(nper=INSERT_RECORDS, freq="S")
    >>> engine = sa.create_engine(f"crate://{crate_host}")
    ...
    >>> # Insert content of DataFrame using batches of records.
    >>> # Effectively, it's six. 42 / 8 = 5.25.
    >>> df.to_sql(
    ...     name="test-testdrive",
    ...     con=engine,
    ...     if_exists="replace",
    ...     index=False,
    ...     chunksize=CHUNK_SIZE,
    ...     method=insert_bulk,
    ... )

.. TIP::

    You will observe that the optimal chunk size highly depends on the shape of
    your data, specifically the width of each record, i.e. the number of columns
    and their individual sizes. You will need to determine a good chunk size by
    running corresponding experiments on your own behalf. For that purpose, you
    can use the `insert_pandas.py`_ program as a blueprint.

    A few details should be taken into consideration when determining the optimal
    chunk size for a specific dataset. We are outlining the two major ones.

    - First, when working with data larger than the main memory available on your
      machine, each chunk should be small enough to fit into the memory, but large
      enough to minimize the overhead of a single data insert operation. Depending
      on whether you are running other workloads on the same machine, you should
      also account for the total share of heap memory you will assign to each domain,
      to prevent overloading the system as a whole.

    - Second, as each batch is submitted using HTTP, you should know about the request
      size limits and other constraints of your HTTP infrastructure, which may include
      any types of HTTP intermediaries relaying information between your database client
      application and your CrateDB cluster. For example, HTTP proxy servers or load
      balancers not optimally configured for performance, or web application firewalls
      and intrusion prevention systems may hamper HTTP communication, sometimes in
      subtle ways, for example based on request size constraints, or throttling
      mechanisms. If you are working with very busy systems, and hosting it on shared
      infrastructure, details like `SNAT port exhaustion`_ may also come into play.

    You will need to determine a good chunk size by running corresponding experiments
    on your own behalf. For that purpose, you can use the `insert_pandas.py`_ program
    as a blueprint.

    It is a good idea to start your explorations with a chunk size of 5_000, and
    then see if performance improves when you increase or decrease that figure.
    Chunk sizes of 20000 may also be applicable, but make sure to take the limits
    of your HTTP infrastructure into consideration.

    In order to learn more about what wide- vs. long-form (tidy, stacked, narrow)
    data means in the context of `DataFrame computing`_, let us refer you to `a
    general introduction <wide-narrow-general_>`_, the corresponding section in
    the `Data Computing book <wide-narrow-data-computing_>`_, and a `pandas
    tutorial <wide-narrow-pandas-tutorial_>`_ about the same topic.


.. hidden: Disconnect from database

    >>> engine.dispose()


.. _batching: https://en.wikipedia.org/wiki/Batch_processing#Common_batch_processing_usage
.. _chunking: https://en.wikipedia.org/wiki/Chunking_(computing)
.. _CrateDB bulk operations: https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#bulk-operations
.. _DataFrame computing: https://realpython.com/pandas-dataframe/
.. _insert_pandas.py: https://github.com/crate/crate-python/blob/master/examples/insert_pandas.py
.. _NumPy: https://en.wikipedia.org/wiki/NumPy
.. _pandas: https://en.wikipedia.org/wiki/Pandas_(software)
.. _pandas DataFrame: https://pandas.pydata.org/pandas-docs/stable/reference/frame.html
.. _Python: https://en.wikipedia.org/wiki/Python_(programming_language)
.. _relational databases: https://en.wikipedia.org/wiki/Relational_database
.. _SQL: https://en.wikipedia.org/wiki/SQL
.. _SQLAlchemy: https://aosabook.org/en/v2/sqlalchemy.html
.. _wide-narrow-general: https://en.wikipedia.org/wiki/Wide_and_narrow_data
.. _wide-narrow-data-computing: https://dtkaplan.github.io/DataComputingEbook/chap-wide-vs-narrow.html#chap:wide-vs-narrow
.. _wide-narrow-pandas-tutorial: https://anvil.works/blog/tidy-data
