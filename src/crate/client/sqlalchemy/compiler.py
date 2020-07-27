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

import string
from collections import defaultdict

import sqlalchemy as sa
from sqlalchemy.sql import crud
from sqlalchemy.sql import compiler
from .types import MutableDict
from .sa_version import SA_1_1, SA_VERSION


def rewrite_update(clauseelement, multiparams, params):
    """ change the params to enable partial updates

    sqlalchemy by default only supports updates of complex types in the form of

        "col = ?", ({"x": 1, "y": 2}

    but crate supports

        "col['x'] = ?, col['y'] = ?", (1, 2)

    by using the `Craty` (`MutableDict`) type.
    The update statement is only rewritten if an item of the MutableDict was
    changed.
    """
    newmultiparams = []
    _multiparams = multiparams[0]
    if len(_multiparams) == 0:
        return clauseelement, multiparams, params
    for _params in _multiparams:
        newparams = {}
        for key, val in _params.items():
            if (
                not isinstance(val, MutableDict) or
                (not any(val._changed_keys) and not any(val._deleted_keys))
            ):
                newparams[key] = val
                continue

            for subkey, subval in val.items():
                if subkey in val._changed_keys:
                    newparams["{0}['{1}']".format(key, subkey)] = subval
            for subkey in val._deleted_keys:
                newparams["{0}['{1}']".format(key, subkey)] = None
        newmultiparams.append(newparams)
    _multiparams = (newmultiparams, )
    clause = clauseelement.values(newmultiparams[0])
    clause._crate_specific = True
    return clause, _multiparams, params


@sa.event.listens_for(sa.engine.Engine, "before_execute", retval=True)
def crate_before_execute(conn, clauseelement, multiparams, params):
    is_crate = type(conn.dialect).__name__ == 'CrateDialect'
    if is_crate and isinstance(clauseelement, sa.sql.expression.Update):
        return rewrite_update(clauseelement, multiparams, params)
    return clauseelement, multiparams, params


class CrateDDLCompiler(compiler.DDLCompiler):

    __special_opts_tmpl = {
        'PARTITIONED_BY': ' PARTITIONED BY ({0})'
    }
    __clustered_opts_tmpl = {
        'NUMBER_OF_SHARDS': ' INTO {0} SHARDS',
        'CLUSTERED_BY': ' BY ({0})',
    }
    __clustered_opt_tmpl = ' CLUSTERED{CLUSTERED_BY}{NUMBER_OF_SHARDS}'

    def get_column_specification(self, column, **kwargs):
        colspec = self.preparer.format_column(column) + " " + \
            self.dialect.type_compiler.process(column.type)
        # TODO: once supported add default / NOT NULL here
        return colspec

    def post_create_table(self, table):
        special_options = ''
        clustered_options = defaultdict(str)
        table_opts = []

        opts = dict(
            (k[len(self.dialect.name) + 1:].upper(), v)
            for k, v, in table.kwargs.items()
            if k.startswith('%s_' % self.dialect.name)
        )
        for k, v in opts.items():
            if k in self.__special_opts_tmpl:
                special_options += self.__special_opts_tmpl[k].format(v)
            elif k in self.__clustered_opts_tmpl:
                clustered_options[k] = self.__clustered_opts_tmpl[k].format(v)
            else:
                table_opts.append('{0} = {1}'.format(k, v))
        if clustered_options:
            special_options += string.Formatter().vformat(
                self.__clustered_opt_tmpl, (), clustered_options)
        if table_opts:
            return special_options + ' WITH ({0})'.format(
                ', '.join(sorted(table_opts)))
        return special_options


class CrateTypeCompiler(compiler.GenericTypeCompiler):

    def visit_string(self, type_, **kw):
        return 'STRING'

    def visit_unicode(self, type_, **kw):
        return 'STRING'

    def visit_TEXT(self, type_, **kw):
        return 'STRING'

    def visit_DECIMAL(self, type_, **kw):
        return 'DOUBLE'

    def visit_BIGINT(self, type_, **kw):
        return 'LONG'

    def visit_NUMERIC(self, type_, **kw):
        return 'LONG'

    def visit_INTEGER(self, type_, **kw):
        return 'INT'

    def visit_SMALLINT(self, type_, **kw):
        return 'SHORT'

    def visit_datetime(self, type_, **kw):
        return 'TIMESTAMP'

    def visit_date(self, type_, **kw):
        return 'TIMESTAMP'

    def visit_ARRAY(self, type_, **kw):
        if type_.dimensions is not None and type_.dimensions > 1:
            raise NotImplementedError(
                "CrateDB doesn't support multidimensional arrays")
        return 'ARRAY({0})'.format(self.process(type_.item_type))


