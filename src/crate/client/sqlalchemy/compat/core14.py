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
from sqlalchemy.sql import selectable
from sqlalchemy.sql.crud import (REQUIRED, _create_bind_param,
                                 _extend_values_for_multiparams,
                                 _get_stmt_parameter_tuples_params,
                                 _get_update_multitable_params,
                                 _key_getters_for_crud_column, _scan_cols,
                                 _scan_insert_from_select_cols)

from crate.client.sqlalchemy.compiler import CrateCompiler


class CrateCompilerSA14(CrateCompiler):

    def visit_update(self, update_stmt, **kw):

        compile_state = update_stmt._compile_state_factory(
            update_stmt, self, **kw
        )
        update_stmt = compile_state.statement

        # [14] CrateDB patch.
        if not compile_state._dict_parameters and \
                not hasattr(update_stmt, '_crate_specific'):
            return super().visit_update(update_stmt, **kw)

        toplevel = not self.stack
        if toplevel:
            self.isupdate = True
            if not self.compile_state:
                self.compile_state = compile_state

        extra_froms = compile_state._extra_froms
        is_multitable = bool(extra_froms)

        if is_multitable:
            # main table might be a JOIN
            main_froms = set(selectable._from_objects(update_stmt.table))
            render_extra_froms = [
                f for f in extra_froms if f not in main_froms
            ]
            correlate_froms = main_froms.union(extra_froms)
        else:
            render_extra_froms = []
            correlate_froms = {update_stmt.table}

        self.stack.append(
            {
                "correlate_froms": correlate_froms,
                "asfrom_froms": correlate_froms,
                "selectable": update_stmt,
            }
        )

        text = "UPDATE "

        if update_stmt._prefixes:
            text += self._generate_prefixes(
                update_stmt, update_stmt._prefixes, **kw
            )

        table_text = self.update_tables_clause(
            update_stmt, update_stmt.table, render_extra_froms, **kw
        )

        # [14] CrateDB patch.
        crud_params = _get_crud_params(
            self, update_stmt, compile_state, **kw
        )

        if update_stmt._hints:
            dialect_hints, table_text = self._setup_crud_hints(
                update_stmt, table_text
            )
        else:
            dialect_hints = None

        if update_stmt._independent_ctes:
            for cte in update_stmt._independent_ctes:
                cte._compiler_dispatch(self, **kw)

        text += table_text

        text += " SET "

        # [14] CrateDB patch begin.
        include_table = \
            extra_froms and self.render_table_with_column_in_update_from

        set_clauses = []

        for c, expr, value in crud_params:
            key = c._compiler_dispatch(self, include_table=include_table)
            clause = key + ' = ' + value
            set_clauses.append(clause)

        for k, v in compile_state._dict_parameters.items():
            if isinstance(k, str) and '[' in k:
                bindparam = sa.sql.bindparam(k, v)
                clause = k + ' = ' + self.process(bindparam)
                set_clauses.append(clause)

        text += ', '.join(set_clauses)
        # [14] CrateDB patch end.

        if self.returning or update_stmt._returning:
            if self.returning_precedes_values:
                text += " " + self.returning_clause(
                    update_stmt, self.returning or update_stmt._returning
                )

        if extra_froms:
            extra_from_text = self.update_from_clause(
                update_stmt,
                update_stmt.table,
                render_extra_froms,
                dialect_hints,
                **kw
            )
            if extra_from_text:
                text += " " + extra_from_text

        if update_stmt._where_criteria:
            t = self._generate_delimited_and_list(
                update_stmt._where_criteria, **kw
            )
            if t:
                text += " WHERE " + t

        limit_clause = self.update_limit_clause(update_stmt)
        if limit_clause:
            text += " " + limit_clause

        if (
                self.returning or update_stmt._returning
        ) and not self.returning_precedes_values:
            text += " " + self.returning_clause(
                update_stmt, self.returning or update_stmt._returning
            )

        if self.ctes:
            nesting_level = len(self.stack) if not toplevel else None
            text = self._render_cte_clause(nesting_level=nesting_level) + text

        self.stack.pop(-1)

        return text


