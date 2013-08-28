import unittest
import doctest


def test_suite():
    return unittest.TestSuite([
        doctest.DocFileSuite('../docs/index.txt',
                             optionflags=doctest.ELLIPSIS),
    ])
