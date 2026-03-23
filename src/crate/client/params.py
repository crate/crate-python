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
import re
import typing as t

from .exceptions import ProgrammingError

_NAMED_PARAM_RE = re.compile(r"%\((\w+)\)s")


def convert_named_to_positional(
    sql: str, params: t.Dict[str, t.Any]
) -> t.Tuple[str, t.List[t.Any]]:
    """Convert pyformat-style named parameters to positional qmark parameters.

    Converts ``%(name)s`` placeholders to ``?`` and returns an ordered list
    of corresponding values extracted from ``params``.

    The same name may appear multiple times; each occurrence appends the
    value to the positional list independently.

    Raises ``ProgrammingError`` if a placeholder name is absent from ``params``.
    Extra keys in ``params`` are silently ignored.

    Example::

        sql = "SELECT * FROM t WHERE a = %(a)s AND b = %(b)s"
        params = {"a": 1, "b": 2}
        # returns: ("SELECT * FROM t WHERE a = ? AND b = ?", [1, 2])
    """
    positional: t.List[t.Any] = []

    def _replace(match: "re.Match[str]") -> str:
        name = match.group(1)
        if name not in params:
            raise ProgrammingError(
                f"Named parameter '{name}' not found in the parameters dict"
            )
        positional.append(params[name])
        return "?"

    converted_sql = _NAMED_PARAM_RE.sub(_replace, sql)
    return converted_sql, positional
