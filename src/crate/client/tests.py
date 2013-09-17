import json
import unittest
from pprint import pprint
import doctest
import requests
import re
from crate.testing.layer import CrateLayer
from crate.testing.tests import crate_path, docs_path
from zope.testing.renormalizing import RENormalizing

from . import http
from .crash import CrateCmd


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
crate_layer = CrateLayer('crate',
                         crate_home=crate_path(),
                         crate_exec=crate_path('bin', 'crate'),
                         port=crate_port,)

crate_host = "127.0.0.1:{port}".format(port=crate_port)
crate_uri = "http://%s" % crate_host


def setUpWithCrateLayer(test):
    test.globs['HttpClient'] = http.Client
    test.globs['crate_host'] = crate_host
    test.globs['pprint'] = pprint
    test.globs['cmd'] = CrateCmd()

    # load testing data into crate
    with open(docs_path('testing', 'testdata', 'mappings', 'test_a.json')) as s:
        requests.put('/'.join([crate_uri, 'locations']), data=json.loads(s.read()))
    with open(docs_path('testing', 'testdata', 'data', 'test_a.json')) as s:
        requests.post('/'.join([crate_uri, '_bulk']), data=(s.read()))

    blob_idx_settings = {
        'number_of_shards': 1,
        'number_of_replicas': 0,
        'blobs': {
            'enabled': True
        }
    }
    requests.post('/'.join([crate_uri, 'myfiles']),
                  data=json.dumps(blob_idx_settings))
    # refresh index
    requests.post('/'.join([crate_uri, 'locations', '_refresh']))


def tearDownWithCrateLayer(test):
    # clear testing data
    requests.delete('/'.join([crate_uri, 'locations']))


def test_suite():
    suite = unittest.TestSuite()
    flags = (doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
    checker = RENormalizing([
        # python 3 drops the u" prefix on unicode strings
        (re.compile(r"u('[^']*')"), r"\1"),

        # python 3 includes module name in exceptions
        (re.compile(r"crate.client.exceptions.ProgrammingError:"),
         "ProgrammingError:"),
        (re.compile(r"crate.client.exceptions.ConnectionError:"),
         "ConnectionError:"),
    ])

    s = doctest.DocFileSuite(
        'cursor.txt',
        'connection.txt',
        checker=checker,
        setUp=setUpMocked,
        optionflags=flags
    )
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'http.txt',
        'index.txt',
        'blobs.txt',
        'crash.txt',
        checker=checker,
        setUp=setUpWithCrateLayer,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags
    )
    s.layer = crate_layer
    suite.addTest(s)

    return suite