def _get_crud_params(compiler, stmt, compile_state, **kw):
    """create a set of tuples representing column/string pairs for use
    in an INSERT or UPDATE statement.

    Also generates the Compiled object's postfetch, prefetch, and
    returning column collections, used for default handling and ultimately
    populating the CursorResult's prefetch_cols() and postfetch_cols()
    collections.

    """

    compiler.postfetch = []
    compiler.insert_prefetch = []
    compiler.update_prefetch = []
    compiler.returning = []

    # getters - these are normally just column.key,
    # but in the case of mysql multi-table update, the rules for
    # .key must conditionally take tablename into account
    (
        _column_as_key,
        _getattr_col_key,
        _col_bind_name,
    ) = getters = _key_getters_for_crud_column(compiler, stmt, compile_state)

    compiler._key_getters_for_crud_column = getters

    # no parameters in the statement, no parameters in the
    # compiled params - return binds for all columns
    if compiler.column_keys is None and compile_state._no_parameters:
        return [
            (
                c,
                compiler.preparer.format_column(c),
                _create_bind_param(compiler, c, None, required=True),
            )
            for c in stmt.table.columns
        ]

    if compile_state._has_multi_parameters:
        spd = compile_state._multi_parameters[0]
        stmt_parameter_tuples = list(spd.items())
    elif compile_state._ordered_values:
        spd = compile_state._dict_parameters
        stmt_parameter_tuples = compile_state._ordered_values
    elif compile_state._dict_parameters:
        spd = compile_state._dict_parameters
        stmt_parameter_tuples = list(spd.items())
    else:
        stmt_parameter_tuples = spd = None

    # if we have statement parameters - set defaults in the
    # compiled params
    if compiler.column_keys is None:
        parameters = {}
    elif stmt_parameter_tuples:
        parameters = dict(
            (_column_as_key(key), REQUIRED)
            for key in compiler.column_keys
            if key not in spd
        )
    else:
        parameters = dict(
            (_column_as_key(key), REQUIRED) for key in compiler.column_keys
        )

    # create a list of column assignment clauses as tuples
    values = []

    if stmt_parameter_tuples is not None:
        _get_stmt_parameter_tuples_params(
            compiler,
            compile_state,
            parameters,
            stmt_parameter_tuples,
            _column_as_key,
            values,
            kw,
        )

    check_columns = {}

    # special logic that only occurs for multi-table UPDATE
    # statements
    if compile_state.isupdate and compile_state.is_multitable:
        _get_update_multitable_params(
            compiler,
            stmt,
            compile_state,
            stmt_parameter_tuples,
            check_columns,
            _col_bind_name,
            _getattr_col_key,
            values,
            kw,
        )

    if compile_state.isinsert and stmt._select_names:
        _scan_insert_from_select_cols(
            compiler,
            stmt,
            compile_state,
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
            compile_state,
            parameters,
            _getattr_col_key,
            _column_as_key,
            _col_bind_name,
            check_columns,
            values,
            kw,
        )

    # [14] CrateDB patch.
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
    if parameters and stmt_parameter_tuples:
        check = (
            set(parameters)
            .intersection(_column_as_key(k) for k, v in stmt_parameter_tuples)
            .difference(check_columns)
        )
        if check:
            raise exc.CompileError(
                "Unconsumed column names: %s"
                % (", ".join("%s" % (c,) for c in check))
            )
    """

    if compile_state._has_multi_parameters:
        values = _extend_values_for_multiparams(
            compiler,
            stmt,
            compile_state,
            values,
            _column_as_key,
            kw,
        )
    elif (
            not values
            and compiler.for_executemany  # noqa: W503
            and compiler.dialect.supports_default_metavalue  # noqa: W503
    ):
        # convert an "INSERT DEFAULT VALUES"
        # into INSERT (firstcol) VALUES (DEFAULT) which can be turned
        # into an in-place multi values.  This supports
        # insert_executemany_returning mode :)
        values = [
            (
                stmt.table.columns[0],
                compiler.preparer.format_column(stmt.table.columns[0]),
                "DEFAULT",
            )
        ]

    return values
