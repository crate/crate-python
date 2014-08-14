from .http import Client
from crate.client import connect
from unittest import TestCase


class ConnectionTest(TestCase):

    def test_lowest_server_version(self):
        infos = [(None, None, '0.42.3'),
                 (None, None, '0.41.8'),
                 (None, None, 'not a version')]

        client = Client(servers="localhost:4200 localhost:4201 localhost:4202")
        client.server_infos = lambda server: infos.pop()
        connection = connect(client=client)
        self.assertEqual((0, 41, 8), connection.lowest_server_version.version)

    def test_invalid_server_version(self):
        client = Client(servers="localhost:4200")
        client.server_infos = lambda server: (None, None, "No version")
        connection = connect(client=client)
        self.assertEqual((0, 0, 0), connection.lowest_server_version.version)
