from sqlalchemy.sql.expression import ColumnElement
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
            column = ', '.join(sorted(["{0} {1}".format(compiler.process(k), v) for k, v in iteritems(self.column
                                                                                                     )]))
            return "({0})".format(column)
        else:
            return "{0}".format(compiler.process(self.column))

    def compile_using(self, compiler):
        if self.match_type:
            using = "using {0}".format(self.match_type)
            with_clause = self.with_clause()
            if with_clause:
                using = ' '.join([using, with_clause])
            return using
        if self.options:
            raise ValueError("missing match_type. "
                             "It's not allowed to specify options without match_type")

    def with_clause(self):
        if self.options:
            options = ', '.join(sorted(["{0}={1}".format(k, v) for k, v in iteritems(self.options)]))

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
    :param options (optional): The match options further distinguish the way the
     matching process using a certain match type works.
    """
    return Match(column, term, match_type, options)


@compiles(Match)
def compile_match(match, compiler, **kwargs):
    func = "match(%s, '%s')" % (
        match.compile_column(compiler),
        match.term
    )
    using = match.compile_using(compiler)
    if using:
        func = ' '.join([func, using])
    return func
