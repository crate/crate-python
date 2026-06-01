import datetime
from unittest.mock import MagicMock, patch

import pytest
from urllib3 import Timeout

from crate.client import connect
from crate.client.connection import Connection
from crate.client.exceptions import ProgrammingError
from crate.client.http import Client

from .settings import crate_host


def test_lowest_server_version():
    """
    Verify the lowest server version is correctly set.
    """
    servers = "localhost:4200 localhost:4201 localhost:4202 localhost:4207"
    infos = [
        (None, None, "1.0.3"),
        (None, None, "5.5.2"),
        (None, None, "6.0.0"),
        (None, None, "not a version"),
    ]

    client = Client(servers=servers)
    client.server_infos = lambda server: infos.pop()
    connection = connect(client=client)
    assert (1, 0, 3) == connection.lowest_server_version.version


def test_connection_closes_access():
    """
    Verify that a connection closes on exit and that it also closes
    the client.
    """
    with patch(
        "crate.client.connection.Client", spec=Client, return_value=MagicMock()
    ) as client:
        conn = connect()
        conn.close()

        assert conn._closed
        client.assert_called_once()

        # Should raise an exception if
        # we try to access a cursor now.
        with pytest.raises(ProgrammingError):
            conn.cursor()

        with pytest.raises(ProgrammingError):
            conn.commit()


def test_connection_closes_context_manager():
    """Verify that the context manager of the client closes the connection"""
    with patch.object(connect, "close", autospec=True) as close_fn:
        with connect():
            pass
        close_fn.assert_called_once()


def test_invalid_server_version():
    """
    Verify that when no correct version is set,
    the default (0, 0, 0) is returned.
    """
    client = Client(servers="localhost:4200")
    client.server_infos = lambda server: (None, None, "No version")
    connection = connect(client=client)
    assert (0, 0, 0) == connection.lowest_server_version.version


def test_context_manager():
    """
    Verify the context manager implementation of `Connection`.
    """
    close_method = "crate.client.http.Client.close"
    with patch(close_method, return_value=MagicMock()) as close_func:
        with connect("localhost:4200") as conn:
            assert not conn._closed

        assert conn._closed
        # Checks that the close method of the client
        # is called when the connection is closed.
        close_func.assert_called_once()


def test_connection_mock():
    """
    Verify that a custom client can be passed.


    For testing purposes, it is often useful to replace the client used for
    communication with the CrateDB server with a stub or mock.

    This can be done by passing an object of the Client class when calling
    the `connect` method.
    """

    mock = MagicMock(spec=Client)
    mock.server_infos.return_value = "localhost:4200", "my server", "0.42.0"
    connection = connect(crate_host, client=mock)

    assert isinstance(connection, Connection)
    assert connection.client.server_infos("foo") == (
        "localhost:4200",
        "my server",
        "0.42.0",
    )


def test_default_repr():
    """
    Verify default repr dunder method.
    """
    conn = connect()
    assert repr(conn) == "<Connection <Client ['http://127.0.0.1:4200']>>"


def test_with_timezone():
    """
    Verify the logic of passing timezone objects to the client.

    The cursor can return timezone-aware `datetime` objects when requested.

    When switching the time zone at runtime on the connection object, only
    new cursor objects will inherit the new time zone.

    These tests are complementary to timezone `test_cursor`
    """

    tz_mst = datetime.timezone(datetime.timedelta(hours=7), name="MST")
    connection = connect("localhost:4200", time_zone=tz_mst)
    cursor = connection.cursor()

    assert cursor.time_zone.tzname(None) == "MST"
    assert cursor.time_zone.utcoffset(None) == datetime.timedelta(seconds=25200)

    connection.time_zone = datetime.timezone.utc
    cursor = connection.cursor()
    assert cursor.time_zone.tzname(None) == "UTC"
    assert cursor.time_zone.utcoffset(None) == datetime.timedelta(0)


def test_timeout_float():
    """
    Verify setting the timeout value as a scalar (float) works.
    """
    with connect("localhost:4200", timeout=2.42) as conn:
        assert conn.client._pool_kw["timeout"] == 2.42


def test_timeout_string():
    """
    Verify setting the timeout value as a scalar (string) works.
    """
    with connect("localhost:4200", timeout="2.42") as conn:
        assert conn.client._pool_kw["timeout"] == 2.42


def test_timeout_object():
    """
    Verify setting the timeout value as a Timeout object works.
    """
    timeout = Timeout(connect=2.42, read=0.01)
    with connect("localhost:4200", timeout=timeout) as conn:
        assert conn.client._pool_kw["timeout"] == timeout
