.. _sqlalchemy-advanced-querying:

=============================
SQLAlchemy: Advanced querying
=============================

This section of the documentation demonstrates running queries using a fulltext
index with an analyzer, queries using counting and aggregations, and support for
the ``INSERT...FROM SELECT`` and ``INSERT...RETURNING`` constructs, all using the
CrateDB SQLAlchemy dialect.


.. rubric:: Table of Contents

.. contents::
   :local:


Introduction
============

Import the relevant symbols:

    >>> import sqlalchemy as sa
    >>> from sqlalchemy.orm import sessionmaker
    >>> try:
    ...     from sqlalchemy.orm import declarative_base
    ... except ImportError:
    ...     from sqlalchemy.ext.declarative import declarative_base
    >>> from uuid import uuid4

Establish a connection to the database, see also :ref:`sa:engines_toplevel`
and :ref:`connect`:

    >>> engine = sa.create_engine(f"crate://{crate_host}")
    >>> connection = engine.connect()

Create an SQLAlchemy :doc:`Session <sa:orm/session_basics>`:

    >>> session = sessionmaker(bind=engine)()
    >>> Base = declarative_base()


Introduction to fulltext indexes
================================

:ref:`crate-reference:fulltext-indices` take the contents of one or more fields
and split it up into tokens that are used for fulltext-search. The
transformation from a text to separate tokens is done by an analyzer. In order
to conduct fulltext search queries, we need to create a table with a
:ref:`fulltext index with an analyzer <crate-reference:sql_ddl_index_fulltext>`.

.. code-block:: sql

    CREATE TABLE characters (
        id STRING PRIMARY KEY,
        name STRING,
        quote STRING,
        INDEX name_ft USING fulltext(name) WITH (analyzer = 'english'),
        INDEX quote_ft USING fulltext(quote) WITH (analyzer = 'english')
    )

We have to create this table using SQL because it is currently not possible to
create ``INDEX`` fields using SQLAlchemy's :ref:`sa:orm_declarative_mapping`.
However, we can define the table to use all other operations:

    >>> def gen_key():
    ...     return str(uuid4())

    >>> class Character(Base):
    ...     __tablename__ = 'characters'
    ...     id = sa.Column(sa.String, primary_key=True, default=gen_key)
    ...     name = sa.Column(sa.String)
    ...     quote = sa.Column(sa.String)
    ...     name_ft = sa.Column(sa.String)
    ...     quote_ft = sa.Column(sa.String)
    ...     __mapper_args__ = {
    ...         'exclude_properties': ['name_ft', 'quote_ft']
    ...     }

We define ``name_ft`` and ``quote_ft`` as regular columns, but add them under
``__mapper_args__.exclude_properties`` to ensure they're excluded from insert
or update operations.

In order to support fulltext query operations, the CrateDB SQLAlchemy dialect
provides the :ref:`crate-reference:predicates_match` through its ``match``
function.

Let's add two records we use for testing.

    >>> arthur = Character(name='Arthur Dent')
    >>> arthur.quote = "Let's go somewhere."
    >>> session.add(arthur)

    >>> trillian = Character(name='Tricia McMillan')
    >>> trillian.quote = "We're on a space ship Arthur. In space."
    >>> session.add(trillian)

    >>> session.commit()

After ``INSERT`` statements are submitted to the database, the newly inserted
records aren't immediately available for retrieval, because the index is only
updated periodically (default: each second). In order to synchronize that,
explicitly refresh the table:

    >>> _ = connection.execute(sa.text("REFRESH TABLE characters"))


Fulltext search with MATCH predicate
====================================

Fulltext search in CrateDB is performed using :ref:`crate-reference:predicates_match`.
The CrateDB SQLAlchemy dialect comes with a ``match`` function, which can be used to
search on one or multiple fields.

    >>> from crate.client.sqlalchemy.predicates import match

    >>> session.query(Character.name) \
    ...     .filter(match(Character.name_ft, 'Arthur')) \
    ...     .all()
    [('Arthur Dent',)]

To get the relevance of a matching row, you can select the ``_score`` system
column. It is a numeric value which is relative to the other rows.
The higher the score value, the more relevant the row.

In most cases, ``_score`` is not part of the SQLAlchemy table definition,
so it must be passed as a verbatim string, using ``literal_column``:

    >>> session.query(Character.name, sa.literal_column('_score')) \
    ...     .filter(match(Character.quote_ft, 'space')) \
    ...     .all()
    [('Tricia McMillan', ...)]

To search multiple columns, use a dictionary where the keys are the columns and
the values are a ``boost``. A ``boost`` is a factor that increases the relevance
of a column in respect to the other columns:

    >>> session.query(Character.name) \
    ...           .filter(match({Character.name_ft: 1.5, Character.quote_ft: 0.1},
    ...                         'Arthur')) \
    ...     .order_by(sa.desc(sa.literal_column('_score'))) \
    ...     .all()
    [('Arthur Dent',), ('Tricia McMillan',)]

The ``match_type`` argument determines how a single ``query_term`` is applied,
and how the resulting ``_score`` is computed. Thus, it influences which
documents are considered more relevant. The default selection is ``best_fields``.
For more information, see :ref:`crate-reference:predicates_match_types`.

If you want to sort the results by ``_score``, you can use the ``order_by()``
function.

    >>> session.query(Character.name) \
    ...     .filter(
    ...         match(Character.name_ft, 'Arth',
    ...                 match_type='phrase',
    ...                 options={'fuzziness': 3})
    ...     ) \
    ...     .all()
    [('Arthur Dent',)]

