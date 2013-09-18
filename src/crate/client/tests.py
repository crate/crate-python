from __future__ import absolute_import

import json
import unittest
import doctest
import re
from pprint import pprint

import requests
from zope.testing.renormalizing import RENormalizing

from crate.testing.layer import CrateLayer
from crate.testing.tests import crate_path, docs_path
from . import http
from .crash import CrateCmd
from .test_cursor import CursorTest
from .test_http import HttpClientTest
from .sqlalchemy.test import SqlAlchemyTest
from .compat import cprint


class ClientMocked(object):
    def __init__(self):
        self.response = {}

    def sql(self, stmt=None, parameters=None):
        return self.response

    def set_next_response(self, response):
        self.response = response


def setUpMocked(test):
    test.globs['connection_client_mocked'] = ClientMocked()


crate_port = 9295
crate_layer = CrateLayer('crate',
                         crate_home=crate_path(),
                         crate_exec=crate_path('bin', 'crate'),
                         port=crate_port)

crate_host = "127.0.0.1:{port}".format(port=crate_port)
crate_uri = "http://%s" % crate_host


def setUpWithCrateLayer(test):
    test.globs['HttpClient'] = http.Client
    test.globs['crate_host'] = crate_host
    test.globs['pprint'] = pprint
    test.globs['cmd'] = CrateCmd()
    test.globs['print'] = cprint

    # load testing data into crate
    with open(docs_path('testing/testdata/mappings/test_a.json')) as s:
        data = {
            "mappings": json.loads(s.read()),
            "settings": {
                "number_of_replicas": 0
            }
        }
        resp = requests.put('/'.join([crate_uri, 'locations']),
                            data=json.dumps(data))
        assert resp.status_code == 200
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


def setUpCrateLayerAndSqlAlchemy(test):
    setUpWithCrateLayer(test)
    from sqlalchemy import create_engine, String, Column, desc
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    engine = create_engine('crate://{0}'.format(crate_host))
    Base = declarative_base()

    class Location(Base):
        __tablename__ = 'locations'
        name = Column(String, primary_key=True)
        kind = Column(String)

    Session = sessionmaker(engine)
    session = Session()
    test.globs['engine'] = engine
    test.globs['connection'] = engine.connect()
    test.globs['Location'] = Location
    test.globs['session'] = session
    test.globs['desc'] = desc


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
        (re.compile(r"crate.client.exceptions.DigestNotFoundException:"),
         "DigestNotFoundException:"),
    ])

    s = doctest.DocFileSuite(
        'cursor.txt',
        'connection.txt',
        checker=checker,
        setUp=setUpMocked,
        optionflags=flags
    )
    suite.addTest(s)
    suite.addTest(unittest.makeSuite(CursorTest))
    suite.addTest(unittest.makeSuite(HttpClientTest))
    suite.addTest(unittest.makeSuite(SqlAlchemyTest))
    suite.addTest(doctest.DocTestSuite('crate.client.connection'))

    s = doctest.DocFileSuite(
        'sqlalchemy/itests.txt',
        checker=checker,
        setUp=setUpCrateLayerAndSqlAlchemy,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags
    )
    s.layer = crate_layer
    suite.addTest(s)
    s = doctest.DocFileSuite(
        'http.txt',
        '../../../docs/client.txt',
        '../../../docs/advanced_usage.txt',
        '../../../docs/blobs.txt',
        'crash.txt',
        checker=checker,
        setUp=setUpWithCrateLayer,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags
    )
    s.layer = crate_layer
    suite.addTest(s)

    return suite
