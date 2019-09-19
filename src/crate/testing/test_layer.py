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

import os
import tempfile
from unittest import TestCase, mock
from io import BytesIO
from .layer import CrateLayer, prepend_http, http_url_from_host_port, wait_for_http_url


class LayerUtilsTest(TestCase):

    def test_prepend_http(self):
        host = prepend_http('localhost')
        self.assertEqual('http://localhost', host)
        host = prepend_http('http://localhost')
        self.assertEqual('http://localhost', host)
        host = prepend_http('https://localhost')
        self.assertEqual('https://localhost', host)
        host = prepend_http('http')
        self.assertEqual('http://http', host)

    def test_http_url(self):
        url = http_url_from_host_port(None, None)
        self.assertEqual(None, url)
        url = http_url_from_host_port('localhost', None)
        self.assertEqual(None, url)
        url = http_url_from_host_port(None, 4200)
        self.assertEqual(None, url)
        url = http_url_from_host_port('localhost', 4200)
        self.assertEqual('http://localhost:4200', url)
        url = http_url_from_host_port('https://crate', 4200)
        self.assertEqual('https://crate:4200', url)

    def test_wait_for_http(self):
        log = BytesIO(b'[i.c.p.h.CrateNettyHttpServerTransport] [crate] publish_address {127.0.0.1:4200}')
        addr = wait_for_http_url(log)
        self.assertEqual('http://127.0.0.1:4200', addr)
        log = BytesIO(b'[i.c.p.h.CrateNettyHttpServerTransport] [crate] publish_address {}')
        addr = wait_for_http_url(log=log, timeout=1)
        self.assertEqual(None, addr)

    @mock.patch.dict('os.environ', {}, clear=True)
    def test_java_home_env_not_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            layer = CrateLayer('java-home-test', tmpdir)
            # JAVA_HOME must not be set to `None`, since it would be interpreted as a
            # string 'None', and therefore intepreted as a path
            self.assertEqual(layer.env['JAVA_HOME'], '')

    @mock.patch.dict('os.environ', {}, clear=True)
    def test_java_home_env_set(self):
        java_home = '/usr/lib/jvm/java-11-openjdk-amd64'
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ['JAVA_HOME'] = java_home
            layer = CrateLayer('java-home-test', tmpdir)
            self.assertEqual(layer.env['JAVA_HOME'], java_home)

    @mock.patch.dict('os.environ', {}, clear=True)
    def test_java_home_env_override(self):
        java_11_home = '/usr/lib/jvm/java-11-openjdk-amd64'
        java_12_home = '/usr/lib/jvm/java-12-openjdk-amd64'
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ['JAVA_HOME'] = java_11_home
            layer = CrateLayer('java-home-test', tmpdir, env={'JAVA_HOME': java_12_home})
            self.assertEqual(layer.env['JAVA_HOME'], java_12_home)
