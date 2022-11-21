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
import socket
import unittest
import doctest
from pprint import pprint
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl
import time
import threading
import logging

import stopit

from crate.testing.layer import CrateLayer
from crate.testing.tests import crate_path, docs_path
from crate.client import connect
from crate.client.sqlalchemy.dialect import CrateDialect
from crate.client.test_util import ClientMocked

from . import http
from .test_cursor import CursorTest
from .test_connection import ConnectionTest
from .test_http import (
    HttpClientTest,
    ThreadSafeHttpClientTest,
    KeepAliveClientTest,
    ParamsTest,
    RetryOnTimeoutServerTest,
    RequestsCaBundleTest,
    TestUsernameSentAsHeader,
    TestDefaultSchemaHeader,
)
from .sqlalchemy.tests import test_suite as sqlalchemy_test_suite
from .sqlalchemy.types import ObjectArray

log = logging.getLogger('crate.testing.layer')
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
log.addHandler(ch)


def cprint(s):
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    print(s)


def setUpMocked(test):
    test.globs['connection_client_mocked'] = ClientMocked()


settings = {
    'udc.enabled': 'false',
    'lang.js.enabled': 'true',
    'auth.host_based.enabled': 'true',
    'auth.host_based.config.0.user': 'crate',
    'auth.host_based.config.0.method': 'trust',
    'auth.host_based.config.98.user': 'trusted_me',
    'auth.host_based.config.98.method': 'trust',
    'auth.host_based.config.99.user': 'me',
    'auth.host_based.config.99.method': 'password',
}
crate_port = 44209
crate_transport_port = 44309
local = '127.0.0.1'
crate_host = "{host}:{port}".format(host=local, port=crate_port)
crate_uri = "http://%s" % crate_host
crate_layer = None


def ensure_cratedb_layer():
    """
    In order to skip individual tests by manually disabling them within
    `def test_suite()`, it is crucial make the test layer not run on each
    and every occasion. So, things like this will be possible::

        ./bin/test -vvvv --ignore_dir=testing

    TODO: Through a subsequent patch, the possibility to individually
          unselect specific tests might be added to `def test_suite()`
          on behalf of environment variables.
          A blueprint for this kind of logic can be found at
          https://github.com/crate/crate/commit/414cd833.
    """
    global crate_layer

    if crate_layer is None:
        crate_layer = CrateLayer('crate',
                                 crate_home=crate_path(),
                                 port=crate_port,
                                 host=local,
                                 transport_port=crate_transport_port,
                                 settings=settings)
    return crate_layer


def refresh(table):
    with connect(crate_host) as conn:
        cursor = conn.cursor()
        cursor.execute("refresh table %s" % table)


def setUpWithCrateLayer(test):
    test.globs['HttpClient'] = http.Client
    test.globs['crate_host'] = crate_host
    test.globs['pprint'] = pprint
    test.globs['print'] = cprint
    test.globs["refresh"] = refresh

    with connect(crate_host) as conn:
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
        # refresh location table so imported data is visible immediately
        cursor.execute("refresh table locations")
        # create blob table
        cursor.execute("create blob table myfiles clustered into 1 shards " +
                       "with (number_of_replicas=0)")
        # create users
        cursor.execute("CREATE USER me WITH (password = 'my_secret_pw')")
        cursor.execute("CREATE USER trusted_me")


def setUpCrateLayerAndSqlAlchemy(test):
    setUpWithCrateLayer(test)
    import sqlalchemy as sa
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    with connect(crate_host) as conn:
        cursor = conn.cursor()
        cursor.execute("""create table characters (
          id string primary key,
          name string,
          quote string,
          details object,
          more_details array(object),
          INDEX name_ft using fulltext(name) with (analyzer = 'english'),
          INDEX quote_ft using fulltext(quote) with (analyzer = 'english')
          )""")
        cursor.execute("CREATE VIEW characters_view AS SELECT * FROM characters")

    with connect(crate_host) as conn:
        cursor = conn.cursor()
        cursor.execute("""create table cities (
          name string primary key,
          coordinate geo_point,
          area geo_shape
    ) """)

    engine = sa.create_engine('crate://{0}'.format(crate_host))
    Base = declarative_base()

    class Location(Base):
        __tablename__ = 'locations'
        name = sa.Column(sa.String, primary_key=True)
        kind = sa.Column(sa.String)
        date = sa.Column(sa.Date, default=lambda: datetime.utcnow().date())
        datetime_tz = sa.Column(sa.DateTime, default=datetime.utcnow)
        datetime_notz = sa.Column(sa.DateTime, default=datetime.utcnow)
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


