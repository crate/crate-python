# -*- coding: utf-8; -*-
#
# Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  Crate licenses
# this file to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
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

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql.base import PGCompiler
from sqlalchemy.sql.crud import (REQUIRED, _create_bind_param,
                                 _extend_values_for_multiparams,
                                 _get_multitable_params,
                                 _get_stmt_parameters_params,
                                 _key_getters_for_crud_column, _scan_cols,
                                 _scan_insert_from_select_cols)

from crate.client.sqlalchemy.compiler import CrateCompiler


class CrateCompilerSA10(CrateCompiler):

    def returning_clause(self, stmt, returning_cols):
        """
        Generate RETURNING clause, PostgreSQL-compatible.
        """
        return PGCompiler.returning_clause(self, stmt, returning_cols)

    def visit_update(self, update_stmt, **kw):
        """
        used to compile <sql.expression.Update> expressions
        Parts are taken from the SQLCompiler base class.
        """

        # [10] CrateDB patch.
        if not update_stmt.parameters and \
                not hasattr(update_stmt, '_crate_specific'):
            return super().visit_update(update_stmt, **kw)

        self.isupdate = True

        extra_froms = update_stmt._extra_froms

        text = 'UPDATE '

        if update_stmt._prefixes:
            text += self._generate_prefixes(update_stmt,
                                            update_stmt._prefixes, **kw)

        table_text = self.update_tables_clause(update_stmt, update_stmt.table,
                                               extra_froms, **kw)

        dialect_hints = None
        if update_stmt._hints:
            dialect_hints, table_text = self._setup_crud_hints(
                update_stmt, table_text
            )

        # [10] CrateDB patch.
        crud_params = _get_crud_params(self, update_stmt, **kw)

        text += table_text

        text += ' SET '

        # [10] CrateDB patch begin.
        include_table = \
            extra_froms and self.render_table_with_column_in_update_from

        set_clauses = []

        for k, v in crud_params:
            clause = k._compiler_dispatch(self,
                                          include_table=include_table) + \
                ' = ' + v
            set_clauses.append(clause)

        for k, v in update_stmt.parameters.items():
            if isinstance(k, str) and '[' in k:
                bindparam = sa.sql.bindparam(k, v)
                set_clauses.append(k + ' = ' + self.process(bindparam))

        text += ', '.join(set_clauses)
        # [10] CrateDB patch end.

        if self.returning or update_stmt._returning:
            if not self.returning:
                self.returning = update_stmt._returning
            if self.returning_precedes_values:
                text += " " + self.returning_clause(
                    update_stmt, self.returning)

        if extra_froms:
            extra_from_text = self.update_from_clause(
                update_stmt,
                update_stmt.table,
                extra_froms,
                dialect_hints,
                **kw)
            if extra_from_text:
                text += " " + extra_from_text

        if update_stmt._whereclause is not None:
            t = self.process(update_stmt._whereclause)
            if t:
                text += " WHERE " + t

        limit_clause = self.update_limit_clause(update_stmt)
        if limit_clause:
            text += " " + limit_clause

        if self.returning and not self.returning_precedes_values:
            text += " " + self.returning_clause(
                update_stmt, self.returning)

        return text


def _get_crud_params(compiler, stmt, **kw):
    """create a set of tuples representing column/string pairs for use
    in an INSERT or UPDATE statement.

    Also generates the Compiled object's postfetch, prefetch, and
    returning column collections, used for default handling and ultimately
    populating the ResultProxy's prefetch_cols() and postfetch_cols()
    collections.

    """

    compiler.postfetch = []
    compiler.insert_prefetch = []
    compiler.update_prefetch = []
    compiler.returning = []

    # no parameters in the statement, no parameters in the
    # compiled params - return binds for all columns
    if compiler.column_keys is None and stmt.parameters is None:
        return [
            (c, _create_bind_param(compiler, c, None, required=True))
            for c in stmt.table.columns
        ]

    if stmt._has_multi_parameters:
        stmt_parameters = stmt.parameters[0]
    else:
        stmt_parameters = stmt.parameters

    # getters - these are normally just column.key,
    # but in the case of mysql multi-table update, the rules for
    # .key must conditionally take tablename into account
    (
        _column_as_key,
        _getattr_col_key,
        _col_bind_name,
    ) = _key_getters_for_crud_column(compiler, stmt)

    # if we have statement parameters - set defaults in the
    # compiled params
    if compiler.column_keys is None:
        parameters = {}
    else:
        parameters = dict(
            (_column_as_key(key), REQUIRED)
            for key in compiler.column_keys
            if not stmt_parameters or key not in stmt_parameters
        )

    # create a list of column assignment clauses as tuples
    values = []

    if stmt_parameters is not None:
        _get_stmt_parameters_params(
            compiler, parameters, stmt_parameters, _column_as_key, values, kw
        )

    check_columns = {}

    # special logic that only occurs for multi-table UPDATE
    # statements
    if compiler.isupdate and stmt._extra_froms and stmt_parameters:
        _get_multitable_params(
            compiler,
            stmt,
            stmt_parameters,
            check_columns,
            _col_bind_name,
            _getattr_col_key,
            values,
            kw,
        )

    if compiler.isinsert and stmt.select_names:
        _scan_insert_from_select_cols(
            compiler,
            stmt,
            parameters,
            _getattr_col_key,
            _column_as_key,
            _col_bind_name,
            check_columns,
            values,
            kw,
        )
    else:
        _scan_cols(
            compiler,
            stmt,
            parameters,
            _getattr_col_key,
            _column_as_key,
            _col_bind_name,
            check_columns,
            values,
            kw,
        )

    # [10] CrateDB patch.
    #
    # This sanity check performed by SQLAlchemy currently needs to be
    # deactivated in order to satisfy the rewriting logic of the CrateDB
    # dialect in `rewrite_update` and `visit_update`.
    #
    # It can be quickly reproduced by activating this section and running the
    # test cases::
    #
    #   ./bin/test -vvvv -t dict_test
    #
    # That croaks like::
    #
    #   sqlalchemy.exc.CompileError: Unconsumed column names: characters_name, data['nested']
    #
    # TODO: Investigate why this is actually happening and eventually mitigate
    #       the root cause.
    """
    if parameters and stmt_parameters:
        check = (
            set(parameters)
            .intersection(_column_as_key(k) for k in stmt_parameters)
            .difference(check_columns)
        )
        if check:
            raise exc.CompileError(
                "Unconsumed column names: %s"
                % (", ".join("%s" % c for c in check))
            )
    """

    if stmt._has_multi_parameters:
        values = _extend_values_for_multiparams(compiler, stmt, values, kw)

    return values
