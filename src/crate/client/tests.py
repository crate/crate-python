# -*- coding: utf-8; -*-
#
# Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  Crate licenses
# this file to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
# However, if you have executed another commercial license agreement
# with Crate these terms will supersede the license and you may use the
# software solely pursuant to the terms of the relevant commercial agreement.

from __future__ import absolute_import

import json
import os
import unittest
import doctest
import re
from pprint import pprint
from datetime import datetime, date
from six.moves.BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import ssl
import time
import threading
from .compat import to_bytes

from zope.testing.renormalizing import RENormalizing

from crate.testing.layer import CrateLayer
from crate.testing.tests import crate_path, docs_path
from crate.client import connect
from crate.client.sqlalchemy.dialect import CrateDialect

from . import http
from .test_cursor import CursorTest
from .test_connection import ConnectionTest
from .test_http import (
    HttpClientTest,
    ThreadSafeHttpClientTest,
    KeepAliveClientTest,
    ParamsTest,
    RetryOnTimeoutServerTest,
    RequestsCaBundleTest
)
from .sqlalchemy.tests import test_suite as sqlalchemy_test_suite
from .sqlalchemy.types import ObjectArray
from .compat import cprint


class ClientMocked(object):

    active_servers = ["http://localhost:4200"]

    def __init__(self):
        self.response = {}
        self._server_infos = ("http://localhost:4200", "my server", "0.42.0")

    def sql(self, stmt=None, parameters=None, bulk_parameters=None):
        return self.response

    def server_infos(self, server):
        return self._server_infos

    def set_next_response(self, response):
        self.response = response

    def set_next_server_infos(self, server, server_name, version):
        self._server_infos = (server, server_name, version)


def setUpMocked(test):
    test.globs['connection_client_mocked'] = ClientMocked()


crate_port = 44209
crate_transport_port = 44309
crate_layer = CrateLayer('crate',
                         crate_home=crate_path(),
                         port=crate_port,
                         transport_port=crate_transport_port)

crate_host = "127.0.0.1:{port}".format(port=crate_port)
crate_uri = "http://%s" % crate_host


def setUpWithCrateLayer(test):
    test.globs['HttpClient'] = http.Client
    test.globs['crate_host'] = crate_host
    test.globs['pprint'] = pprint
    test.globs['print'] = cprint

    conn = connect(crate_host)
    cursor = conn.cursor()

    def refresh(table):
        cursor.execute("refresh table %s" % table)
    test.globs["refresh"] = refresh

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
    # refresh location table so imported data is visible immediately
    refresh("locations")

    # create blob table
    cursor.execute("create blob table myfiles clustered into 1 shards " +
                   "with (number_of_replicas=0)")


def setUpCrateLayerAndSqlAlchemy(test):
    setUpWithCrateLayer(test)
    import sqlalchemy as sa
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    conn = connect(crate_host)
    cursor = conn.cursor()
    cursor.execute("""create table characters (
      id string primary key,
      name string,
      quote string,
      details object,
      more_details array(object),
      INDEX name_ft using fulltext(name) with (analyzer = 'english'),
      INDEX quote_ft using fulltext(quote) with (analyzer = 'english')
) """)
    conn.close()

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
    test.globs['CrateDialect'] = CrateDialect


_server = None


class HttpsTestServerLayer(object):
    PORT = 65534
    HOST = "localhost"
    CERT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                "test_https.pem"))

    __name__ = "httpsserver"
    __bases__ = tuple()

    class HttpsServer(HTTPServer):
        def get_request(self):
            socket, client_address = HTTPServer.get_request(self)
            socket = ssl.wrap_socket(socket,
                                     keyfile=HttpsTestServerLayer.CERT_FILE,
                                     certfile=HttpsTestServerLayer.CERT_FILE,
                                     cert_reqs=ssl.CERT_OPTIONAL,
                                     server_side=True)
            return socket, client_address

    class HttpsHandler(BaseHTTPRequestHandler):

        payload = json.dumps({"name": "test", "status": 200, })

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", len(self.payload))
            self.send_header("Content-Type", "application/json; charset=UTF-8")
            self.end_headers()
            self.wfile.write(to_bytes(self.payload, 'UTF-8'))
            return

    def __init__(self):
        self.server = self.HttpsServer(
            (self.HOST, self.PORT),
            self.HttpsHandler
        )

    def setUp(self):
        thread = threading.Thread(target=self.serve_forever)
        thread.daemon = True  # quit interpreter when only thread exists
        thread.start()
        time.sleep(1)

    def serve_forever(self):
        print("listening on", self.HOST, self.PORT)
        self.server.serve_forever()
        print("server stopped.")

    def tearDown(self):
        self.server.shutdown()


def setUpWithHttps(test):
    test.globs['HttpClient'] = http.Client
    test.globs['crate_host'] = "https://{0}:{1}".format(
        HttpsTestServerLayer.HOST, HttpsTestServerLayer.PORT
    )
    test.globs['invalid_ca_cert'] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "invalid_ca.pem")
    )
    test.globs['valid_ca_cert'] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "test_https_ca.pem")
    )
    test.globs['pprint'] = pprint
    test.globs['print'] = cprint


def tearDownWithCrateLayer(test):
    # clear testing data
    conn = connect(crate_host)
    cursor = conn.cursor()
    cursor.execute("drop table locations")
    cursor.execute("drop blob table myfiles")
    try:
        cursor.execute("drop table characters")
    except:
        pass


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
        optionflags=flags,
        encoding='utf-8'
    )
    suite.addTest(s)
    suite.addTest(unittest.makeSuite(CursorTest))
    suite.addTest(unittest.makeSuite(HttpClientTest))
    suite.addTest(unittest.makeSuite(KeepAliveClientTest))
    suite.addTest(unittest.makeSuite(ThreadSafeHttpClientTest))
    suite.addTest(unittest.makeSuite(ParamsTest))
    suite.addTest(unittest.makeSuite(ConnectionTest))
    suite.addTest(unittest.makeSuite(RetryOnTimeoutServerTest))
    suite.addTest(unittest.makeSuite(RequestsCaBundleTest))
    suite.addTest(sqlalchemy_test_suite())
    suite.addTest(doctest.DocTestSuite('crate.client.connection'))
    suite.addTest(doctest.DocTestSuite('crate.client.http'))

    s = doctest.DocFileSuite(
        '../../../docs/https.txt',
        checker=checker,
        setUp=setUpWithHttps,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = HttpsTestServerLayer()
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'sqlalchemy/itests.txt',
        'sqlalchemy/dialect.txt',
        checker=checker,
        setUp=setUpCrateLayerAndSqlAlchemy,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = crate_layer
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'http.txt',
        'blob.txt',
        '../../../docs/client.txt',
        '../../../docs/advanced_usage.txt',
        '../../../docs/blobs.txt',
        checker=checker,
        setUp=setUpWithCrateLayer,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = crate_layer
    suite.addTest(s)

    s = doctest.DocFileSuite(
        '../../../docs/sqlalchemy.txt',
        checker=checker,
        setUp=setUpCrateLayerAndSqlAlchemy,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = crate_layer
    suite.addTest(s)

    return suite
