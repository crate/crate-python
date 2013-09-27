
import sqlalchemy.types as sqltypes
from sqlalchemy.sql import operators
from sqlalchemy.ext.mutable import Mutable


class MutableDict(Mutable, dict):

    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __init__(self, initval=None):
        initval = initval or {}
        self._changed_keys = set()
        self._deleted_keys = set()
        dict.__init__(self, initval)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self._deleted_keys.discard(key)
        self._changed_keys.add(key)
        self.changed()

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._deleted_keys.add(key)
        self.changed()


class _Craty(sqltypes.UserDefinedType):

    class Comparator(sqltypes.TypeEngine.Comparator):

        def __getitem__(self, key):
            return self._binary_operate(self.expr, operators.getitem, key)

    type = MutableDict
    comparator_factory = Comparator


Craty = MutableDict.as_mutable(_Craty)
