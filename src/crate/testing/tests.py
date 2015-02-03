import unittest
import doctest
import os


def docs_path(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), *parts)


def crate_path(*parts):
    return os.path.abspath(docs_path('..', '..', 'parts', 'crate', *parts))

def public_ip():
    import socket
    return socket.gethostbyname(socket.gethostname())

def setUp(test):
    test.globs['crate_path'] = crate_path
    test.globs['public_ip'] = public_ip()

def test_suite():
    suite = unittest.TestSuite()

    s = doctest.DocFileSuite('layer.txt',
                             setUp=setUp,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                                         doctest.ELLIPSIS)
    suite.addTest(s)
    return suite
