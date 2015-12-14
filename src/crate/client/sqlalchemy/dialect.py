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

from __future__ import absolute_import
import logging
from datetime import datetime, date

from sqlalchemy import types as sqltypes
from sqlalchemy.engine import default, reflection

from .compiler import (
    CrateCompiler,
    CrateCompilerV1,
    CrateTypeCompiler,
    CrateDDLCompiler
)
from crate.client.exceptions import TimezoneUnawareException

from .sa_version import SA_1_0

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


class CrateDialect(default.DefaultDialect):
    name = 'crate'
    statement_compiler = SA_1_0 and CrateCompilerV1 or CrateCompiler
    ddl_compiler = CrateDDLCompiler
    type_compiler = CrateTypeCompiler
    supports_native_boolean = True
    colspecs = colspecs

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
        if server:
            return self.dbapi.connect(servers=server, **kwargs)
        return self.dbapi.connect(**kwargs)

    def _get_default_schema_name(self, connection):
        return 'doc'

    def _get_server_version_info(self, connection):
        return tuple(connection.connection.lowest_server_version.version)

    @classmethod
    def dbapi(cls):
        from crate import client
        return client

    def has_schema(self, connection, schema):
        return schema in self.get_schema_names(connection)

    def has_table(self, connection, table_name, schema=None):
        return table_name in self.get_table_names(connection, schema=schema)

    @reflection.cache
    def get_schema_names(self, connection, **kw):
        cursor = connection.execute(
            "select schema_name "
            "from information_schema.schemata "
            "order by schema_name asc"
        )
        return [row[0] for row in cursor.fetchall()]

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        cursor = connection.execute(
            "select table_name from information_schema.tables "
            "where schema_name = ? "
            "order by table_name asc, schema_name asc",
            [schema or self.default_schema_name]
        )
        return [row[0] for row in cursor.fetchall()]
