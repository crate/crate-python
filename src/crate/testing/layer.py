import os
import signal
import time
import logging
import urllib3

from lovely.testlayers import server, layer


logger = logging.getLogger(__name__)


class CrateLayer(server.ServerLayer, layer.WorkDirectoryLayer):
    """
    this layer starts a crate server.
    """

    wdClean = True

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
                 multicast=False):
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
        """
        self.keepRunning = keepRunning
        crate_home = os.path.abspath(crate_home)
        servers = ['%s:%s' % (host, port)]
        self.crate_servers = ['http://%s:%s' % (host, port)]
        if crate_exec is None:
            crate_exec = os.path.join(crate_home, 'bin', 'crate')
        if crate_config is None:
            crate_config = os.path.join(crate_home, 'config', 'crate.yml')
        if cluster_name is None:
            cluster_name = "Testing{0}".format(port)
        start_cmd = (
            crate_exec,
            '-Des.index.storage.type=memory',
            '-Des.node.name=%s' % name,
            '-Des.cluster.name=%s' % cluster_name,
            '-Des.http.port=%s-%s' % (port, port),
            '-Des.network.host=%s' % host,
            '-Des.discovery.type=zen',
            '-Des.discovery.zen.ping.multicast.enabled=%s' % ("true" if multicast else "false"),
            '-Des.config=%s' % crate_config,
            '-Des.path.conf=%s' % os.path.dirname(crate_config),
        )
        if transport_port:
            start_cmd += ('-Des.transport.tcp.port=%s' % transport_port,)
        super(CrateLayer, self).__init__(name, servers=servers, start_cmd=start_cmd)
        self.setUpWD()

    def stop(self):
        # override because if we use proc.kill the terminal gets poisioned
        self.process.send_signal(signal.SIGINT)
        self.process.wait()

    def start(self):
        wd = self.wdPath()
        self.start_cmd = self.start_cmd + ('-Des.path.data="%s"' % wd,)
        super(CrateLayer, self).start()
        # since crate 0.10.0 http may be ready before the cluster is fully available
        # block here so that early requests after the layer starts don't result in 503

        time_slept = 0
        http = urllib3.PoolManager()
        while True:
            try:
                resp = http.request('GET', self.crate_servers[0] + '/')
                if resp.status == 200:
                    break
                time.sleep(0.02)
                time_slept += 0.02
                if time_slept % 1 == 0:
                    logger.warning(('Crate not yet fully available. '
                                    'Waiting since %s seconds...'), time_slept)
            except Exception:
                self.stop()
                raise
