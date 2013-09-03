import json
from pprint import pprint
import unittest
import doctest
import requests
import time
from crate.testing.layer import CrateLayer
from crate.testing.tests import crate_path, docs_path

from . import http

class ClientMocked(object):

    def __init__(self):
        self.response = {}

    def sql(self, stmt=None):
        return self.response

    def set_next_response(self, response):
        self.response = response


def setUp(test):
    test.globs['connection_client'] = ClientMocked()


crate_port = 9295
crate_layer =  CrateLayer('crate',
                    crate_home=crate_path(),
                    crate_exec=crate_path('bin', 'crate'),
                    port=crate_port,)

crate_host = "http://127.0.0.1:{port}".format(port=crate_port)

def setUpWithCrateLayer(test):
    test.globs['HttpClient'] = http.Client
    test.globs['crate_port'] = crate_port
    test.globs['pprint'] = pprint

    # load testing data into crate
    with open(docs_path('testing', 'cratesetup', 'mappings', 'test_a.json')) as s:
        requests.put('/'.join([crate_host, 'locations']), data=json.loads(s.read()))
    with open(docs_path('testing', 'cratesetup', 'data', 'test_a.json')) as s:
        requests.post('/'.join([crate_host, '_bulk']), data=(s.read()))

    # wait a little for data indexing
    time.sleep(1)

def tearDownWithCrateLayer(test):
    # clear testing data
    requests.delete('/'.join([crate_host, 'locations']))

def test_suite():
    suite = unittest.TestSuite()

    s = doctest.DocFileSuite('cursor.txt',
                             'connection.txt',
                             setUp=setUp,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                             doctest.ELLIPSIS)
    suite.addTest(s)

    s = doctest.DocFileSuite('http.txt',
                             setUp=setUpWithCrateLayer,
                             tearDown=tearDownWithCrateLayer,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                             doctest.ELLIPSIS)
    s.layer = crate_layer
    suite.addTest(s)

    return suite
