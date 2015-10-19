import os
import sys
import signal
import time
import json
import logging
import urllib3
from urllib3.exceptions import MaxRetryError
from lovely.testlayers import server, layer

logger = logging.getLogger(__name__)

class CrateLayer(server.ServerLayer, layer.WorkDirectoryLayer):
    """
    this layer starts a crate server.
    """

    wait_interval = 0.2
    wdClean = True
    conn_pool = urllib3.PoolManager()

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
        :param transport_port: port on which transport layer for crate should run
        :param crate_exec: alternative executable command
        :param crate_config: alternative crate config file location
        :param cluster_name: the name of the cluster to join/build. Will be
                             generated automatically if omitted.
        :param host: the host to bind to. defaults to 'localhost'
        :param settings: further settings that do not deserve a keyword argument
                         will be prefixed with ``es.``.
        """
        self.keepRunning = keepRunning
        crate_home = os.path.abspath(crate_home)
        if crate_exec is None:
            crate_exec = os.path.join(crate_home, 'bin', 'crate')
        if crate_config is None:
            crate_config = os.path.join(crate_home, 'config', 'crate.yml')
        if cluster_name is None:
            cluster_name = "Testing{0}".format(port)
        settings = self.create_settings(crate_config, cluster_name, name, host, port, transport_port, multicast, settings)
        start_cmd = (crate_exec, ) + tuple(["-Des.%s=%s" % opt for opt in settings.items()])

        server = '%s:%s' % (settings["network.host"], settings["http.port"])
        self.crate_servers = ['http://%s' % server]

        super(CrateLayer, self).__init__(name, servers=[server], start_cmd=start_cmd)
        self.setUpWD()

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
            "index.store.type": "memory",
            "discovery.type": "zen",
            "gateway.type": "none",
            "cluster.routing.allocation.disk.watermark.low": "1b",
            "cluster.routing.allocation.disk.watermark.high": "1b",
            "discovery.initial_state_timeout": 0,
            "discovery.zen.ping.multicast.enabled": "true" if multicast else "false",
            "node.name": node_name,
            "cluster.name": cluster_name,
            "network.host": host,
            "http.port": http_port,
            "config": crate_config,
            "path.conf": os.path.dirname(crate_config)
        }
        if transport_port:
            settings["transport.tcp.port"] = transport_port
        if further_settings:
            settings.update(further_settings)
        return settings

    def stop(self):
        # override because if we use proc.kill the terminal gets poisioned
        self.process.send_signal(signal.SIGINT)
        self.process.wait()

    def start(self):
        wd = self.wdPath()
        self.start_cmd = self.start_cmd + ('-Des.path.data="%s"' % wd,)
        super(CrateLayer, self).start()
        self.wait_for_start()
        self.wait_for_master()

    def _wait_for(self, validator):
        time_slept = 0
        max_wait_for_connection = 5  # secs

        while True:
            try:
                if validator():
                    break
                else:
                    sys.stderr.write('Waiting for layer ... {0:.1f}s\n'.format(time_slept))
            except MaxRetryError as e:
                if time_slept >= max_wait_for_connection:
                    raise e
            except Exception as e:
                self.stop()
                raise e

            time.sleep(self.wait_interval)
            time_slept += self.wait_interval


    def wait_for_start(self):
        """Wait for instance to be started"""

        # since crate 0.10.0 http may be ready before the cluster is fully available
        # block here so that early requests after the layer starts don't result in 503
        def validator():
            url = '{server}/'.format(server=self.crate_servers[0])
            resp = self.conn_pool.request('HEAD', url)
            return resp.status == 200

        self._wait_for(validator)

    def wait_for_master(self):
        """Wait for master node"""

        def validator():
            url = '{server}/_sql'.format(server=self.crate_servers[0])
            resp = self.conn_pool.urlopen('POST', url,
                headers={'Content-Type': 'application/json'},
                body='{"stmt": "select master_node from sys.cluster"}')
            data = json.loads(resp.data.decode('utf-8'))
            if resp.status == 200 and data['rows'][0][0]:
                sys.stderr.write('Crate layer started.\n')
                return True
            return False

        self._wait_for(validator)
