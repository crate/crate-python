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
from six import iteritems


class Match(ColumnElement):

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
                       for k, v in iteritems(self.column)])
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
                       for k, v in iteritems(self.options)])
            )

            return "with ({0})".format(options)


def match(column, term, match_type=None, options=None):
    """Generates match predicate for fulltext search

    :param column: A reference to an index column or an existing column
     that is of type string and is indexed. It's also allowed to pass multiple
     columns and boosts as dict
    :param term: The term to search for. This string is analyzed
     and the resulting tokens are compared to the already indexed ones.
    :param match_type (optional): The match type determines how the query_term
     is applied and the _score is created
    :param options (optional): The match options further distinguish the way
     the matching process using a certain match type works.
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
