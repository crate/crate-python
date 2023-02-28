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

import logging
from datetime import datetime, date

from sqlalchemy import types as sqltypes
from sqlalchemy.engine import default, reflection
from sqlalchemy.sql import functions
from sqlalchemy.util import asbool, to_list

from .compiler import (
    CrateTypeCompiler,
    CrateDDLCompiler
)
from crate.client.exceptions import TimezoneUnawareException
from .sa_version import SA_VERSION, SA_1_4, SA_2_0
from .types import Object, ObjectArray

TYPES_MAP = {
    "boolean": sqltypes.Boolean,
    "short": sqltypes.SmallInteger,
    "smallint": sqltypes.SmallInteger,
    "timestamp": sqltypes.TIMESTAMP,
    "timestamp with time zone": sqltypes.TIMESTAMP,
    "object": Object,
    "integer": sqltypes.Integer,
    "long": sqltypes.NUMERIC,
    "bigint": sqltypes.NUMERIC,
    "double": sqltypes.DECIMAL,
    "double precision": sqltypes.DECIMAL,
    "object_array": ObjectArray,
    "float": sqltypes.Float,
    "real": sqltypes.Float,
    "string": sqltypes.String,
    "text": sqltypes.String
}
try:
    # SQLAlchemy >= 1.1
    from sqlalchemy.types import ARRAY
    TYPES_MAP["integer_array"] = ARRAY(sqltypes.Integer)
    TYPES_MAP["boolean_array"] = ARRAY(sqltypes.Boolean)
    TYPES_MAP["short_array"] = ARRAY(sqltypes.SmallInteger)
    TYPES_MAP["smallint_array"] = ARRAY(sqltypes.SmallInteger)
    TYPES_MAP["timestamp_array"] = ARRAY(sqltypes.TIMESTAMP)
    TYPES_MAP["timestamp with time zone_array"] = ARRAY(sqltypes.TIMESTAMP)
    TYPES_MAP["long_array"] = ARRAY(sqltypes.NUMERIC)
    TYPES_MAP["bigint_array"] = ARRAY(sqltypes.NUMERIC)
    TYPES_MAP["double_array"] = ARRAY(sqltypes.DECIMAL)
    TYPES_MAP["double precision_array"] = ARRAY(sqltypes.DECIMAL)
    TYPES_MAP["float_array"] = ARRAY(sqltypes.Float)
    TYPES_MAP["real_array"] = ARRAY(sqltypes.Float)
    TYPES_MAP["string_array"] = ARRAY(sqltypes.String)
    TYPES_MAP["text_array"] = ARRAY(sqltypes.String)
except Exception:
    pass


log = logging.getLogger(__name__)


class Date(sqltypes.Date):
    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                assert isinstance(value, date)
                return value.strftime('%Y-%m-%d')
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if not value:
                return
            try:
                return datetime.utcfromtimestamp(value / 1e3).date()
            except TypeError:
                pass

            # Crate doesn't really have datetime or date types but a
            # timestamp type. The "date" mapping (conversion to long)
            # is only applied if the schema definition for the column exists
            # and if the sql insert statement was used.
            # In case of dynamic mapping or using the rest indexing endpoint
            # the date will be returned in the format it was inserted.
            log.warning(
                "Received timestamp isn't a long value."
                "Trying to parse as date string and then as datetime string")
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ').date()
        return process


class DateTime(sqltypes.DateTime):

    TZ_ERROR_MSG = "Timezone aware datetime objects are not supported"

    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                assert isinstance(value, datetime)
                if value.tzinfo is not None:
                    raise TimezoneUnawareException(DateTime.TZ_ERROR_MSG)
                return value.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if not value:
                return
            try:
                return datetime.utcfromtimestamp(value / 1e3)
            except TypeError:
                pass

            # Crate doesn't really have datetime or date types but a
            # timestamp type. The "date" mapping (conversion to long)
            # is only applied if the schema definition for the column exists
            # and if the sql insert statement was used.
            # In case of dynamic mapping or using the rest indexing endpoint
            # the date will be returned in the format it was inserted.
            log.warning(
                "Received timestamp isn't a long value."
                "Trying to parse as datetime string and then as date string")
            try:
                return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError:
                return datetime.strptime(value, '%Y-%m-%d')
        return process


colspecs = {
    sqltypes.DateTime: DateTime,
    sqltypes.Date: Date
}


if SA_VERSION >= SA_2_0:
    from .compat.core20 import CrateCompilerSA20
    statement_compiler = CrateCompilerSA20
elif SA_VERSION >= SA_1_4:
    from .compat.core14 import CrateCompilerSA14
    statement_compiler = CrateCompilerSA14
else:
    from .compat.core10 import CrateCompilerSA10
    statement_compiler = CrateCompilerSA10