It is not possible to specify options without the ``match_type`` argument:

    >>> session.query(Character.name) \
    ...     .filter(
    ...         match(Character.name_ft, 'Arth',
    ...                 options={'fuzziness': 3})
    ...     ) \
    ...     .all()
    Traceback (most recent call last):
    ValueError: missing match_type. It's not allowed to specify options without match_type


Aggregates: Counting and grouping
=================================

SQLAlchemy supports different approaches to issue a query with a count
aggregate function. Take a look at the `count result rows`_ documentation
for a full overview.

CrateDB currently does not support all variants as it can not handle the
sub-queries yet.

This means that queries using ``count()`` have to be written in one of the
following ways:

    >>> session.query(sa.func.count(Character.id)).scalar()
    2

    >>> session.query(sa.func.count('*')).select_from(Character).scalar()
    2

Using the ``group_by`` clause is similar:

    >>> session.query(sa.func.count(Character.id), Character.name) \
    ...     .group_by(Character.name) \
    ...     .order_by(sa.desc(sa.func.count(Character.id))) \
    ...     .order_by(Character.name).all()
    [(1, 'Arthur Dent'), (1, 'Tricia McMillan')]


``INSERT...FROM SELECT``
========================

In SQLAlchemy, the ``insert().from_select()`` function returns a new ``Insert``
construct, which represents an ``INSERT...FROM SELECT`` statement. This
functionality is supported by the CrateDB client library. Here is an example
that uses ``insert().from_select()``.

First, let's define and create the tables:

    >>> from sqlalchemy import select, insert

    >>> class Todos(Base):
    ...     __tablename__ = 'todos'
    ...     __table_args__ = {
    ...         'crate_number_of_replicas': '0'
    ...     }
    ...     id = sa.Column(sa.String, primary_key=True, default=gen_key)
    ...     content = sa.Column(sa.String)
    ...     status = sa.Column(sa.String)

    >>> class ArchivedTasks(Base):
    ...     __tablename__ = 'archived_tasks'
    ...     __table_args__ = {
    ...         'crate_number_of_replicas': '0'
    ...     }
    ...     id = sa.Column(sa.String, primary_key=True)
    ...     content = sa.Column(sa.String)

    >>> Base.metadata.create_all(bind=engine)

Let's add a task to the ``Todo`` table:

    >>> task = Todos(content='Write Tests', status='done')
    >>> session.add(task)
    >>> session.commit()
    >>> _ = connection.execute(sa.text("REFRESH TABLE todos"))

Now, let's use ``insert().from_select()`` to archive the task into the
``ArchivedTasks`` table:

    >>> sel = select(Todos.id, Todos.content).where(Todos.status == "done")
    >>> ins = insert(ArchivedTasks).from_select(['id', 'content'], sel)
    >>> result = session.execute(ins)
    >>> session.commit()

This will emit the following ``INSERT`` statement to the database:

    INSERT INTO archived_tasks (id, content)
        (SELECT todos.id, todos.content FROM todos WHERE todos.status = 'done')

Now, verify that the data is present in the database:

    >>> _ = connection.execute(sa.text("REFRESH TABLE archived_tasks"))
    >>> pprint([str(r) for r in session.execute(sa.text("SELECT content FROM archived_tasks"))])
    ["('Write Tests',)"]


``INSERT...RETURNING``
======================

The ``RETURNING`` clause can be used to retrieve the result rows of an ``INSERT``
operation. It may be specified using the ``Insert.returning()`` method.

The first step is to define the table:

    >>> from sqlalchemy import insert

    >>> class User(Base):
    ...     __tablename__ = 'user'
    ...     __table_args__ = {
    ...         'crate_number_of_replicas': '0'
    ...     }
    ...     id = sa.Column(sa.String, primary_key=True, default=gen_key)
    ...     username = sa.Column(sa.String)
    ...     email = sa.Column(sa.String)

    >>> Base.metadata.create_all(bind=engine)

Now, let's use the returning clause on our insert to retrieve the values inserted:

    >>> stmt = insert(User).values(username='Crate', email='crate@crate.io').returning(User.username, User.email)
    >>> result = session.execute(stmt)
    >>> session.commit()
    >>> print([str(r) for r in result])
    ["('Crate', 'crate@crate.io')"]

The following ``INSERT...RETURNING`` statement was issued to the database::

    INSERT INTO user (id, username, email)
    VALUES (:id, :username, :email)
    RETURNING user.id, user.username, user.email

``UPDATE...RETURNING``

The ``RETURNING`` clause can also be used with an ``UPDATE`` operation to return
specified rows to be returned on execution. It can be specified using the
``Update.returning()`` method.


We can reuse the user table previously created in the ``INSERT...RETURNING`` section.

Insert a user and get the user id:

    >>> from sqlalchemy import insert, update

    >>> stmt = insert(User).values(username='Arthur Dent', email='arthur_dent@crate.io').returning(User.id, User.username, User.email)
    >>> result = session.execute(stmt)
    >>> session.commit()
    >>> uid = [r[0] for r in result][0]

Now let's update the user:

    >>> stmt = update(User).where(User.id == uid).values(username='Tricia McMillan', email='tricia_mcmillan@crate.io').returning(User.username, User.email)
    >>> res = session.execute(stmt)
    >>> session.commit()
    >>> print([str(r) for r in res])
    ["('Tricia McMillan', 'tricia_mcmillan@crate.io')"]

The following ``UPDATE...RETURNING`` statement was issued to the database::

    UPDATE user SET username=:username, email=:email
    WHERE user.id = :id_1
    RETURNING user.username, user.email

.. hidden: Disconnect from database

    >>> session.close()
    >>> connection.close()
    >>> engine.dispose()


.. _count result rows: https://docs.sqlalchemy.org/en/14/orm/tutorial.html#counting
