import unittest
import doctest
from crate.testing.layer import CrateLayer
import os
import urllib2
import json
from .core import Client

class Endpoint(object):
    def __init__(self, base='http://localhost:9200'):
        self.base = base

    def _req(self, path):
        url = self.base + path
        return urllib2.Request(url)

    def _exec_req(self, req):
        try:
            result = urllib2.urlopen(req)
            print(json.dumps(json.loads(result.read()), indent=4,
                             sort_keys=True))
        except urllib2.HTTPError as e:
            print(e)
            print(e.read())

    def get(self, path):
        req = self._req(path)
        self._exec_req(req)

    def post(self, path, data='', bulk=False):
        req = self._req(path)
        if bulk:
            body = data
        else:
            body = json.dumps(data)
        req.add_data(body)
        self._exec_req(req)

    def put(self, path, data=''):
        req = self._req(path)
        body = json.dumps(data)
        req.add_data(body)
        req.get_method = lambda: 'PUT'
        self._exec_req(req)

    def refresh(self):
        self.post("/_flush")
        self.post("/_refresh")


def docs_path(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), *parts)


def crate_path(*parts):
    return docs_path('..', '..', 'parts', 'crate', *parts)

empty_layer = CrateLayer('crate',
                         crate_home=crate_path(),
                         crate_exec=crate_path('bin', 'crate'),
                         port=9200,)


def setUp(test):
    test.globs['client'] = Client()
   
    '''
    ep = Endpoint()
    with open(docs_path('testing', 'cratesetup', 'mappings', 'test_a.json')) as s:
        ep.put('/locations', data=json.loads(s.read()))
    with open(docs_path('testing', 'cratesetup', 'data', 'test_a.json')) as s:
        ep.post('/_bulk', data=(s.read()), bulk=True)
    '''


def tearDown(test):
    print('tearDown')


def test_suite():
    suite = unittest.TestSuite()

    s = doctest.DocFileSuite('cursor.txt',
                             setUp=setUp,
                             tearDown=tearDown,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                             doctest.ELLIPSIS)
    #s.layer = empty_layer
    suite.addTest(s)
    return suite
