import multiprocessing
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import MagicMock

import pytest
import urllib3

import crate

REQUEST_PATH = "crate.client.http.Server.request"


def fake_response(
        status: int,
        reason: str = None,
        content_type: str = "application/json"
) -> MagicMock:
    """
    Returns a mocked `urllib3.response.HTTPResponse` HTTP response.
    """
    m = MagicMock(spec=urllib3.response.HTTPResponse)
    m.status = status
    m.reason = reason or ""
    m.headers = {"content-type": content_type}
    return m


@pytest.fixture
def mocked_connection():
    """
    Returns a crate `Connection` with a mocked `Client`

    Example:
        def test_conn(mocked_connection):
            cursor = mocked_connection.cursor()
            statement = "select * from locations where position = ?"
            cursor.execute(statement, 1)
            mocked_connection.client.sql.called_with(statement, 1, None)
    """
    yield crate.client.connect(client=MagicMock(spec=crate.client.http.Client))




@pytest.fixture
def serve_http():
    """
    Returns a context manager that start an http server running
    in another thread that returns CrateDB successful responses.

    It accepts an optional parameter, the handler class, it has to be an
    instance of `BaseHTTPRequestHandler`

    The port will be an unused random port.

    Example:
        def test_http(serve_http):
            with serve_http() as url:
                urllib3.urlopen(url)

    See `test_http.test_keep_alive` for more advance example.
    """

    @contextmanager
    def _serve(handler_cls=BaseHTTPRequestHandler):
        assert issubclass(handler_cls, BaseHTTPRequestHandler) # noqa: S101
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()

        manager = multiprocessing.Manager()
        SHARED = manager.dict()
        SHARED["count"] = 0
        SHARED["usernameFromXUser"] = None
        SHARED["username"] = None
        SHARED["password"] = None
        SHARED["schema"] = None

        server = HTTPServer((host, port), handler_cls)

        server.SHARED = SHARED

        thread = threading.Thread(target=server.serve_forever, daemon=False)
        thread.start()
        try:
            yield server, f"http://{host}:{port}"

        finally:
            server.shutdown()
            thread.join()
    return _serve
