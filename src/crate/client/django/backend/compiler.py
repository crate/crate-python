# -*- coding: utf-8 -*-

from django.db.models.sql import compiler


class SQLCompiler(compiler.SQLCompiler):

    def as_sql(self, with_limits=True, with_col_aliases=False):
        sql, params = super(SQLCompiler, self).as_sql(with_limits=with_limits, with_col_aliases=with_col_aliases)
        return sql.replace("%s", "?"), params


class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    pass


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    def as_sql(self):
        """
        hack for converting djangos arguments placeholders into question marks
        as crate-python uses dbapi option ``paramstyle=qmark`` which is not supported by
        django

        TODO: make a Pull Request for django to support this dbapi option
        :return: tuple of (<sql-statement>, <list of params>)
        """
        sql, params = super(SQLDeleteCompiler, self).as_sql()
        return sql.replace("%s", "?"), params


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    pass


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    pass


class SQLDateCompiler(compiler.SQLDateCompiler, SQLCompiler):
    pass


class SQLDateTimeCompiler(compiler.SQLDateTimeCompiler, SQLCompiler):
    pass
