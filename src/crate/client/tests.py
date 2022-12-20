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
from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl
import time
import threading
import logging

import stopit

from crate.testing.layer import CrateLayer
from crate.testing.settings import \
    crate_host, crate_path, crate_port, \
    crate_transport_port, docs_path, localhost
from crate.client import connect

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

log = logging.getLogger('crate.testing.layer')
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
log.addHandler(ch)


def cprint(s):
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    print(s)


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
                                 host=localhost,
                                 transport_port=crate_transport_port,
                                 settings=settings)
    return crate_layer


def setUpCrateLayerBaseline(test):
    test.globs['crate_host'] = crate_host
    test.globs['pprint'] = pprint
    test.globs['print'] = cprint

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

        cursor.close()


def setUpCrateLayerSqlAlchemy(test):
    """
    Setup tables and views needed for SQLAlchemy tests.
    """
    setUpCrateLayerBaseline(test)

    ddl_statements = [
        """
        CREATE TABLE characters (
            id STRING PRIMARY KEY,
            name STRING,
            quote STRING,
            details OBJECT,
            more_details ARRAY(OBJECT),
            INDEX name_ft USING fulltext(name) WITH (analyzer = 'english'),
            INDEX quote_ft USING fulltext(quote) WITH (analyzer = 'english')
            )""",
        """
        CREATE VIEW characters_view
            AS SELECT * FROM characters
        """,
        """
        CREATE TABLE cities (
            name STRING PRIMARY KEY,
            coordinate GEO_POINT,
            area GEO_SHAPE
        )"""
    ]
    _execute_statements(ddl_statements, on_error="raise")


def tearDownDropEntitiesBaseline(test):
    """
    Drop all tables, views, and users created by `setUpWithCrateLayer*`.
    """
    ddl_statements = [
        "DROP TABLE locations",
        "DROP BLOB TABLE myfiles",
        "DROP USER me",
        "DROP USER trusted_me",
    ]
    _execute_statements(ddl_statements)


def tearDownDropEntitiesSqlAlchemy(test):
    """
    Drop all tables, views, and users created by `setUpWithCrateLayer*`.
    """
    tearDownDropEntitiesBaseline(test)
    ddl_statements = [
        "DROP TABLE characters",
        "DROP VIEW characters_view",
        "DROP TABLE cities",
    ]
    _execute_statements(ddl_statements)


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


def _execute_statements(statements, on_error="ignore"):
    with connect(crate_host) as conn:
        cursor = conn.cursor()
        for stmt in statements:
            _execute_statement(cursor, stmt, on_error=on_error)
        cursor.close()


def _execute_statement(cursor, stmt, on_error="ignore"):
    try:
        cursor.execute(stmt)
    except Exception:  # pragma: no cover
        # FIXME: Why does this croak on statements like ``DROP TABLE cities``?
        # Note: When needing to debug the test environment, you may want to
        #       enable this logger statement.
        # log.exception("Executing SQL statement failed")
        if on_error == "ignore":
            pass
        elif on_error == "raise":
            raise


def test_suite():
    suite = unittest.TestSuite()
    flags = (doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)

    # Unit tests.
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
        'docs/by-example/connection.rst',
        'docs/by-example/cursor.rst',
        module_relative=False,
        optionflags=flags,
        encoding='utf-8'
    )
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'docs/by-example/https.rst',
        module_relative=False,
        setUp=setUpWithHttps,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = HttpsTestServerLayer()
    suite.addTest(s)

    # Integration tests.
    s = doctest.DocFileSuite(
        'docs/by-example/http.rst',
        'docs/by-example/client.rst',
        'docs/by-example/blob.rst',
        module_relative=False,
        setUp=setUpCrateLayerBaseline,
        tearDown=tearDownDropEntitiesBaseline,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = ensure_cratedb_layer()
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'docs/by-example/sqlalchemy/getting-started.rst',
        'docs/by-example/sqlalchemy/crud.rst',
        'docs/by-example/sqlalchemy/working-with-types.rst',
        'docs/by-example/sqlalchemy/advanced-querying.rst',
        'docs/by-example/sqlalchemy/inspection-reflection.rst',
        module_relative=False,
        setUp=setUpCrateLayerSqlAlchemy,
        tearDown=tearDownDropEntitiesSqlAlchemy,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = ensure_cratedb_layer()
    suite.addTest(s)

    return suite
