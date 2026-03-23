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

import pytest

from crate.client.exceptions import ProgrammingError
from crate.client.params import convert_named_to_positional


def test_basic_conversion():
    """Named placeholders are replaced with ? and values are ordered."""
    sql, params = convert_named_to_positional(
        "SELECT * FROM t WHERE a = %(a)s AND b = %(b)s",
        {"a": 1, "b": 2},
    )
    assert sql == "SELECT * FROM t WHERE a = ? AND b = ?"
    assert params == [1, 2]


def test_repeated_param():
    """The same name appearing multiple times appends the value each time."""
    sql, params = convert_named_to_positional(
        "SELECT %(x)s, %(x)s",
        {"x": 42},
    )
    assert sql == "SELECT ?, ?"
    assert params == [42, 42]


def test_missing_param_raises():
    """A placeholder without a matching key raises ProgrammingError."""
    with pytest.raises(ProgrammingError, match="Named parameter 'z' not found"):
        convert_named_to_positional("SELECT %(z)s", {"a": 1})


def test_extra_params_ignored():
    """Extra keys in the params dict cause no error."""
    sql, params = convert_named_to_positional(
        "SELECT %(a)s",
        {"a": 10, "b": 99, "c": "unused"},
    )
    assert sql == "SELECT ?"
    assert params == [10]


def test_no_named_params():
    """SQL without %(...)s placeholders is returned unchanged."""
    sql, params = convert_named_to_positional(
        "SELECT * FROM t WHERE a = ?",
        {},
    )
    assert sql == "SELECT * FROM t WHERE a = ?"
    assert params == []


def test_various_value_types():
    """Different value types (str, int, float, None, bool) are handled."""
    sql, params = convert_named_to_positional(
        "INSERT INTO t VALUES (%(s)s, %(i)s, %(f)s, %(n)s, %(b)s)",
        {"s": "hello", "i": 7, "f": 3.14, "n": None, "b": True},
    )
    assert sql == "INSERT INTO t VALUES (?, ?, ?, ?, ?)"
    assert params == ["hello", 7, 3.14, None, True]


def test_preserves_surrounding_text():
    """Non-placeholder text in the SQL is not modified."""
    sql, params = convert_named_to_positional(
        "SELECT name FROM locations WHERE name = %(name)s ORDER BY name",
        {"name": "Algol"},
    )
    assert sql == "SELECT name FROM locations WHERE name = ? ORDER BY name"
    assert params == ["Algol"]
