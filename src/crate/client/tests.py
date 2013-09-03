import unittest
import doctest
import os
import requests
import json
from crate.testing.layer import CrateLayer
from urlparse import urljoin


class Client(object):

    def __init__(self):
        self.response = {}

    def sql(self, stmt=None):
        return self.response


def docs_path(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), *parts)


def crate_path(*parts):
    return docs_path('..', '..', 'parts', 'crate', *parts)

empty_layer = CrateLayer('crate',
                         crate_home=crate_path(),
                         crate_exec=crate_path('bin', 'crate'),
                         port=9200,)


def setUp(test):
    host = 'http://127.0.0.1:9200'

    test.globs['client'] = Client()

    with open(docs_path('testing', 'cratesetup', 'mappings', 'test_a.json')) as s:
        requests.put(urljoin(host, 'locations'), data=json.loads(s.read()))
    with open(docs_path('testing', 'cratesetup', 'data', 'test_a.json')) as s:
        requests.post(urljoin(host, '_bulk'), data=(s.read()))


def test_suite():
    suite = unittest.TestSuite()

    s = doctest.DocFileSuite('cursor.txt',
                             setUp=setUp,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                             doctest.ELLIPSIS)
    s.layer = empty_layer
    suite.addTest(s)
    return suite
