import unittest
import doctest
import os


def docs_path(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), *parts)


def crate_path(*parts):
    return docs_path('..', '..', 'parts', 'crate', *parts)


def setUp(test):
    test.globs['crate_path'] = crate_path


def test_suite():
    suite = unittest.TestSuite()

    s = doctest.DocFileSuite('layer.txt',
                             setUp=setUp,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                                         doctest.ELLIPSIS)
    suite.addTest(s)
    return suite