class CrateCompiler(compiler.SQLCompiler):

    prefetch = []

    def visit_getitem_binary(self, binary, operator, **kw):
        return "{0}['{1}']".format(
            self.process(binary.left, **kw),
            binary.right.value
        )

    def visit_any(self, element, **kw):
        return "%s%sANY (%s)" % (
            self.process(element.left, **kw),
            compiler.OPERATORS[element.operator],
            self.process(element.right, **kw)
        )

    def returning_clause(self, stmt, returning_cols):
        columns = [
            self._label_select_column(None, c, True, False, {})
            for c in sa.sql.expression._select_iterables(returning_cols)
        ]
        return "RETURNING " + ", ".join(columns)

    def visit_insert(self, insert_stmt, asfrom=False, **kw):
        """
        used to compile <sql.expression.Insert> expressions.

        this function wraps insert_from_select statements inside
         parentheses to be conform with earlier versions of CreateDB.
        """

        self.stack.append(
            {'correlate_froms': set(),
             "asfrom_froms": set(),
             "selectable": insert_stmt})

        self.isinsert = True
        crud_params = crud._get_crud_params(self, insert_stmt, **kw)

        if not crud_params and \
                not self.dialect.supports_default_values and \
                not self.dialect.supports_empty_insert:
            raise NotImplementedError(
                "The '%s' dialect with current database version settings does "
                "not support empty inserts." % self.dialect.name)

        if insert_stmt._has_multi_parameters:
            if not self.dialect.supports_multivalues_insert:
                raise NotImplementedError(
                    "The '%s' dialect with current database "
                    "version settings does not support "
                    "in-place multirow inserts." % self.dialect.name)
            crud_params_single = crud_params[0]
        else:
            crud_params_single = crud_params

        preparer = self.preparer
        supports_default_values = self.dialect.supports_default_values

        text = "INSERT "

        if insert_stmt._prefixes:
            text += self._generate_prefixes(insert_stmt,
                                            insert_stmt._prefixes, **kw)

        text += "INTO "
        table_text = preparer.format_table(insert_stmt.table)

        if insert_stmt._hints:
            dialect_hints = dict([
                (table, hint_text)
                for (table, dialect), hint_text in
                insert_stmt._hints.items()
                if dialect in ('*', self.dialect.name)
            ])
            if insert_stmt.table in dialect_hints:
                table_text = self.format_from_hint_text(
                    table_text,
                    insert_stmt.table,
                    dialect_hints[insert_stmt.table],
                    True
                )

        text += table_text

        if crud_params_single or not supports_default_values:
            text += " (%s)" % ', '.join([preparer.format_column(c[0])
                                         for c in crud_params_single])

        if self.returning or insert_stmt._returning:
            self.returning = self.returning or insert_stmt._returning
            returning_clause = self.returning_clause(
                insert_stmt, self.returning)

            if self.returning_precedes_values:
                text += " " + returning_clause

        if insert_stmt.select is not None:
            text += " (%s)" % self.process(self._insert_from_select, **kw)
        elif not crud_params and supports_default_values:
            text += " DEFAULT VALUES"
        elif insert_stmt._has_multi_parameters:
            text += " VALUES %s" % (
                ", ".join(
                    "(%s)" % (
                        ', '.join(c[1] for c in crud_param_set)
                    )
                    for crud_param_set in crud_params
                )
            )
        else:
            text += " VALUES (%s)" % \
                ', '.join([c[1] for c in crud_params])

        if self.returning and not self.returning_precedes_values:
            text += " " + returning_clause

        self.stack.pop(-1)

        return text

    def visit_update(self, update_stmt, **kw):
        """
        used to compile <sql.expression.Update> expressions
        Parts are taken from the SQLCompiler base class.
        """

        if not update_stmt.parameters and \
                not hasattr(update_stmt, '_crate_specific'):
            return super(CrateCompiler, self).visit_update(update_stmt, **kw)

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

        crud_params = self._get_crud_params(update_stmt, **kw)

        text += table_text

        text += ' SET '
        include_table = extra_froms and \
            self.render_table_with_column_in_update_from

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
        """ extract values from crud parameters

        taken from SQLAlchemy's crud module (since 1.0.x) and
        adapted for Crate dialect"""

        compiler.postfetch = []
        compiler.insert_prefetch = []
        compiler.update_prefetch = []
        compiler.returning = []

        # no parameters in the statement, no parameters in the
        # compiled params - return binds for all columns
        if compiler.column_keys is None and stmt.parameters is None:
            return [(c, crud._create_bind_param(compiler, c, None,
                                                required=True))
                    for c in stmt.table.columns]

        if stmt._has_multi_parameters:
            stmt_parameters = stmt.parameters[0]
        else:
            stmt_parameters = stmt.parameters

        # getters - these are normally just column.key,
        # but in the case of mysql multi-table update, the rules for
        # .key must conditionally take tablename into account
        if SA_VERSION >= SA_1_1:
            _column_as_key, _getattr_col_key, _col_bind_name = \
                crud._key_getters_for_crud_column(compiler, stmt)
        else:
            _column_as_key, _getattr_col_key, _col_bind_name = \
                crud._key_getters_for_crud_column(compiler)

        # if we have statement parameters - set defaults in the
        # compiled params
        if compiler.column_keys is None:
            parameters = {}
        else:
            parameters = dict((_column_as_key(key), crud.REQUIRED)
                              for key in compiler.column_keys
                              if not stmt_parameters or
                              key not in stmt_parameters)

        # create a list of column assignment clauses as tuples
        values = []

        if stmt_parameters is not None:
            crud._get_stmt_parameters_params(
                compiler,
                parameters, stmt_parameters, _column_as_key, values, kw)

        check_columns = {}

        crud._scan_cols(compiler, stmt, parameters,
                        _getattr_col_key, _column_as_key,
                        _col_bind_name, check_columns, values, kw)

        if stmt._has_multi_parameters:
            values = crud._extend_values_for_multiparams(compiler, stmt,
                                                         values, kw)

        return values
