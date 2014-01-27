from __future__ import absolute_import

import json
import unittest
import doctest
import re
from pprint import pprint
from datetime import datetime, date

import requests
from zope.testing.renormalizing import RENormalizing
import zc.customdoctests

from crate.testing.layer import CrateLayer
from crate.testing.tests import crate_path, docs_path
from crate.client import connect

from . import http
from .crash import CrateCmd
from .test_cursor import CursorTest
from .test_http import HttpClientTest, ThreadSafeHttpClientTest, KeepAliveClientTest
from .sqlalchemy.test import tests as sqlalchemy_tests
from .sqlalchemy.types import ObjectArray
from .compat import cprint


def crash_transform(s):
    return 'cmd.onecmd("""{0}""");'.format(s.strip())


crash_parser = zc.customdoctests.DocTestParser(
    ps1='cr>', comment_prefix='#', transform=crash_transform)


class ClientMocked(object):
    def __init__(self):
        self.response = {}

    def sql(self, stmt=None, parameters=None):
        return self.response

    def set_next_response(self, response):
        self.response = response


def setUpMocked(test):
    test.globs['connection_client_mocked'] = ClientMocked()


crate_port = 44209
crate_transport_port = 44309
crate_layer = CrateLayer('crate',
                         crate_home=crate_path(),
                         crate_exec=crate_path('bin', 'crate'),
                         port=crate_port,
                         transport_port=crate_transport_port)

crate_host = "127.0.0.1:{port}".format(port=crate_port)
crate_uri = "http://%s" % crate_host


def setUpWithCrateLayer(test):
    test.globs['HttpClient'] = http.Client
    test.globs['crate_host'] = crate_host
    test.globs['pprint'] = pprint
    test.globs['cmd'] = CrateCmd()
    test.globs['print'] = cprint

    conn = connect(crate_host)
    cursor = conn.cursor()

    with open(docs_path('testing/testdata/mappings/locations.sql')) as s:
        stmt = s.read()
        cursor.execute(stmt)
        stmt = ("select count(*) from information_schema.tables "
                "where table_name = 'locations'")
        cursor.execute(stmt)
        assert cursor.fetchall()[0][0] == 1

    data_path = docs_path('testing/testdata/data/test_a.json')
    # load testing data into crate
    cursor.execute("copy locations from ?", (data_path,))

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
    import sqlalchemy as sa
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    data = {
        "settings": {
            "mapper": {
                "dynamic": True
            }
        },
        "mappings": {
            "default": {
                "_meta": {
                    "primary_keys": "id"
                },
                "properties": {
                    "id": {
                        "type": "string",
                        "index": "not_analyzed"
                    }
                }
            }
        }
    }
    requests.put('{0}/characters'.format(crate_uri), data=json.dumps(data))

    engine = sa.create_engine('crate://{0}'.format(crate_host))
    Base = declarative_base()

    class Location(Base):
        __tablename__ = 'locations'
        name = sa.Column(sa.String, primary_key=True)
        kind = sa.Column(sa.String)
        date = sa.Column(sa.Date, default=date.today)
        datetime = sa.Column(sa.DateTime, default=datetime.utcnow)
        nullable_datetime = sa.Column(sa.DateTime)
        nullable_date = sa.Column(sa.Date)
        flag = sa.Column(sa.Boolean)
        details = sa.Column(ObjectArray)

    Session = sessionmaker(engine)
    session = Session()
    test.globs['sa'] = sa
    test.globs['engine'] = engine
    test.globs['Location'] = Location
    test.globs['Base'] = Base
    test.globs['session'] = session
    test.globs['Session'] = Session


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
        (re.compile(r"crate.client.exceptions.BlobsDisabledException:"),
         "BlobsDisabledException:"),
        (re.compile(r"<type "),
         "<class "),
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
    suite.addTest(unittest.makeSuite(KeepAliveClientTest))
    suite.addTest(unittest.makeSuite(ThreadSafeHttpClientTest))
    suite.addTest(sqlalchemy_tests)
    suite.addTest(doctest.DocTestSuite('crate.client.connection'))
    suite.addTest(doctest.DocTestSuite('crate.client.http'))

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
        checker=checker,
        setUp=setUpWithCrateLayer,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags
    )
    s.layer = crate_layer
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'crash.txt',
        checker=checker,
        setUp=setUpWithCrateLayer,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags,
        parser=crash_parser
    )
    s.layer = crate_layer
    suite.addTest(s)

    s = doctest.DocFileSuite(
        '../../../docs/sqlalchemy.txt',
        checker=checker,
        setUp=setUpCrateLayerAndSqlAlchemy,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags
    )
    s.layer = crate_layer
    suite.addTest(s)

    return suite
