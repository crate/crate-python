.. _sqlalchemy-pandas:
.. _sqlalchemy-dataframe:

================================
SQLAlchemy: DataFrame operations
================================

.. rubric:: Table of Contents

.. contents::
   :local:


About
=====

This section of the documentation demonstrates support for efficient batch/bulk
``INSERT`` operations with `pandas`_ and `Dask`_, using the CrateDB SQLAlchemy dialect.

Efficient bulk operations are needed for typical `ETL`_ batch processing and
data streaming workloads, for example to move data in and out of OLAP data
warehouses, as contrasted to interactive online transaction processing (OLTP)
applications. The strategies of `batching`_ together series of records for
improving performance are also referred to as `chunking`_.


Introduction
============

pandas
------
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

Dask
----
`Dask`_ is a flexible library for parallel computing in Python, which scales
Python code from multi-core local machines to large distributed clusters in
the cloud. Dask provides a familiar user interface by mirroring the APIs of
other libraries in the PyData ecosystem, including `pandas`_, `scikit-learn`_,
and `NumPy`_.

A :doc:`dask:dataframe` is a large parallel DataFrame composed of many smaller
pandas DataFrames, split along the index. These pandas DataFrames may live on
disk for larger-than-memory computing on a single machine, or on many different
machines in a cluster. One Dask DataFrame operation triggers many operations on
the constituent pandas DataFrames.


Compatibility notes
===================

.. NOTE::

    Please note that DataFrame support for pandas and Dask is only validated
    with Python 3.8 and higher, and SQLAlchemy 1.4 and higher. We recommend
    to use the most recent versions of those libraries.


Efficient ``INSERT`` operations with pandas
===========================================

The package provides a ``bulk_insert`` function to use the
:meth:`pandas:pandas.DataFrame.to_sql` method more efficiently, based on the
`CrateDB bulk operations`_ endpoint. It will effectively split your insert
workload across multiple batches, using a defined chunk size.

    >>> import sqlalchemy as sa
    >>> from crate.client.sqlalchemy.support import insert_bulk
    >>> from pueblo.testing.pandas import makeTimeDataFrame
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
    and their individual sizes, which will in the end determine the total size of
    each batch/chunk.

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
    People are reporting that 10_000-20_000 is their optimal setting, but if you
    process, for example, just three "small" columns, you may also experiment with
    `leveling up to 200_000`_, because `the chunksize should not be too small`_.
    If it is too small, the I/O cost will be too high to overcome the benefit of
    batching.

    In order to learn more about what wide- vs. long-form (tidy, stacked, narrow)
    data means in the context of `DataFrame computing`_, let us refer you to `a
    general introduction <wide-narrow-general_>`_, the corresponding section in
    the `Data Computing book <wide-narrow-data-computing_>`_, and a `pandas
    tutorial <wide-narrow-pandas-tutorial_>`_ about the same topic.


Efficient ``INSERT`` operations with Dask
=========================================

The same ``bulk_insert`` function presented in the previous section will also
be used in the context of `Dask`_, in order to make the
:func:`dask:dask.dataframe.to_sql` method more efficiently, based on the
`CrateDB bulk operations`_ endpoint.

The example below will partition your insert workload into equal-sized parts, and
schedule it to be executed on Dask cluster resources, using a defined number of
compute partitions. Each worker instance will then insert its partition's records
in a batched/chunked manner, using a defined chunk size, effectively using the
pandas implementation introduced in the previous section.

    >>> import dask.dataframe as dd
    >>> from crate.client.sqlalchemy.support import insert_bulk
    >>> from pueblo.testing.pandas import makeTimeDataFrame
    ...
    >>> # Define the number of records, the number of computing partitions,
    >>> # and the chunk size of each database insert operation.
    >>> INSERT_RECORDS = 100
    >>> NPARTITIONS = 4
    >>> CHUNK_SIZE = 25
    ...
    >>> # Create a Dask DataFrame.
    >>> df = makeTimeDataFrame(nper=INSERT_RECORDS, freq="S")
    >>> ddf = dd.from_pandas(df, npartitions=NPARTITIONS)
    ...
    >>> # Insert content of DataFrame using multiple workers on a
    >>> # compute cluster, transferred using batches of records.
    >>> ddf.to_sql(
    ...     name="test-testdrive",
    ...     uri=f"crate://{crate_host}",
    ...     if_exists="replace",
    ...     index=False,
    ...     chunksize=CHUNK_SIZE,
    ...     method=insert_bulk,
    ...     parallel=True,
    ... )


