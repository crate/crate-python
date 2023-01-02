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
from sqlalchemy.dialects.postgresql.base import PGCompiler
from sqlalchemy.sql import compiler
from .types import MutableDict, _Craty, Geopoint, Geoshape
from .sa_version import SA_VERSION, SA_1_4


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
def crate_before_execute(conn, clauseelement, multiparams, params, *args, **kwargs):
    is_crate = type(conn.dialect).__name__ == 'CrateDialect'
    if is_crate and isinstance(clauseelement, sa.sql.expression.Update):
        if SA_VERSION >= SA_1_4:
            if params is None:
                multiparams = ([],)
            else:
                multiparams = ([params],)
            params = {}

        clauseelement, multiparams, params = rewrite_update(clauseelement, multiparams, params)

        if SA_VERSION >= SA_1_4:
            if multiparams[0]:
                params = multiparams[0][0]
            else:
                params = multiparams[0]
            multiparams = []

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
        # TODO: once supported add default here

        if column.computed is not None:
            colspec += " " + self.process(column.computed)

        if column.nullable is False:
            colspec += " NOT NULL"
        elif column.nullable and column.primary_key:
            raise sa.exc.CompileError(
                "Primary key columns cannot be nullable"
            )

        if column.dialect_options['crate'].get('index') is False:
            if isinstance(column.type, (Geopoint, Geoshape, _Craty)):
                raise sa.exc.CompileError(
                    "Disabling indexing is not supported for column "
                    "types OBJECT, GEO_POINT, and GEO_SHAPE"
                )

            colspec += " INDEX OFF"

        return colspec

    def visit_computed_column(self, generated):
        if generated.persisted is False:
            raise sa.exc.CompileError(
                "Virtual computed columns are not supported, set "
                "'persisted' to None or True"
            )

        return "GENERATED ALWAYS AS (%s)" % self.sql_compiler.process(
            generated.sqltext, include_table=False, literal_binds=True
        )

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

    def limit_clause(self, select, **kw):
        """
        Generate OFFSET / LIMIT clause, PostgreSQL-compatible.
        """
        return PGCompiler.limit_clause(self, select, **kw)
