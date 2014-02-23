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

from sqlalchemy.engine import default
from sqlalchemy import types as sqltypes

from .compiler import CrateCompiler
from crate.client.exceptions import TimezoneUnawareException


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
    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                assert isinstance(value, datetime)
                if value.tzinfo is not None:
                    raise TimezoneUnawareException("Timezone aware datetime objects are not supported")
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
    statement_compiler = CrateCompiler
    supports_native_boolean = True
    colspecs = colspecs

    def __init__(self, *args, **kwargs):
        super(CrateDialect, self).__init__(*args, **kwargs)

        # currently our sql parser doesn't support unquoted column names that
        # start with _. Adding it here causes sqlalchemy to quote such columns
        self.identifier_preparer.illegal_initial_characters.add('_')

    def initialize(self, connection):
        # the DefaultDialect issues some queries to test for unicode support in
        # the resutls. etc. -> don't need any of that.
        pass

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

    @classmethod
    def dbapi(cls):
        from crate import client
        return client