.. TIP::

    You will observe that optimizing your workload will now also involve determining a
    good value for the ``NPARTITIONS`` argument, based on the capacity and topology of
    the available compute resources, and based on workload characteristics or policies
    like peak- vs. balanced- vs. shared-usage. For example, on a machine or cluster fully
    dedicated to the problem at hand, you may want to use all available processor cores,
    while on a shared system, this strategy may not be appropriate.

    If you want to dedicate all available compute resources on your machine, you may want
    to use the number of CPU cores as a value to the ``NPARTITIONS`` argument. You can find
    out about the available CPU cores on your machine, for example by running the ``nproc``
    command in your terminal.

    Depending on the implementation and runtime behavior of the compute task, the optimal
    number of worker processes, determined by the ``NPARTITIONS`` argument, also needs to be
    figured out by running a few test iterations. For that purpose, you can use the
    `insert_dask.py`_ program as a blueprint.

    Adjusting this value in both directions is perfectly fine: If you observe that you are
    overloading the machine, maybe because there are workloads scheduled other than the one
    you are running, try to reduce the value. If fragments/steps of your implementation
    involve waiting for network or disk I/O, you may want to increase the number of workers
    beyond the number of available CPU cores, to increase utilization. On the other hand,
    you should be wary about not over-committing resources too much, as it may slow your
    system down.

    Before getting more serious with Dask, you are welcome to read and watch the excellent
    :doc:`dask:best-practices` and :ref:`dask:dataframe.performance` resources, in order to
    learn about things to avoid, and beyond. For finding out if your compute workload
    scheduling is healthy, you can, for example, use Dask's :doc:`dask:dashboard`.

.. WARNING::

    Because the settings assigned in the example above fit together well, the ``to_sql()``
    instruction will effectively run four insert operations, executed in parallel, and
    scheduled optimally on the available cluster resources.

    However, not using those settings sensibly, you can easily misconfigure the resource
    scheduling system, and overload the underlying hardware or operating system, virtualized
    or not. This is why experimenting with different parameters, and a real dataset, is crucial.



.. hidden: Disconnect from database

    >>> engine.dispose()


.. _batching: https://en.wikipedia.org/wiki/Batch_processing#Common_batch_processing_usage
.. _chunking: https://en.wikipedia.org/wiki/Chunking_(computing)
.. _CrateDB bulk operations: https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#bulk-operations
.. _Dask: https://en.wikipedia.org/wiki/Dask_(software)
.. _DataFrame computing: https://realpython.com/pandas-dataframe/
.. _ETL: https://en.wikipedia.org/wiki/Extract,_transform,_load
.. _insert_dask.py: https://github.com/crate/cratedb-examples/blob/main/by-language/python-sqlalchemy/insert_dask.py
.. _insert_pandas.py: https://github.com/crate/cratedb-examples/blob/main/by-language/python-sqlalchemy/insert_pandas.py
.. _leveling up to 200_000: https://acepor.github.io/2017/08/03/using-chunksize/
.. _NumPy: https://en.wikipedia.org/wiki/NumPy
.. _pandas: https://en.wikipedia.org/wiki/Pandas_(software)
.. _pandas DataFrame: https://pandas.pydata.org/pandas-docs/stable/reference/frame.html
.. _Python: https://en.wikipedia.org/wiki/Python_(programming_language)
.. _relational databases: https://en.wikipedia.org/wiki/Relational_database
.. _scikit-learn: https://en.wikipedia.org/wiki/Scikit-learn
.. _SNAT port exhaustion: https://learn.microsoft.com/en-us/azure/load-balancer/troubleshoot-outbound-connection
.. _SQL: https://en.wikipedia.org/wiki/SQL
.. _SQLAlchemy: https://aosabook.org/en/v2/sqlalchemy.html
.. _the chunksize should not be too small: https://acepor.github.io/2017/08/03/using-chunksize/
.. _wide-narrow-general: https://en.wikipedia.org/wiki/Wide_and_narrow_data
.. _wide-narrow-data-computing: https://dtkaplan.github.io/DataComputingEbook/chap-wide-vs-narrow.html#chap:wide-vs-narrow
.. _wide-narrow-pandas-tutorial: https://anvil.works/blog/tidy-data
