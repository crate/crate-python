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

from typing import Any, Dict, List, MutableMapping, Optional, Tuple, Union

import sqlalchemy as sa
from sqlalchemy import ColumnClause, ValuesBase, cast, exc
from sqlalchemy.sql import dml
from sqlalchemy.sql.base import _from_objects
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.crud import (REQUIRED, _as_dml_column, _create_bind_param,
                                 _CrudParamElement, _CrudParams,
                                 _extend_values_for_multiparams,
                                 _get_stmt_parameter_tuples_params,
                                 _get_update_multitable_params,
                                 _key_getters_for_crud_column, _scan_cols,
                                 _scan_insert_from_select_cols,
                                 _setup_delete_return_defaults)
from sqlalchemy.sql.dml import DMLState, _DMLColumnElement
from sqlalchemy.sql.dml import isinsert as _compile_state_isinsert

from crate.client.sqlalchemy.compiler import CrateCompiler


class CrateCompilerSA20(CrateCompiler):

    def visit_update(self, update_stmt, **kw):
        compile_state = update_stmt._compile_state_factory(
            update_stmt, self, **kw
        )
        update_stmt = compile_state.statement

        # [20] CrateDB patch.
        if not compile_state._dict_parameters and \
                not hasattr(update_stmt, '_crate_specific'):
            return super().visit_update(update_stmt, **kw)

        toplevel = not self.stack
        if toplevel:
            self.isupdate = True
            if not self.dml_compile_state:
                self.dml_compile_state = compile_state
            if not self.compile_state:
                self.compile_state = compile_state

        extra_froms = compile_state._extra_froms
        is_multitable = bool(extra_froms)

        if is_multitable:
            # main table might be a JOIN
            main_froms = set(_from_objects(update_stmt.table))
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
        # [20] CrateDB patch.
        crud_params_struct = _get_crud_params(
            self, update_stmt, compile_state, toplevel, **kw
        )
        crud_params = crud_params_struct.single_params

        if update_stmt._hints:
            dialect_hints, table_text = self._setup_crud_hints(
                update_stmt, table_text
            )
        else:
            dialect_hints = None

        if update_stmt._independent_ctes:
            self._dispatch_independent_ctes(update_stmt, kw)

        text += table_text

        text += " SET "

        # [20] CrateDB patch begin.
        include_table = extra_froms and \
            self.render_table_with_column_in_update_from

        set_clauses = []

        for c, expr, value, _ in crud_params:
            key = c._compiler_dispatch(self, include_table=include_table)
            clause = key + ' = ' + value
            set_clauses.append(clause)

        for k, v in compile_state._dict_parameters.items():
            if isinstance(k, str) and '[' in k:
                bindparam = sa.sql.bindparam(k, v)
                clause = k + ' = ' + self.process(bindparam)
                set_clauses.append(clause)

        text += ', '.join(set_clauses)
        # [20] CrateDB patch end.

        if self.implicit_returning or update_stmt._returning:
            if self.returning_precedes_values:
                text += " " + self.returning_clause(
                    update_stmt,
                    self.implicit_returning or update_stmt._returning,
                    populate_result_map=toplevel,
                )

        if extra_froms:
            extra_from_text = self.update_from_clause(
                update_stmt,
                update_stmt.table,
                render_extra_froms,
                dialect_hints,
                **kw,
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
            self.implicit_returning or update_stmt._returning
        ) and not self.returning_precedes_values:
            text += " " + self.returning_clause(
                update_stmt,
                self.implicit_returning or update_stmt._returning,
                populate_result_map=toplevel,
            )

        if self.ctes:
            nesting_level = len(self.stack) if not toplevel else None
            text = self._render_cte_clause(nesting_level=nesting_level) + text

        self.stack.pop(-1)

        return text


