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
from sqlalchemy import Inspector
from sqlalchemy_postgresql_relaxed.asyncpg import PGDialect_asyncpg_relaxed
from sqlalchemy_postgresql_relaxed.base import PGDialect_relaxed
from sqlalchemy_postgresql_relaxed.psycopg import (
    PGDialect_psycopg_relaxed,
    PGDialectAsync_psycopg_relaxed,
)

from crate.client.sqlalchemy import CrateDialect


class CrateDialectPostgresAdapter(PGDialect_relaxed, CrateDialect):
    """
    Provide a CrateDialect on top of the relaxed PostgreSQL dialect.
    """

    inspector = Inspector

    # Need to manually override some methods because of polymorphic inheritance woes.
    # TODO: Investigate if this can be solved using metaprogramming or other techniques.
    has_schema = CrateDialect.has_schema
    has_table = CrateDialect.has_table
    get_schema_names = CrateDialect.get_schema_names
    get_table_names = CrateDialect.get_table_names
    get_view_names = CrateDialect.get_view_names
    get_columns = CrateDialect.get_columns
    get_pk_constraint = CrateDialect.get_pk_constraint
    get_foreign_keys = CrateDialect.get_foreign_keys
    get_indexes = CrateDialect.get_indexes

    get_multi_columns = CrateDialect.get_multi_columns
    get_multi_pk_constraint = CrateDialect.get_multi_pk_constraint
    get_multi_foreign_keys = CrateDialect.get_multi_foreign_keys

    # TODO: Those may want to go to CrateDialect instead?
    def get_multi_indexes(self, *args, **kwargs):
        return []

    def get_multi_unique_constraints(self, *args, **kwargs):
        return []

    def get_multi_check_constraints(self, *args, **kwargs):
        return []

    def get_multi_table_comment(self, *args, **kwargs):
        return []


class CrateDialect_psycopg(PGDialect_psycopg_relaxed, CrateDialectPostgresAdapter):
    driver = "psycopg"

    @classmethod
    def get_async_dialect_cls(cls, url):
        return CrateDialectAsync_psycopg

    @classmethod
    def import_dbapi(cls):
        import psycopg

        return psycopg


class CrateDialectAsync_psycopg(PGDialectAsync_psycopg_relaxed, CrateDialectPostgresAdapter):
    driver = "psycopg_async"
    is_async = True


class CrateDialect_asyncpg(PGDialect_asyncpg_relaxed, CrateDialectPostgresAdapter):
    driver = "asyncpg"

    # TODO: asyncpg may have `paramstyle="numeric_dollar"`. Review this!

    # TODO: AttributeError: module 'asyncpg' has no attribute 'paramstyle'
    """
    @classmethod
    def import_dbapi(cls):
        import asyncpg

        return asyncpg
    """


dialect_urllib3 = CrateDialect
dialect_psycopg = CrateDialect_psycopg
dialect_psycopg_async = CrateDialectAsync_psycopg
dialect_asyncpg = CrateDialect_asyncpg
