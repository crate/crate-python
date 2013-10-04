

import sqlalchemy as sa
from sqlalchemy.sql.compiler import SQLCompiler
from .types import MutableDict


def rewrite_update(clauseelement, multiparams, params):
    """ change the params to enable partial updates

    sqlalchemy by default only supports updates of complex types in the form of

        "col = ?", ({"x": 1, "y": 2}

    but crate supports

        "col['x'] = ?, col['y'] = ?", (1, 2)

    by using the `Craty` (`MutableDict`) type.
    The update statement is only rewritten if a item of the MutableDict was
    changed.
    """

    newmultiparams = []
    for params in multiparams:
        newparams = {}
        for key, val in params.items():
            if (
                not isinstance(val, MutableDict) or
                (not any(val._changed_keys) and not any(val._deleted_keys))
            ):
                newparams[key] = val
                continue

            for subkey, subval in val.items():
                if subkey in val._changed_keys:
                    newparams["{0}['{1}']".format(key, subkey)] = subval
            for subkey in val._deleted_keys:
                newparams["{0}['{1}']".format(key, subkey)] = None
        newmultiparams.append(newparams)
    multiparams = tuple(newmultiparams)
    clauseelement = clauseelement.values(multiparams[0])

    # use CrateCompiler specific visit_update
    clauseelement._crate_specific = True
    return clauseelement, multiparams, params


@sa.event.listens_for(sa.engine.Engine, "before_execute", retval=True)
def crate_before_execute(conn, clauseelement, multiparams, params):
    if isinstance(clauseelement, sa.sql.expression.Update):
        return rewrite_update(clauseelement, multiparams, params)
    return clauseelement, multiparams, params


class CrateCompiler(SQLCompiler):

    def visit_getitem_binary(self, binary, operator, **kw):
        return "{0}['{1}']".format(
            self.process(binary.left, **kw),
            binary.right.value
        )

    def visit_update(self, update_stmt, **kw):
        """ used to compile <sql.expression.Update> expressions

        only implements a subset of the SQLCompiler.visit_update method
        e.g. updating multiple tables is not supported.
        """

        if (
            not update_stmt.parameters
            and not hasattr(update_stmt, '_crate_specific')
        ):
            return super(CrateCompiler, self).visit_update(update_stmt, **kw)

        self.isupdate = True
        self.postfetch = []
        self.prefetch = []
        self.returning = []

        text = 'UPDATE '
        extra_froms = update_stmt._extra_froms
        table_text = self.update_tables_clause(update_stmt, update_stmt.table,
                                               extra_froms, **kw)
        text += table_text
        text += ' SET '

        set_clauses = []
        parameters = update_stmt.parameters
        self.__handle_regular_columns(update_stmt, parameters, set_clauses)

        for k, v in parameters.items():
            if '[' in k:
                bindparam = sa.sql.bindparam(k, v)
                set_clauses.append(k + ' = ' + self.process(bindparam))

        text += ', '.join(set_clauses)

        if update_stmt._whereclause is not None:
            text += ' WHERE ' + self.process(update_stmt._whereclause)

        return text

    def __handle_regular_columns(self, stmt, parameters, set_clauses):
        need_pks = self.isinsert and \
            not self.inline and \
            not stmt._returning

        implicit_returning = need_pks and \
            self.dialect.implicit_returning and \
            stmt.table.implicit_returning

        for c in stmt.table.columns:
            if c.key in parameters:
                value = parameters.pop(c.key)
                if sa.sql.expression._is_literal(value):
                    value = self._create_crud_bind_param(
                        c, value, required=value is sa.sql.compiler.REQUIRED,
                        name=c.key
                    )
                elif c.primary_key and implicit_returning:
                    self.returning.append(c)
                    value = self.process(value.self_group())
                else:
                    self.postfetch.append(c)
                    value = self.process(value.self_group())
                set_clauses.append(c._compiler_dispatch(self) + ' = ?')
