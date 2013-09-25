
import sqlalchemy.types as sqltypes
from sqlalchemy.sql import operators


class Dict(sqltypes.UserDefinedType):

    class Comparator(sqltypes.TypeEngine.Comparator):

        def __getitem__(self, key):
            return self._binary_operate(self.expr, operators.getitem, key)

    type = dict
    comparator_factory = Comparator
