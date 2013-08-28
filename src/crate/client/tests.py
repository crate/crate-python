import unittest
import doctest
from crate.testing.layer import CrateLayer
import os


def docs_path(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), *parts)


def crate_path(*parts):
    return docs_path('..', '..', 'parts', 'crate', *parts)


empty_layer = CrateLayer('crate',
                         crate_home=crate_path(),
                         crate_exec=crate_path('bin', 'crate'),
                         port=9200,)


def test_suite():
    suite = unittest.TestSuite()

    s = doctest.DocFileSuite('../../../docs/index.txt',
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                             doctest.ELLIPSIS)
    s.layer = empty_layer
    suite.addTest(s)
    return suite
