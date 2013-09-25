
from sqlalchemy.sql.compiler import SQLCompiler


class CrateCompiler(SQLCompiler):

    def visit_getitem_binary(self, binary, operator, **kw):
        return "{0}['{1}']".format(
            self.process(binary.left, **kw),
            binary.right.value
        )
