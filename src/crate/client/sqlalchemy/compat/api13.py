# -*- coding: utf-8; -*-
#
# Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  Crate licenses
# this file to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
#
#   https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
# However, if you have executed another commercial license agreement
# with Crate these terms will supersede the license and you may use the
# software solely pursuant to the terms of the relevant commercial agreement.

"""
Compatibility module for running a subset of SQLAlchemy 2.0 programs on
SQLAlchemy 1.3. By using monkey-patching, it can do two things:

1. Add the `exec_driver_sql` method to SA's `Connection` and `Engine`.
2. Amend the `sql.select` function to accept the calling semantics of
   the modern variant.

Reason: `exec_driver_sql` gets used within the CrateDB dialect already,
and the new calling semantics of `sql.select` already get used within
many of the test cases already. Please note that the patch for
`sql.select` is only applied when running the test suite.
"""

import collections.abc as collections_abc

from sqlalchemy import exc
from sqlalchemy.sql import Select
from sqlalchemy.sql import select as original_select
from sqlalchemy.util import immutabledict


# `_distill_params_20` copied from SA14's `sqlalchemy.engine.{base,util}`.
_no_tuple = ()
_no_kw = immutabledict()


def _distill_params_20(params):
    if params is None:
        return _no_tuple, _no_kw
    elif isinstance(params, list):
        # collections_abc.MutableSequence): # avoid abc.__instancecheck__
        if params and not isinstance(params[0], (collections_abc.Mapping, tuple)):
            raise exc.ArgumentError(
                "List argument must consist only of tuples or dictionaries"
            )

        return (params,), _no_kw
    elif isinstance(
        params,
        (tuple, dict, immutabledict),
        # only do abc.__instancecheck__ for Mapping after we've checked
        # for plain dictionaries and would otherwise raise
    ) or isinstance(params, collections_abc.Mapping):
        return (params,), _no_kw
    else:
        raise exc.ArgumentError("mapping or sequence expected for parameters")


def exec_driver_sql(self, statement, parameters=None, execution_options=None):
    """
    Adapter for `exec_driver_sql`, which is available since SA14, for SA13.
    """
    if execution_options is not None:
        raise ValueError(
            "SA13 backward-compatibility: "
            "`exec_driver_sql` does not support `execution_options`"
        )
    args_10style, kwargs_10style = _distill_params_20(parameters)
    return self.execute(statement, *args_10style, **kwargs_10style)


def monkeypatch_add_exec_driver_sql():
    """
    Transparently add SA14's `exec_driver_sql()` method to SA13.

    AttributeError: 'Connection' object has no attribute 'exec_driver_sql'
    AttributeError: 'Engine' object has no attribute 'exec_driver_sql'
    """
    from sqlalchemy.engine.base import Connection, Engine

    # Add `exec_driver_sql` method to SA's `Connection` and `Engine` classes.
    Connection.exec_driver_sql = exec_driver_sql
    Engine.exec_driver_sql = exec_driver_sql


def select_sa14(*columns, **kw) -> Select:
    """
    Adapt SA14/SA20's calling semantics of `sql.select()` to SA13.

    With SA20, `select()` no longer accepts varied constructor arguments, only
    the "generative" style of `select()` will be supported. The list of columns
    / tables to select from should be passed positionally.

    Derived from https://github.com/sqlalchemy/alembic/blob/b1fad6b6/alembic/util/sqla_compat.py#L557-L558

    sqlalchemy.exc.ArgumentError: columns argument to select() must be a Python list or other iterable
    """
    if isinstance(columns, tuple) and isinstance(columns[0], list):
        if "whereclause" in kw:
            raise ValueError(
                "SA13 backward-compatibility: "
                "`whereclause` is both in kwargs and columns tuple"
            )
        columns, whereclause = columns
        kw["whereclause"] = whereclause
    return original_select(columns, **kw)


def monkeypatch_amend_select_sa14():
    """
    Make SA13's `sql.select()` transparently accept calling semantics of SA14
    and SA20, by swapping in the newer variant of `select_sa14()`.

    This supports the test suite of `crate-python`, because it already uses the
    modern calling semantics.
    """
    import sqlalchemy

    sqlalchemy.select = select_sa14
    sqlalchemy.sql.select = select_sa14
    sqlalchemy.sql.expression.select = select_sa14


@property
def connectionfairy_driver_connection_sa14(self):
    """The connection object as returned by the driver after a connect.

    .. versionadded:: 1.4.24

    .. seealso::

        :attr:`._ConnectionFairy.dbapi_connection`

        :attr:`._ConnectionRecord.driver_connection`

        :ref:`faq_dbapi_connection`

    """
    return self.connection


def monkeypatch_add_connectionfairy_driver_connection():
    import sqlalchemy.pool.base
    sqlalchemy.pool.base._ConnectionFairy.driver_connection = connectionfairy_driver_connection_sa14