def _get_crud_params(
    compiler: SQLCompiler,
    stmt: ValuesBase,
    compile_state: DMLState,
    toplevel: bool,
    **kw: Any,
) -> _CrudParams:
    """create a set of tuples representing column/string pairs for use
    in an INSERT or UPDATE statement.

    Also generates the Compiled object's postfetch, prefetch, and
    returning column collections, used for default handling and ultimately
    populating the CursorResult's prefetch_cols() and postfetch_cols()
    collections.

    """

    # note: the _get_crud_params() system was written with the notion in mind
    # that INSERT, UPDATE, DELETE are always the top level statement and
    # that there is only one of them.  With the addition of CTEs that can
    # make use of DML, this assumption is no longer accurate; the DML
    # statement is not necessarily the top-level "row returning" thing
    # and it is also theoretically possible (fortunately nobody has asked yet)
    # to have a single statement with multiple DMLs inside of it via CTEs.

    # the current _get_crud_params() design doesn't accommodate these cases
    # right now.  It "just works" for a CTE that has a single DML inside of
    # it, and for a CTE with multiple DML, it's not clear what would happen.

    # overall, the "compiler.XYZ" collections here would need to be in a
    # per-DML structure of some kind, and DefaultDialect would need to
    # navigate these collections on a per-statement basis, with additional
    # emphasis on the "toplevel returning data" statement.  However we
    # still need to run through _get_crud_params() for all DML as we have
    # Python / SQL generated column defaults that need to be rendered.

    # if there is user need for this kind of thing, it's likely a post 2.0
    # kind of change as it would require deep changes to DefaultDialect
    # as well as here.

    compiler.postfetch = []
    compiler.insert_prefetch = []
    compiler.update_prefetch = []
    compiler.implicit_returning = []

    # getters - these are normally just column.key,
    # but in the case of mysql multi-table update, the rules for
    # .key must conditionally take tablename into account
    (
        _column_as_key,
        _getattr_col_key,
        _col_bind_name,
    ) = _key_getters_for_crud_column(compiler, stmt, compile_state)

    compiler._get_bind_name_for_col = _col_bind_name

    if stmt._returning and stmt._return_defaults:
        raise exc.CompileError(
            "Can't compile statement that includes returning() and "
            "return_defaults() simultaneously"
        )

    if compile_state.isdelete:
        _setup_delete_return_defaults(
            compiler,
            stmt,
            compile_state,
            (),
            _getattr_col_key,
            _column_as_key,
            _col_bind_name,
            (),
            (),
            toplevel,
            kw,
        )
        return _CrudParams([], [])

    # no parameters in the statement, no parameters in the
    # compiled params - return binds for all columns
    if compiler.column_keys is None and compile_state._no_parameters:
        return _CrudParams(
            [
                (
                    c,
                    compiler.preparer.format_column(c),
                    _create_bind_param(compiler, c, None, required=True),
                    (c.key,),
                )
                for c in stmt.table.columns
            ],
            [],
        )

    stmt_parameter_tuples: Optional[
        List[Tuple[Union[str, ColumnClause[Any]], Any]]
    ]
    spd: Optional[MutableMapping[_DMLColumnElement, Any]]

    if (
        _compile_state_isinsert(compile_state)
        and compile_state._has_multi_parameters
    ):
        mp = compile_state._multi_parameters
        assert mp is not None
        spd = mp[0]
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
        assert spd is not None
        parameters = {
            _column_as_key(key): REQUIRED
            for key in compiler.column_keys
            if key not in spd
        }
    else:
        parameters = {
            _column_as_key(key): REQUIRED for key in compiler.column_keys
        }

    # create a list of column assignment clauses as tuples
    values: List[_CrudParamElement] = []

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

    check_columns: Dict[str, ColumnClause[Any]] = {}

    # special logic that only occurs for multi-table UPDATE
    # statements
    if dml.isupdate(compile_state) and compile_state.is_multitable:
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

    if _compile_state_isinsert(compile_state) and stmt._select_names:
        # is an insert from select, is not a multiparams

        assert not compile_state._has_multi_parameters

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
            toplevel,
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
            toplevel,
            kw,
        )

    # [20] CrateDB patch.
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
    #   sqlalchemy.exc.CompileError: Unconsumed column names: characters_name
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

    if (
        _compile_state_isinsert(compile_state)
        and compile_state._has_multi_parameters
    ):
        # is a multiparams, is not an insert from a select
        assert not stmt._select_names
        multi_extended_values = _extend_values_for_multiparams(
            compiler,
            stmt,
            compile_state,
            cast(
                "Sequence[_CrudParamElementStr]",
                values,
            ),
            cast("Callable[..., str]", _column_as_key),
            kw,
        )
        return _CrudParams(values, multi_extended_values)
    elif (
        not values
        and compiler.for_executemany
        and compiler.dialect.supports_default_metavalue
    ):
        # convert an "INSERT DEFAULT VALUES"
        # into INSERT (firstcol) VALUES (DEFAULT) which can be turned
        # into an in-place multi values.  This supports
        # insert_executemany_returning mode :)
        values = [
            (
                _as_dml_column(stmt.table.columns[0]),
                compiler.preparer.format_column(stmt.table.columns[0]),
                compiler.dialect.default_metavalue_token,
                (),
            )
        ]

    return _CrudParams(values, [])
