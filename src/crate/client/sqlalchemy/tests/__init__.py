# -*- coding: utf-8 -*-

from unittest import TestCase, TestSuite, makeSuite
from .connection_test import SqlAlchemyConnectionTest
from .dict_test import SqlAlchemyDictTypeTest
from .datetime_test import SqlAlchemyDateAndDateTimeTest


def test_suite():
    tests = TestSuite()
    tests.addTest(makeSuite(SqlAlchemyConnectionTest))
    tests.addTest(makeSuite(SqlAlchemyDictTypeTest))
    tests.addTest(makeSuite(SqlAlchemyDateAndDateTimeTest))
    return tests
