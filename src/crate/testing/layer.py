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
import sys
import time
import json
import logging
import urllib3
import tempfile
import shutil
import subprocess
from urllib3.exceptions import MaxRetryError

logger = logging.getLogger(__name__)


CRATE_CONFIG_ERROR = 'crate_config must point to a folder or to a file named "crate.yml"'


class CrateLayer(object):
    """
    this layer starts a crate server.
    """

    __bases__ = ()

    tmpdir = tempfile.gettempdir()
    wait_interval = 0.2
    conn_pool = urllib3.PoolManager(num_pools=1)

    def __init__(self,
                 name,
                 crate_home,
                 crate_config=None,
                 port=4200,
                 keepRunning=False,
                 transport_port=None,
                 crate_exec=None,
                 cluster_name=None,
                 host="localhost",
                 multicast=False,
                 settings=None):
        """
        :param name: layer name, is also used as the cluser name
        :param crate_home: path to home directory of the crate installation
        :param port: port on which crate should run
        :param keepRunning: do not shut down the crate instance for every
                            single test instead just delete all indices
        :param transport_port: port on which transport layer for crate should
                               run
        :param crate_exec: alternative executable command
        :param crate_config: alternative crate config file location.
                             Must be a directory or a file named 'crate.yml'
        :param cluster_name: the name of the cluster to join/build. Will be
                             generated automatically if omitted.
        :param host: the host to bind to. defaults to 'localhost'
        :param settings: further settings that do not deserve a keyword
                         argument will be prefixed with ``es.``.
        """
        self.__name__ = name
        self.keepRunning = keepRunning
        crate_home = os.path.abspath(crate_home)
        if crate_exec is None:
            start_script = 'crate.bat' if sys.platform == 'win32' else 'crate'
            crate_exec = os.path.join(crate_home, 'bin', start_script)
        if crate_config is None:
            crate_config = os.path.join(crate_home, 'config', 'crate.yml')
        elif (os.path.isfile(crate_config) and
              os.path.basename(crate_config) != 'crate.yml'):
            raise ValueError(CRATE_CONFIG_ERROR)
        if cluster_name is None:
            cluster_name = "Testing{0}".format(port)
        settings = self.create_settings(crate_config,
                                        cluster_name,
                                        name,
                                        host,
                                        port,
                                        transport_port,
                                        multicast,
                                        settings)
        start_cmd = (crate_exec, ) + tuple(["-Des.%s=%s" % opt
                                           for opt in settings.items()])

        self.http_url = 'http://{host}:{port}'.format(
            host=settings['network.host'], port=settings['http.port'])

        self._wd = wd = os.path.join(CrateLayer.tmpdir, 'crate_layer', name)
        self.start_cmd = start_cmd + ('-Des.path.data=%s' % wd,)

    def create_settings(self,
                        crate_config,
                        cluster_name,
                        node_name,
                        host,
                        http_port,
                        transport_port,
                        multicast,
                        further_settings=None):
        settings = {
            "discovery.type": "zen",
            "cluster.routing.allocation.disk.watermark.low": "1b",
            "cluster.routing.allocation.disk.watermark.high": "1b",
            "discovery.initial_state_timeout": 0,
            "discovery.zen.ping.multicast.enabled": str(multicast).lower(),
            "node.name": node_name,
            "cluster.name": cluster_name,
            "network.host": host,
            "http.port": http_port,
            "path.conf": os.path.dirname(crate_config)
        }
        if transport_port:
            settings["transport.tcp.port"] = transport_port
        if further_settings:
            settings.update(further_settings)
        return settings

    def wdPath(self):
        return self._wd

    @property
    def crate_servers(self):
        return [self.http_url]

    def setUp(self):
        self.start()

    def start(self):
        if os.path.exists(self._wd):
            shutil.rmtree(self._wd)

        self.process = subprocess.Popen(self.start_cmd)
        returncode = self.process.poll()
        if returncode is not None:
            raise SystemError('Failed to start server rc={0} cmd={1}'.format(
                returncode, self.start_cmd))
        self._wait_for_start()
        self._wait_for_master()

    def stop(self):
        self.process.kill()

    def tearDown(self):
        self.stop()

    def _wait_for(self, validator):
        time_slept = 0
        max_wait_for_connection = 20  # secs

        while True:
            try:
                if validator():
                    break
                else:
                    sys.stderr.write(
                        'Waiting for layer ... {0:.1f}s\n'.format(time_slept)
                    )
            except MaxRetryError as e:
                if time_slept >= max_wait_for_connection:
                    raise e
            except Exception as e:
                self.stop()
                raise e

            time.sleep(self.wait_interval)
            time_slept += self.wait_interval

    def _wait_for_start(self):
        """Wait for instance to be started"""

        # since crate 0.10.0 http may be ready before the cluster
        # is fully available block here so that early requests
        # after the layer starts don't result in 503
        def validator():
            url = '{server}/'.format(server=self.http_url)
            resp = self.conn_pool.request('HEAD', url)
            return resp.status == 200

        self._wait_for(validator)

    def _wait_for_master(self):
        """Wait for master node"""

        def validator():
            url = '{server}/_sql'.format(server=self.http_url)
            resp = self.conn_pool.urlopen(
                'POST', url,
                headers={'Content-Type': 'application/json'},
                body='{"stmt": "select master_node from sys.cluster"}'
            )
            data = json.loads(resp.data.decode('utf-8'))
            if resp.status == 200 and data['rows'][0][0]:
                sys.stderr.write('Crate layer started.\n')
                return True
            return False

        self._wait_for(validator)
