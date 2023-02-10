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
import json
import os
import tempfile
import urllib
from crate.client._pep440 import Version
from unittest import TestCase, mock
from io import BytesIO

import urllib3

import crate
from .layer import CrateLayer, prepend_http, http_url_from_host_port, wait_for_http_url
from .settings import crate_path


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

    @mock.patch.object(crate.testing.layer, "_download_and_extract", lambda uri, directory: None)
    def test_layer_from_uri(self):
        """
        The CrateLayer can also be created by providing an URI that points to
        a CrateDB tarball.
        """
        with urllib.request.urlopen("https://crate.io/versions.json") as response:
            versions = json.loads(response.read().decode())
            version = versions["crate_testing"]

        self.assertGreaterEqual(Version(version), Version("4.5.0"))

        uri = "https://cdn.crate.io/downloads/releases/crate-{}.tar.gz".format(version)
        layer = CrateLayer.from_uri(uri, name="crate-by-uri", http_port=42203)
        self.assertIsInstance(layer, CrateLayer)

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


class LayerTest(TestCase):

    def test_basic(self):
        """
        This layer starts and stops a ``Crate`` instance on a given host, port,
        a given crate node name and, optionally, a given cluster name::
        """

        port = 44219
        transport_port = 44319

        layer = CrateLayer('crate',
                           crate_home=crate_path(),
                           host='127.0.0.1',
                           port=port,
                           transport_port=transport_port,
                           cluster_name='my_cluster'
                           )

        # The working directory is defined on layer instantiation.
        # It is sometimes required to know it before starting the layer.
        self.assertRegex(layer.wdPath(), r".+/crate_layer/crate")

        # Start the layer.
        layer.start()

        # The urls of the crate servers to be instantiated can be obtained
        # via `crate_servers`.
        self.assertEqual(layer.crate_servers, ["http://127.0.0.1:44219"])

        # Access the CrateDB instance on the HTTP interface.

        http = urllib3.PoolManager()

        stats_uri = "http://127.0.0.1:{0}/".format(port)
        response = http.request('GET', stats_uri)
        self.assertEqual(response.status, 200)

        # The layer can be shutdown using its `stop()` method.
        layer.stop()

    def test_dynamic_http_port(self):
        """
        It is also possible to define a port range instead of a static HTTP port for the layer.

        Crate will start with the first available port in the given range and the test
        layer obtains the chosen port from the startup logs of the Crate process.
        Note, that this feature requires a logging configuration with at least loglevel
        ``INFO`` on ``http``.
        """
        port = '44200-44299'
        layer = CrateLayer('crate', crate_home=crate_path(), port=port)
        layer.start()
        self.assertRegex(layer.crate_servers[0], r"http://127.0.0.1:442\d\d")
        layer.stop()

    def test_default_settings(self):
        """
        Starting a CrateDB layer leaving out optional parameters will apply the following
        defaults.

        The default http port is the first free port in the range of ``4200-4299``,
        the default transport port is the first free port in the range of ``4300-4399``,
        the host defaults to ``127.0.0.1``.

        The command to call is ``bin/crate`` inside the ``crate_home`` path.
        The default config file is ``config/crate.yml`` inside ``crate_home``.
        The default cluster name will be auto generated using the HTTP port.
        """
        layer = CrateLayer('crate_defaults', crate_home=crate_path())
        layer.start()
        self.assertEqual(layer.crate_servers[0], "http://127.0.0.1:4200")
        layer.stop()

    def test_additional_settings(self):
        """
        The ``Crate`` layer can be started with additional settings as well.
        Add a dictionary for keyword argument ``settings`` which contains your settings.
        Those additional setting will override settings given as keyword argument.

        The settings will be handed over to the ``Crate`` process with the ``-C`` flag.
        So the setting ``threadpool.bulk.queue_size: 100`` becomes
        the command line flag: ``-Cthreadpool.bulk.queue_size=100``::
        """
        layer = CrateLayer(
            'custom',
            crate_path(),
            port=44401,
            settings={
                "cluster.graceful_stop.min_availability": "none",
                "http.port": 44402
            }
        )
        layer.start()
        self.assertEqual(layer.crate_servers[0], "http://127.0.0.1:44402")
        self.assertIn("-Ccluster.graceful_stop.min_availability=none", layer.start_cmd)
        layer.stop()

    def test_verbosity(self):
        """
        The test layer hides the standard output of Crate per default. To increase the
        verbosity level the additional keyword argument ``verbose`` needs to be set
        to ``True``::
        """
        layer = CrateLayer('crate',
                           crate_home=crate_path(),
                           verbose=True)
        layer.start()
        self.assertTrue(layer.verbose)
        layer.stop()

    def test_environment_variables(self):
        """
        It is possible to provide environment variables for the ``Crate`` testing
        layer.
        """
        layer = CrateLayer('crate',
                           crate_home=crate_path(),
                           env={"CRATE_HEAP_SIZE": "300m"})

        layer.start()

        sql_uri = layer.crate_servers[0] + "/_sql"

        http = urllib3.PoolManager()
        response = http.urlopen('POST', sql_uri,
                                body='{"stmt": "select heap[\'max\'] from sys.nodes"}')
        json_response = json.loads(response.data.decode('utf-8'))

        self.assertEqual(json_response["rows"][0][0], 314572800)

        layer.stop()

    def test_cluster(self):
        """
        To start a cluster of ``Crate`` instances, give each instance the same
        ``cluster_name``. If you want to start instances on the same machine then
        use value ``_local_`` for ``host`` and give every node different ports::
        """
        cluster_layer1 = CrateLayer(
            'crate1',
            crate_path(),
            host='_local_',
            cluster_name='my_cluster',
        )
        cluster_layer2 = CrateLayer(
            'crate2',
            crate_path(),
            host='_local_',
            cluster_name='my_cluster',
            settings={"discovery.initial_state_timeout": "10s"}
        )

        # If we start both layers, they will, after a small amount of time, find each other
        # and form a cluster.
        cluster_layer1.start()
        cluster_layer2.start()

        # We can verify that by checking the number of nodes a node knows about.
        http = urllib3.PoolManager()

        def num_cluster_nodes(crate_layer):
            sql_uri = crate_layer.crate_servers[0] + "/_sql"
            response = http.urlopen('POST', sql_uri, body='{"stmt":"select count(*) from sys.nodes"}')
            json_response = json.loads(response.data.decode('utf-8'))
            return json_response["rows"][0][0]

        # We might have to wait a moment before the cluster is finally created.
        num_nodes = num_cluster_nodes(cluster_layer1)
        import time
        retries = 0
        while num_nodes < 2:  # pragma: no cover
            time.sleep(1)
            num_nodes = num_cluster_nodes(cluster_layer1)
            retries += 1
            if retries == 30:
                break
        self.assertEqual(num_nodes, 2)

        cluster_layer1.stop()
        cluster_layer2.stop()
