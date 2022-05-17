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

from sqlalchemy.sql.expression import ColumnElement, literal
from sqlalchemy.ext.compiler import compiles


class Match(ColumnElement):
    inherit_cache = True

    def __init__(self, column, term, match_type=None, options=None):
        super(Match, self).__init__()
        self.column = column
        self.term = term
        self.match_type = match_type
        self.options = options

    def compile_column(self, compiler):
        if isinstance(self.column, dict):
            column = ', '.join(
                sorted(["{0} {1}".format(compiler.process(k), v)
                       for k, v in self.column.items()])
            )
            return "({0})".format(column)
        else:
            return "{0}".format(compiler.process(self.column))

    def compile_term(self, compiler):
        return compiler.process(literal(self.term))

    def compile_using(self, compiler):
        if self.match_type:
            using = "using {0}".format(self.match_type)
            with_clause = self.with_clause()
            if with_clause:
                using = ' '.join([using, with_clause])
            return using
        if self.options:
            raise ValueError("missing match_type. " +
                             "It's not allowed to specify options " +
                             "without match_type")

    def with_clause(self):
        if self.options:
            options = ', '.join(
                sorted(["{0}={1}".format(k, v)
                       for k, v in self.options.items()])
            )

            return "with ({0})".format(options)


def match(column, term, match_type=None, options=None):
    """Generates match predicate for fulltext search

    :param column: A reference to a column or an index, or a subcolumn, or a
     dictionary of subcolumns with boost values.

    :param term: The term to match against. This string is analyzed and the
     resulting tokens are compared to the index.

    :param match_type (optional): The match type. Determine how the term is
     applied and the score calculated.

    :param options (optional): The match options. Specify match type behaviour.
     (Not possible without a specified match type.) Match options must be
     supplied as a dictionary.
    """
    return Match(column, term, match_type, options)


@compiles(Match)
def compile_match(match, compiler, **kwargs):
    func = "match(%s, %s)" % (
        match.compile_column(compiler),
        match.compile_term(compiler)
    )
    using = match.compile_using(compiler)
    if using:
        func = ' '.join([func, using])
    return func
