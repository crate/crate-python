import json
from pprint import pprint
import unittest
import doctest
import requests
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


def setUpMocked(test):
    test.globs['connection_client_mocked'] = ClientMocked()


crate_port = 9295
crate_layer =  CrateLayer('crate',
                    crate_home=crate_path(),
                    crate_exec=crate_path('bin', 'crate'),
                    port=crate_port,)

crate_host = "127.0.0.1:{port}".format(port=crate_port)
crate_uri = "http://%s" % crate_host

def setUpWithCrateLayer(test):
    test.globs['HttpClient'] = http.Client
    test.globs['crate_host'] = crate_host
    test.globs['pprint'] = pprint

    # load testing data into crate
    with open(docs_path('testing', 'cratesetup', 'mappings', 'test_a.json')) as s:
        requests.put('/'.join([crate_uri, 'locations']), data=json.loads(s.read()))
    with open(docs_path('testing', 'cratesetup', 'data', 'test_a.json')) as s:
        requests.post('/'.join([crate_uri, '_bulk']), data=(s.read()))
    # refresh index
    requests.post('/'.join([crate_uri, 'locations', '_refresh']))

def tearDownWithCrateLayer(test):
    # clear testing data

    requests.delete('/'.join([crate_uri, 'locations']))


def test_suite():
    suite = unittest.TestSuite()

    s = doctest.DocFileSuite('cursor.txt',
                             'connection.txt',
                             setUp=setUpMocked,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                             doctest.ELLIPSIS)
    suite.addTest(s)

    s = doctest.DocFileSuite('http.txt',
                             'index.txt',
                             setUp=setUpWithCrateLayer,
                             tearDown=tearDownWithCrateLayer,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                             doctest.ELLIPSIS)
    s.layer = crate_layer
    suite.addTest(s)

    return suite
