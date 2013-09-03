import unittest
import doctest


class ClientMocked(object):

    def __init__(self):
        self.response = {}

    def sql(self, stmt=None):
        return self.response

    def set_next_response(self, response):
        self.response = response


def setUp(test):
    test.globs['connection_client'] = ClientMocked()


def test_suite():
    suite = unittest.TestSuite()

    s = doctest.DocFileSuite('cursor.txt',
                             'connection.txt',
                             setUp=setUp,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                             doctest.ELLIPSIS)
    suite.addTest(s)
    return suite
