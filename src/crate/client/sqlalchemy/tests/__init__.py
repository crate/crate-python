# -*- coding: utf-8 -*-

from unittest import TestCase, TestSuite, makeSuite
from .connection_test import SqlAlchemyConnectionTest
from .dict_test import SqlAlchemyDictTypeTest
from .datetime_test import SqlAlchemyDateAndDateTimeTest
from .compiler_test import SqlAlchemyCompilerTest


def test_suite():
    tests = TestSuite()
    tests.addTest(makeSuite(SqlAlchemyConnectionTest))
    tests.addTest(makeSuite(SqlAlchemyDictTypeTest))
    tests.addTest(makeSuite(SqlAlchemyDateAndDateTimeTest))
    tests.addTest(makeSuite(SqlAlchemyCompilerTest))
    return tests
