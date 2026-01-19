import json
import logging
import multiprocessing
import os
import platform
import socket
import ssl
import sys
import tarfile
import threading
import time
import zipfile
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import MagicMock
from urllib.request import urlretrieve

import pytest
import urllib3

import crate
from crate.client import connect
from crate.testing.layer import CrateLayer
from tests.client.settings import assets_path

log = logging.getLogger("tests.conftest")


REQUEST_PATH = "crate.client.http.Server.request"
URL_TMPL = "https://cdn.crate.io/downloads/releases/cratedb/{arch}_{os}/crate-6.1.2.{ext}"

project_root = Path(__file__).parent.parent
cratedb_path = project_root / "parts/crate"


crate_port = 44209
crate_transport_port = 44309
localhost = "127.0.0.1"
crate_host = f"http://{localhost}:{crate_port}"


def fake_response(
    status: int, reason: str = None, content_type: str = "application/json"
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
        assert issubclass(handler_cls, BaseHTTPRequestHandler)  # noqa: S101
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


def get_crate_url() -> str:
    extension = "tar.gz"

    machine = platform.machine()
    if machine.startswith("arm") or machine == "aarch64":
        arch = "aarch64"
    else:
        arch = "x64"

    if sys.platform.startswith("linux"):
        os = "linux"
    elif sys.platform.startswith("win32"):
        os = "windows"
        extension = "zip"
    elif sys.platform.startswith("darwin"):
        os = "mac"

        # there are no aarch64/arm64 distributions available
        # x64 should work via emulation layer
        arch = "x64"
    else:
        raise ValueError(f"Unsupported platform: {sys.platform}")

    return URL_TMPL.format(arch=arch, os=os, ext=extension)


def download_cratedb(path: Path):
    url = get_crate_url()
    if path.exists():
        return
    if not url.startswith("https:"):
        raise ValueError("Invalid url")
    filename, _msg = urlretrieve(url)
    if sys.platform.startswith("win32"):
        with zipfile.ZipFile(filename) as z:
            first_file = z.namelist()[0]
            folder_name = os.path.dirname(first_file)
            z.extractall(path.parent)
            (path.parent / folder_name).rename(path)
    else:
        with tarfile.open(filename) as t:
            first_file = t.getnames()[0]
            folder_name = os.path.dirname(first_file)
            t.extractall(path.parent, filter="data")
            (path.parent / folder_name).rename(path)


def create_test_data(cursor):
    with open(project_root / "tests/assets/mappings/locations.sql") as s:
        stmt = s.read()
        cursor.execute(stmt)
        stmt = (
            "select count(*) from information_schema.tables "
            "where table_name = 'locations'"
        )
        cursor.execute(stmt)
        assert cursor.fetchall()[0][0] == 1  # noqa: S101

    data_path = str(project_root / "tests/assets/import/test_a.json")
    # load testing data into crate
    cursor.execute("copy locations from ?", (data_path,))
    # refresh location table so imported data is visible immediately
    cursor.execute("refresh table locations")
    # create blob table
    cursor.execute(
        "create blob table myfiles clustered into 1 shards "
        + "with (number_of_replicas=0)"
    )

    # create users
    cursor.execute("CREATE USER me WITH (password = 'my_secret_pw')")
    cursor.execute("CREATE USER trusted_me")


@pytest.fixture()
def doctest_node():
    download_cratedb(cratedb_path)
    settings = {
        "udc.enabled": "false",
        "lang.js.enabled": "true",
        "auth.host_based.enabled": "true",
        "auth.host_based.config.0.user": "crate",
        "auth.host_based.config.0.method": "trust",
        "auth.host_based.config.98.user": "trusted_me",
        "auth.host_based.config.98.method": "trust",
        "auth.host_based.config.99.user": "me",
        "auth.host_based.config.99.method": "password",
        "discovery.type": "single-node",
    }
    crate_layer = CrateLayer(
        "crate",
        crate_home=cratedb_path,
        port=crate_port,
        host=localhost,
        transport_port=crate_transport_port,
        settings=settings,
    )
    crate_layer.start()
    with connect(crate_host) as conn:
        cursor = conn.cursor()
        create_test_data(cursor)
        cursor.close()

    yield crate_layer
    crate_layer.stop()


class HttpsServer(HTTPServer):

    PORT = 65534
    HOST = "localhost"
    CERT_FILE = assets_path("pki/server_valid.pem")
    CACERT_FILE = assets_path("pki/cacert_valid.pem")

    def get_request(self):
        # Prepare SSL context.
        context = ssl._create_unverified_context(  # noqa: S323
            protocol=ssl.PROTOCOL_TLS_SERVER,
            cert_reqs=ssl.CERT_OPTIONAL,
            check_hostname=False,
            purpose=ssl.Purpose.CLIENT_AUTH,
            certfile=HttpsServer.CERT_FILE,
            keyfile=HttpsServer.CERT_FILE,
            cafile=HttpsServer.CACERT_FILE,
        )  # noqa: S323

        # Set minimum protocol version, TLSv1 and TLSv1.1 are unsafe.
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        # Wrap TLS encryption around socket.
        socket, client_address = HTTPServer.get_request(self)
        socket = context.wrap_socket(socket, server_side=True)

        return socket, client_address


class HttpsHandler(BaseHTTPRequestHandler):
    payload = json.dumps(
        {
            "name": "test",
            "status": 200,
        }
    )

    def do_GET(self):
        self.send_response(200)
        payload = self.payload.encode("UTF-8")
        self.send_header("Content-Length", f"{len(payload)}")
        self.send_header("Content-Type", "application/json; charset=UTF-8")
        self.end_headers()
        self.wfile.write(payload)


def is_up(host: str, port: int) -> bool:
    """
    Test if a host is up.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ex = s.connect_ex((host, port))
    s.close()
    return ex == 0


@pytest.fixture
def https_server():
    port = HttpsServer.PORT
    host = HttpsServer.HOST
    server_address = (host, port)
    server = HttpsServer(server_address, HttpsHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    start = time.monotonic()
    timeout = 5
    while True:
        if is_up(host, port):
            break
        now = time.monotonic()
        if now - start > timeout:
            raise TimeoutError(
                "Could not properly start embedded webserver "
                "within {} seconds".format(timeout)
            )

    yield server
    server.shutdown()
    server.server_close()
