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

from .compat.api13 import monkeypatch_add_exec_driver_sql
from .dialect import CrateDialect
from .sa_version import SA_1_4, SA_VERSION


if SA_VERSION < SA_1_4:
    import textwrap
    import warnings

    # SQLAlchemy 1.3 is effectively EOL.
    SA13_DEPRECATION_WARNING = textwrap.dedent("""
    WARNING: SQLAlchemy 1.3 is effectively EOL.

    SQLAlchemy 1.3 is EOL since 2023-01-27.
    Future versions of the CrateDB SQLAlchemy dialect will drop support for SQLAlchemy 1.3.
    It is recommended that you transition to using SQLAlchemy 1.4 or 2.0:

    - https://docs.sqlalchemy.org/en/14/changelog/migration_14.html
    - https://docs.sqlalchemy.org/en/20/changelog/migration_20.html
    """.lstrip("\n"))
    warnings.warn(message=SA13_DEPRECATION_WARNING, category=DeprecationWarning)

    # SQLAlchemy 1.3 does not have the `exec_driver_sql` method, so add it.
    monkeypatch_add_exec_driver_sql()


__all__ = [
    CrateDialect,
]
