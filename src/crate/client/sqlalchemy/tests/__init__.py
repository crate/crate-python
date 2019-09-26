# -*- coding: utf-8 -*-

from unittest import TestSuite, makeSuite
from .connection_test import SqlAlchemyConnectionTest
from .dict_test import SqlAlchemyDictTypeTest
from .datetime_test import SqlAlchemyDateAndDateTimeTest
from .compiler_test import SqlAlchemyCompilerTest
from .update_test import SqlAlchemyUpdateTest
from .match_test import SqlAlchemyMatchTest
from .bulk_test import SqlAlchemyBulkTest
from .insert_from_select_test import SqlAlchemyInsertFromSelectTest
from .create_table_test import CreateTableTest
from .array_test import SqlAlchemyArrayTypeTest
from .dialect_test import DialectTest
from .function_test import FunctionTest
from ..sa_version import SA_1_1, SA_VERSION


def test_suite():
    tests = TestSuite()
    tests.addTest(makeSuite(SqlAlchemyConnectionTest))
    tests.addTest(makeSuite(SqlAlchemyDictTypeTest))
    tests.addTest(makeSuite(SqlAlchemyDateAndDateTimeTest))
    tests.addTest(makeSuite(SqlAlchemyCompilerTest))
    tests.addTest(makeSuite(SqlAlchemyUpdateTest))
    tests.addTest(makeSuite(SqlAlchemyMatchTest))
    tests.addTest(makeSuite(CreateTableTest))
    tests.addTest(makeSuite(SqlAlchemyBulkTest))
    tests.addTest(makeSuite(SqlAlchemyInsertFromSelectTest))
    tests.addTest(makeSuite(SqlAlchemyInsertFromSelectTest))
    tests.addTest(makeSuite(DialectTest))
    tests.addTest(makeSuite(FunctionTest))
    if SA_VERSION >= SA_1_1:
        tests.addTest(makeSuite(SqlAlchemyArrayTypeTest))
    return tests
