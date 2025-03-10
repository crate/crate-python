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
import logging
import socket
import ssl
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pprint import pprint

import stopit

from crate.client import connect
from crate.testing.layer import CrateLayer

from .settings import (
    assets_path,
    crate_host,
    crate_path,
    crate_port,
    crate_transport_port,
    localhost,
)

makeSuite = unittest.TestLoader().loadTestsFromTestCase

log = logging.getLogger("crate.testing.layer")
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
log.addHandler(ch)


def cprint(s):
    if isinstance(s, bytes):
        s = s.decode("utf-8")
    print(s)  # noqa: T201


settings = {
    "udc.enabled": "false",
    "lang.js.enabled": "true",
    "auth.host_based.enabled": "true",
    "auth.host_based.config.0.user": "crate",
    "auth.host_based.config.0.method": "trust",
    "auth.host_based.config.98.user": "trusted_me",
    "auth.host_based.config.98.method": "trust",
    "auth.host_based.config.99.user": "me",
    "auth.host_based.config.99.method": "password",
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
        crate_layer = CrateLayer(
            "crate",
            crate_home=crate_path(),
            port=crate_port,
            host=localhost,
            transport_port=crate_transport_port,
            settings=settings,
        )
    return crate_layer


def setUpCrateLayerBaseline(test):
    if hasattr(test, "globs"):
        test.globs["crate_host"] = crate_host
        test.globs["pprint"] = pprint
        test.globs["print"] = cprint

    with connect(crate_host) as conn:
        cursor = conn.cursor()

        with open(assets_path("mappings/locations.sql")) as s:
            stmt = s.read()
            cursor.execute(stmt)
            stmt = (
                "select count(*) from information_schema.tables "
                "where table_name = 'locations'"
            )
            cursor.execute(stmt)
            assert cursor.fetchall()[0][0] == 1  # noqa: S101

        data_path = assets_path("import/test_a.json")
        # load testing data into crate
        cursor.execute("copy locations from ?", (data_path,))
        # refresh location table so imported data is visible immediately
        cursor.execute("refresh table locations")
        # create blob table
        cursor.execute(
            "create blob table myfiles clustered into 1 shards "
            + "with (number_of_replicas=0)"
        )

        # create users
        cursor.execute("CREATE USER me WITH (password = 'my_secret_pw')")
        cursor.execute("CREATE USER trusted_me")

        cursor.close()


def tearDownDropEntitiesBaseline(test):
    """
    Drop all tables, views, and users created by `setUpWithCrateLayer*`.
    """
    ddl_statements = [
        "DROP TABLE foobar",
        "DROP TABLE locations",
        "DROP BLOB TABLE myfiles",
        "DROP USER me",
        "DROP USER trusted_me",
    ]
    _execute_statements(ddl_statements)


class HttpsTestServerLayer:
    PORT = 65534
    HOST = "localhost"
    CERT_FILE = assets_path("pki/server_valid.pem")
    CACERT_FILE = assets_path("pki/cacert_valid.pem")

    __name__ = "httpsserver"
    __bases__ = ()

    class HttpsServer(HTTPServer):
        def get_request(self):
            # Prepare SSL context.
            context = ssl._create_unverified_context(  # noqa: S323
                protocol=ssl.PROTOCOL_TLS_SERVER,
                cert_reqs=ssl.CERT_OPTIONAL,
                check_hostname=False,
                purpose=ssl.Purpose.CLIENT_AUTH,
                certfile=HttpsTestServerLayer.CERT_FILE,
                keyfile=HttpsTestServerLayer.CERT_FILE,
                cafile=HttpsTestServerLayer.CACERT_FILE,
            )  # noqa: S323

            # Set minimum protocol version, TLSv1 and TLSv1.1 are unsafe.
            context.minimum_version = ssl.TLSVersion.TLSv1_2

            # Wrap TLS encryption around socket.
            socket, client_address = HTTPServer.get_request(self)
            socket = context.wrap_socket(socket, server_side=True)

            return socket, client_address

    class HttpsHandler(BaseHTTPRequestHandler):
        payload = json.dumps(
            {
                "name": "test",
                "status": 200,
            }
        )

        def do_GET(self):
            self.send_response(200)
            payload = self.payload.encode("UTF-8")
            self.send_header("Content-Length", len(payload))
            self.send_header("Content-Type", "application/json; charset=UTF-8")
            self.end_headers()
            self.wfile.write(payload)

    def setUp(self):
        self.server = self.HttpsServer(
            (self.HOST, self.PORT), self.HttpsHandler
        )
        thread = threading.Thread(target=self.serve_forever)
        thread.daemon = True  # quit interpreter when only thread exists
        thread.start()
        self.waitForServer()

    def serve_forever(self):
        log.info("listening on", self.HOST, self.PORT)
        self.server.serve_forever()
        log.info("server stopped.")

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
            raise TimeoutError(
                "Could not properly start embedded webserver "
                "within {} seconds".format(timeout)
            )


def setUpWithHttps(test):
    test.globs["crate_host"] = "https://{0}:{1}".format(
        HttpsTestServerLayer.HOST, HttpsTestServerLayer.PORT
    )
    test.globs["pprint"] = pprint
    test.globs["print"] = cprint

    test.globs["cacert_valid"] = assets_path("pki/cacert_valid.pem")
    test.globs["cacert_invalid"] = assets_path("pki/cacert_invalid.pem")
    test.globs["clientcert_valid"] = assets_path("pki/client_valid.pem")
    test.globs["clientcert_invalid"] = assets_path("pki/client_invalid.pem")


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
        # FIXME: Why does this trip on statements like `DROP TABLE cities`?
        # Note: When needing to debug the test environment, you may want to
        #       enable this logger statement.
        # log.exception("Executing SQL statement failed")  # noqa: ERA001
        if on_error == "ignore":
            pass
        elif on_error == "raise":
            raise
