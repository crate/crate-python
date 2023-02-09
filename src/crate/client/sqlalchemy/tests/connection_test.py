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

from unittest import TestCase
import sqlalchemy as sa
from sqlalchemy.exc import NoSuchModuleError


class SqlAlchemyConnectionTest(TestCase):

    def test_connection_server_uri_unknown_sa_plugin(self):
        with self.assertRaises(NoSuchModuleError):
            sa.create_engine("foobar://otherhost:19201")

    def test_default_connection(self):
        engine = sa.create_engine('crate://')
        conn = engine.raw_connection()
        self.assertEqual("<Connection <Client ['http://127.0.0.1:4200']>>",
                         repr(conn.driver_connection))
        conn.close()
        engine.dispose()

    def test_connection_server_uri_http(self):
        engine = sa.create_engine(
            "crate://otherhost:19201")
        conn = engine.raw_connection()
        self.assertEqual("<Connection <Client ['http://otherhost:19201']>>",
                         repr(conn.driver_connection))
        conn.close()
        engine.dispose()

    def test_connection_server_uri_https(self):
        engine = sa.create_engine(
            "crate://otherhost:19201/?ssl=true")
        conn = engine.raw_connection()
        self.assertEqual("<Connection <Client ['https://otherhost:19201']>>",
                         repr(conn.driver_connection))
        conn.close()
        engine.dispose()

    def test_connection_server_uri_invalid_port(self):
        with self.assertRaises(ValueError) as context:
            sa.create_engine("crate://foo:bar")
        self.assertIn("invalid literal for int() with base 10: 'bar'", str(context.exception))

    def test_connection_server_uri_https_with_trusted_user(self):
        engine = sa.create_engine(
            "crate://foo@otherhost:19201/?ssl=true")
        conn = engine.raw_connection()
        self.assertEqual("<Connection <Client ['https://otherhost:19201']>>",
                         repr(conn.driver_connection))
        self.assertEqual(conn.driver_connection.client.username, "foo")
        self.assertEqual(conn.driver_connection.client.password, None)
        conn.close()
        engine.dispose()

    def test_connection_server_uri_https_with_credentials(self):
        engine = sa.create_engine(
            "crate://foo:bar@otherhost:19201/?ssl=true")
        conn = engine.raw_connection()
        self.assertEqual("<Connection <Client ['https://otherhost:19201']>>",
                         repr(conn.driver_connection))
        self.assertEqual(conn.driver_connection.client.username, "foo")
        self.assertEqual(conn.driver_connection.client.password, "bar")
        conn.close()
        engine.dispose()

    def test_connection_multiple_server_http(self):
        engine = sa.create_engine(
            "crate://", connect_args={
                'servers': ['localhost:4201', 'localhost:4202']
            }
        )
        conn = engine.raw_connection()
        self.assertEqual(
            "<Connection <Client ['http://localhost:4201', " +
            "'http://localhost:4202']>>",
            repr(conn.driver_connection))
        conn.close()
        engine.dispose()

    def test_connection_multiple_server_https(self):
        engine = sa.create_engine(
            "crate://", connect_args={
                'servers': ['localhost:4201', 'localhost:4202'],
                'ssl': True,
            }
        )
        conn = engine.raw_connection()
        self.assertEqual(
            "<Connection <Client ['https://localhost:4201', " +
            "'https://localhost:4202']>>",
            repr(conn.driver_connection))
        conn.close()
        engine.dispose()