class HttpsTestServerLayer:
    PORT = 65534
    HOST = "localhost"
    CERT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                "pki/server_valid.pem"))
    CACERT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                  "pki/cacert_valid.pem"))

    __name__ = "httpsserver"
    __bases__ = tuple()

    class HttpsServer(HTTPServer):
        def get_request(self):

            # Prepare SSL context.
            context = ssl._create_unverified_context(
                protocol=ssl.PROTOCOL_TLS_SERVER,
                cert_reqs=ssl.CERT_OPTIONAL,
                check_hostname=False,
                purpose=ssl.Purpose.CLIENT_AUTH,
                certfile=HttpsTestServerLayer.CERT_FILE,
                keyfile=HttpsTestServerLayer.CERT_FILE,
                cafile=HttpsTestServerLayer.CACERT_FILE)

            # Set minimum protocol version, TLSv1 and TLSv1.1 are unsafe.
            context.minimum_version = ssl.TLSVersion.TLSv1_2

            # Wrap TLS encryption around socket.
            socket, client_address = HTTPServer.get_request(self)
            socket = context.wrap_socket(socket, server_side=True)

            return socket, client_address

    class HttpsHandler(BaseHTTPRequestHandler):

        payload = json.dumps({"name": "test", "status": 200, })

        def do_GET(self):
            self.send_response(200)
            payload = self.payload.encode('UTF-8')
            self.send_header("Content-Length", len(payload))
            self.send_header("Content-Type", "application/json; charset=UTF-8")
            self.end_headers()
            self.wfile.write(payload)

    def setUp(self):
        self.server = self.HttpsServer(
            (self.HOST, self.PORT),
            self.HttpsHandler
        )
        thread = threading.Thread(target=self.serve_forever)
        thread.daemon = True  # quit interpreter when only thread exists
        thread.start()
        self.waitForServer()

    def serve_forever(self):
        print("listening on", self.HOST, self.PORT)
        self.server.serve_forever()
        print("server stopped.")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def isUp(self):
        """
        Test if a host is up.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ex = s.connect_ex((self.HOST, self.PORT))
        s.close()
        return ex == 0

    def waitForServer(self, timeout=5):
        """
        Wait for the host to be available.
        """
        with stopit.ThreadingTimeout(timeout) as to_ctx_mgr:
            while True:
                if self.isUp():
                    break
                time.sleep(0.001)

        if not to_ctx_mgr:
            raise TimeoutError("Could not properly start embedded webserver "
                               "within {} seconds".format(timeout))


def setUpWithHttps(test):
    test.globs['HttpClient'] = http.Client
    test.globs['crate_host'] = "https://{0}:{1}".format(
        HttpsTestServerLayer.HOST, HttpsTestServerLayer.PORT
    )
    test.globs['pprint'] = pprint
    test.globs['print'] = cprint

    test.globs['cacert_valid'] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "pki/cacert_valid.pem")
    )
    test.globs['cacert_invalid'] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "pki/cacert_invalid.pem")
    )
    test.globs['clientcert_valid'] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "pki/client_valid.pem")
    )
    test.globs['clientcert_invalid'] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "pki/client_invalid.pem")
    )


def _try_execute(cursor, stmt):
    try:
        cursor.execute(stmt)
    except Exception:
        # FIXME: Why does this croak on statements like ``DROP TABLE cities``?
        # Note: When needing to debug the test environment, you may want to
        #       enable this logger statement.
        # log.exception("Executing SQL statement failed")
        pass


def tearDownWithCrateLayer(test):
    # clear testing data
    with connect(crate_host) as conn:
        for stmt in ["DROP TABLE locations",
                     "DROP BLOB TABLE myfiles",
                     "DROP TABLE characters",
                     "DROP VIEW characters_view",
                     "DROP TABLE cities",
                     "DROP USER me",
                     "DROP USER trusted_me",
                     ]:
            _try_execute(conn.cursor(), stmt)


def test_suite():
    suite = unittest.TestSuite()
    flags = (doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)

    s = doctest.DocFileSuite(
        'doctests/cursor.txt',
        'doctests/connection.txt',
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
    suite.addTest(unittest.makeSuite(TestUsernameSentAsHeader))
    suite.addTest(unittest.makeSuite(TestDefaultSchemaHeader))
    suite.addTest(sqlalchemy_test_suite())
    suite.addTest(doctest.DocTestSuite('crate.client.connection'))
    suite.addTest(doctest.DocTestSuite('crate.client.http'))

    s = doctest.DocFileSuite(
        'doctests/https.txt',
        setUp=setUpWithHttps,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = HttpsTestServerLayer()
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'sqlalchemy/doctests/itests.txt',
        'sqlalchemy/doctests/dialect.txt',
        'sqlalchemy/doctests/reflection.txt',
        setUp=setUpCrateLayerAndSqlAlchemy,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = ensure_cratedb_layer()
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'doctests/http.txt',
        'doctests/blob.txt',
        'doctests/client.txt',
        'doctests/mocking.txt',
        'doctests/blob.txt',
        setUp=setUpWithCrateLayer,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = ensure_cratedb_layer()
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'doctests/sqlalchemy.txt',
        setUp=setUpCrateLayerAndSqlAlchemy,
        tearDown=tearDownWithCrateLayer,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = ensure_cratedb_layer()
    suite.addTest(s)

    return suite
