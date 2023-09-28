# -*- coding: utf-8 -*-

from ..compat.api13 import monkeypatch_amend_select_sa14, monkeypatch_add_connectionfairy_driver_connection
from ..sa_version import SA_1_4, SA_VERSION
from ...test_util import ParametrizedTestCase

# `sql.select()` of SQLAlchemy 1.3 uses old calling semantics,
# but the test cases already need the modern ones.
if SA_VERSION < SA_1_4:
    monkeypatch_amend_select_sa14()
    monkeypatch_add_connectionfairy_driver_connection()

from unittest import TestLoader, TestSuite
from .connection_test import SqlAlchemyConnectionTest
from .dict_test import SqlAlchemyDictTypeTest
from .datetime_test import SqlAlchemyDateAndDateTimeTest
from .compiler_test import SqlAlchemyCompilerTest, SqlAlchemyDDLCompilerTest
from .update_test import SqlAlchemyUpdateTest
from .match_test import SqlAlchemyMatchTest
from .bulk_test import SqlAlchemyBulkTest
from .insert_from_select_test import SqlAlchemyInsertFromSelectTest
from .create_table_test import SqlAlchemyCreateTableTest
from .array_test import SqlAlchemyArrayTypeTest
from .dialect_test import SqlAlchemyDialectTest
from .function_test import SqlAlchemyFunctionTest
from .warnings_test import SqlAlchemyWarningsTest
from .query_caching import SqlAlchemyQueryCompilationCaching


makeSuite = TestLoader().loadTestsFromTestCase


def test_suite_unit():
    tests = TestSuite()
    tests.addTest(makeSuite(SqlAlchemyConnectionTest))
    tests.addTest(makeSuite(SqlAlchemyDictTypeTest))
    tests.addTest(makeSuite(SqlAlchemyDateAndDateTimeTest))
    tests.addTest(makeSuite(SqlAlchemyCompilerTest))
    tests.addTest(makeSuite(SqlAlchemyDDLCompilerTest))
    tests.addTest(ParametrizedTestCase.parametrize(SqlAlchemyCompilerTest, param={"server_version_info": None}))
    tests.addTest(ParametrizedTestCase.parametrize(SqlAlchemyCompilerTest, param={"server_version_info": (4, 0, 12)}))
    tests.addTest(ParametrizedTestCase.parametrize(SqlAlchemyCompilerTest, param={"server_version_info": (4, 1, 10)}))
    tests.addTest(makeSuite(SqlAlchemyUpdateTest))
    tests.addTest(makeSuite(SqlAlchemyMatchTest))
    tests.addTest(makeSuite(SqlAlchemyCreateTableTest))
    tests.addTest(makeSuite(SqlAlchemyBulkTest))
    tests.addTest(makeSuite(SqlAlchemyInsertFromSelectTest))
    tests.addTest(makeSuite(SqlAlchemyInsertFromSelectTest))
    tests.addTest(makeSuite(SqlAlchemyDialectTest))
    tests.addTest(makeSuite(SqlAlchemyFunctionTest))
    tests.addTest(makeSuite(SqlAlchemyArrayTypeTest))
    tests.addTest(makeSuite(SqlAlchemyWarningsTest))
    return tests


def test_suite_integration():
    tests = TestSuite()
    tests.addTest(makeSuite(SqlAlchemyQueryCompilationCaching))
    return tests