class CrateDialect(default.DefaultDialect):
    name = 'crate'
    driver = 'crate-python'
    statement_compiler = statement_compiler
    ddl_compiler = CrateDDLCompiler
    type_compiler = CrateTypeCompiler
    supports_native_boolean = True
    supports_statement_cache = True
    colspecs = colspecs
    implicit_returning = True

    def __init__(self, *args, **kwargs):
        super(CrateDialect, self).__init__(*args, **kwargs)
        # currently our sql parser doesn't support unquoted column names that
        # start with _. Adding it here causes sqlalchemy to quote such columns
        self.identifier_preparer.illegal_initial_characters.add('_')

    def initialize(self, connection):
        # get lowest server version
        self.server_version_info = \
            self._get_server_version_info(connection)
        # get default schema name
        self.default_schema_name = \
            self._get_default_schema_name(connection)

    def do_rollback(self, connection):
        # if any exception is raised by the dbapi, sqlalchemy by default
        # attempts to do a rollback crate doesn't support rollbacks.
        # implementing this as noop seems to cause sqlalchemy to propagate the
        # original exception to the user
        pass

    def connect(self, host=None, port=None, *args, **kwargs):
        server = None
        if host:
            server = '{0}:{1}'.format(host, port or '4200')
        if 'servers' in kwargs:
            server = kwargs.pop('servers')
        servers = to_list(server)
        if servers:
            use_ssl = asbool(kwargs.pop("ssl", False))
            if use_ssl:
                servers = ["https://" + server for server in servers]
            return self.dbapi.connect(servers=servers, **kwargs)
        return self.dbapi.connect(**kwargs)

    def _get_default_schema_name(self, connection):
        return 'doc'

    def _get_server_version_info(self, connection):
        return tuple(connection.connection.lowest_server_version.version)

    @classmethod
    def import_dbapi(cls):
        from crate import client
        return client

    @classmethod
    def dbapi(cls):
        return cls.import_dbapi()

    def has_schema(self, connection, schema, **kw):
        return schema in self.get_schema_names(connection, **kw)

    def has_table(self, connection, table_name, schema=None, **kw):
        return table_name in self.get_table_names(connection, schema=schema, **kw)

    @reflection.cache
    def get_schema_names(self, connection, **kw):
        cursor = connection.exec_driver_sql(
            "select schema_name "
            "from information_schema.schemata "
            "order by schema_name asc"
        )
        return [row[0] for row in cursor.fetchall()]

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        cursor = connection.exec_driver_sql(
            "SELECT table_name FROM information_schema.tables "
            "WHERE {0} = ? "
            "AND table_type = 'BASE TABLE' "
            "ORDER BY table_name ASC, {0} ASC".format(self.schema_column),
            (schema or self.default_schema_name, )
        )
        return [row[0] for row in cursor.fetchall()]

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        cursor = connection.exec_driver_sql(
            "SELECT table_name FROM information_schema.views "
            "ORDER BY table_name ASC, {0} ASC".format(self.schema_column),
            (schema or self.default_schema_name, )
        )
        return [row[0] for row in cursor.fetchall()]

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):
        query = "SELECT column_name, data_type " \
                "FROM information_schema.columns " \
                "WHERE table_name = ? AND {0} = ? " \
                "AND column_name !~ ?" \
                .format(self.schema_column)
        cursor = connection.exec_driver_sql(
            query,
            (table_name,
             schema or self.default_schema_name,
             r"(.*)\[\'(.*)\'\]")  # regex to filter subscript
        )
        return [self._create_column_info(row) for row in cursor.fetchall()]

    @reflection.cache
    def get_pk_constraint(self, engine, table_name, schema=None, **kw):
        if self.server_version_info >= (3, 0, 0):
            query = """SELECT column_name
                    FROM information_schema.key_column_usage
                    WHERE table_name = ? AND table_schema = ?"""

            def result_fun(result):
                rows = result.fetchall()
                return set(map(lambda el: el[0], rows))

        elif self.server_version_info >= (2, 3, 0):
            query = """SELECT column_name
                    FROM information_schema.key_column_usage
                    WHERE table_name = ? AND table_catalog = ?"""

            def result_fun(result):
                rows = result.fetchall()
                return set(map(lambda el: el[0], rows))

        else:
            query = """SELECT constraint_name
                   FROM information_schema.table_constraints
                   WHERE table_name = ? AND {schema_col} = ?
                   AND constraint_type='PRIMARY_KEY'
                   """.format(schema_col=self.schema_column)

            def result_fun(result):
                rows = result.fetchone()
                return set(rows[0] if rows else [])

        pk_result = engine.exec_driver_sql(
            query,
            (table_name, schema or self.default_schema_name)
        )
        pks = result_fun(pk_result)
        return {'constrained_columns': pks,
                'name': 'PRIMARY KEY'}

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None,
                         postgresql_ignore_search_path=False, **kw):
        # Crate doesn't support Foreign Keys, so this stays empty
        return []

    @reflection.cache
    def get_indexes(self, connection, table_name, schema, **kw):
        return []

    @property
    def schema_column(self):
        return "table_schema"

    def _create_column_info(self, row):
        return {
            'name': row[0],
            'type': self._resolve_type(row[1]),
            # In Crate every column is nullable except PK
            # Primary Key Constraints are not nullable anyway, no matter what
            # we return here, so it's fine to return always `True`
            'nullable': True
        }

    def _resolve_type(self, type_):
        return TYPES_MAP.get(type_, sqltypes.UserDefinedType)


class DateTrunc(functions.GenericFunction):
    name = "date_trunc"
    type = sqltypes.TIMESTAMP
