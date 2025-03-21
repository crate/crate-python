import datetime
from unittest import TestCase

from urllib3 import Timeout

from crate.client import connect
from crate.client.connection import Connection
from crate.client.http import Client

from .settings import crate_host


class ConnectionTest(TestCase):
    def test_connection_mock(self):
        """
        For testing purposes it is often useful to replace the client used for
        communication with the CrateDB server with a stub or mock.

        This can be done by passing an object of the Client class when calling
        the `connect` method.
        """

        class MyConnectionClient:
            active_servers = ["localhost:4200"]

            def __init__(self):
                pass

            def server_infos(self, server):
                return ("localhost:4200", "my server", "0.42.0")

        connection = connect([crate_host], client=MyConnectionClient())
        self.assertIsInstance(connection, Connection)
        self.assertEqual(
            connection.client.server_infos("foo"),
            ("localhost:4200", "my server", "0.42.0"),
        )

    def test_lowest_server_version(self):
        infos = [
            (None, None, "0.42.3"),
            (None, None, "0.41.8"),
            (None, None, "not a version"),
        ]

        client = Client(servers="localhost:4200 localhost:4201 localhost:4202")
        client.server_infos = lambda server: infos.pop()
        connection = connect(client=client)
        self.assertEqual((0, 41, 8), connection.lowest_server_version.version)
        connection.close()

    def test_invalid_server_version(self):
        client = Client(servers="localhost:4200")
        client.server_infos = lambda server: (None, None, "No version")
        connection = connect(client=client)
        self.assertEqual((0, 0, 0), connection.lowest_server_version.version)
        connection.close()

    def test_context_manager(self):
        with connect("localhost:4200") as conn:
            pass
        self.assertEqual(conn._closed, True)

    def test_with_timezone(self):
        """
        The cursor can return timezone-aware `datetime` objects when requested.

        When switching the time zone at runtime on the connection object, only
        new cursor objects will inherit the new time zone.
        """

        tz_mst = datetime.timezone(datetime.timedelta(hours=7), name="MST")
        connection = connect("localhost:4200", time_zone=tz_mst)
        cursor = connection.cursor()
        self.assertEqual(cursor.time_zone.tzname(None), "MST")
        self.assertEqual(
            cursor.time_zone.utcoffset(None), datetime.timedelta(seconds=25200)
        )

        connection.time_zone = datetime.timezone.utc
        cursor = connection.cursor()
        self.assertEqual(cursor.time_zone.tzname(None), "UTC")
        self.assertEqual(
            cursor.time_zone.utcoffset(None), datetime.timedelta(0)
        )

    def test_timeout_float(self):
        """
        Verify setting the timeout value as a scalar (float) works.
        """
        with connect("localhost:4200", timeout=2.42) as conn:
            self.assertEqual(conn.client._pool_kw["timeout"], 2.42)

    def test_timeout_string(self):
        """
        Verify setting the timeout value as a scalar (string) works.
        """
        with connect("localhost:4200", timeout="2.42") as conn:
            self.assertEqual(conn.client._pool_kw["timeout"], 2.42)

    def test_timeout_object(self):
        """
        Verify setting the timeout value as a Timeout object works.
        """
        timeout = Timeout(connect=2.42, read=0.01)
        with connect("localhost:4200", timeout=timeout) as conn:
            self.assertEqual(conn.client._pool_kw["timeout"], timeout)
