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
import queue
import random
import socket
import time
from base64 import b64decode
from http.server import BaseHTTPRequestHandler
from threading import Event, Thread
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import certifi
import pytest
import urllib3.exceptions

from crate.client.connection import connect
from crate.client.exceptions import (
    ConnectionError,
    IntegrityError,
    ProgrammingError,
)
from crate.client.http import (
    Client,
    _get_socket_opts,
    _remove_certs_for_non_https,
)
from tests.conftest import REQUEST_PATH, fake_response

mocked_request = MagicMock(spec=urllib3.response.HTTPResponse)


def fake_redirect(location: str) -> MagicMock:
    m = fake_response(307)
    m.get_redirect_location.return_value = location
    return m


def duplicate_key_exception():
    r = fake_response(409, "Conflict")
    r.data = json.dumps(
        {
            "error": {
                "code": 4091,
                "message": "DuplicateKeyException[A document with the "
                "same primary key exists already]",
            }
        }
    ).encode()
    return r


def fail_sometimes(*args, **kwargs) -> MagicMock:
    """
    Function that fails with a 50% chance. It either returns a successful mocked
    response or raises an urllib3 exception.
    """
    if random.randint(1, 10) % 2:
        raise urllib3.exceptions.MaxRetryError(None, "/_sql", "")
    return fake_response(200)


def test_connection_reset_exception():
    """
    Verify that a HTTP 503 status code response raises an exception.
    """

    expected_exception_msg = (
        "No more Servers available, exception"
        " from last server: Service Unavailable"
    )
    with patch(
        REQUEST_PATH,
        side_effect=[
            fake_response(200),
            fake_response(104, "Connection reset by peer"),
            fake_response(503, "Service Unavailable"),
        ],
    ):
        client = Client(servers="localhost:4200")
        client.sql("select 1")  # 200 response
        client.sql("select 2")  # 104 response
        assert list(client._active_servers) == ["http://localhost:4200"]

        with pytest.raises(ProgrammingError, match=expected_exception_msg):
            client.sql("select 3")  # 503 response
        assert not client._active_servers


def test_no_connection_exception():
    """
    Verify that when no connection can be made to the server,
    a `ConnectionError` is raised.
    """
    client = Client(servers="localhost:9999")
    with pytest.raises(ConnectionError):
        client.sql("")


def test_http_error_is_re_raised():
    """
    Verify that when calling `REQUEST` if any error occurs,
    a `ProgrammingError` exception is raised _from_ that exception.
    """
    client = Client()

    exception_msg = "some exception did happen"
    with patch(REQUEST_PATH, side_effect=Exception(exception_msg)):
        with pytest.raises(ProgrammingError, match=exception_msg):
            client.sql("select foo")


def test_programming_error_contains_http_error_response_content():
    """
    Verify that when calling `REQUEST` if any error occurs,
    the raised `ProgrammingError` exception
    contains the error message from the original error.
    """
    expected_msg = "this message should appear"
    with patch(REQUEST_PATH, side_effect=Exception(expected_msg)):
        client = Client()
        with pytest.raises(ProgrammingError, match=expected_msg):
            client.sql("select 1")


def test_connect():
    """
    Verify the correctness of `server` parameter when `Client` is instantiated.
    """
    client = Client(servers="localhost:4200 localhost:4201")
    assert client._active_servers == [
        "http://localhost:4200",
        "http://localhost:4201",
    ]

    # By default, it's http://127.0.0.1:4200
    client = Client(servers=None)
    assert client._active_servers == ["http://127.0.0.1:4200"]

    with pytest.raises(TypeError, match="expected string or bytes"):
        Client(servers=[123, "127.0.0.1:4201", False])


def test_redirect_handling():
    """
    Verify that when a redirect happens, that redirect uri
    gets added to the server pool.
    """
    with patch(
        REQUEST_PATH, return_value=fake_redirect("http://localhost:4201")
    ):
        client = Client(servers="localhost:4200")

        # Don't try to print the exception or use `match`, otherwise
        # the recursion will not be short-circuited and it will hang.
        with pytest.raises(ProgrammingError):
            # 4201 gets added to serverpool but isn't available
            # that's why we run into an infinite recursion
            # exception message is: maximum recursion depth exceeded
            client.blob_get("blobs", "fake_digest")

        assert sorted(client.server_pool.keys()) == [
            "http://localhost:4200",
            "http://localhost:4201",
        ]

    # the new non-https server must not contain any SSL only arguments
    # regression test for:
    # - https://github.com/crate/crate-python/issues/179
    # - https://github.com/crate/crate-python/issues/180

    assert client.server_pool["http://localhost:4201"].pool.conn_kw == {
        "socket_options": _get_socket_opts(keepalive=True)
    }


def test_server_infos():
    """
    Verify that when a `MaxRetryError` is raised, a `ConnectionError` is raised.
    """
    error = urllib3.exceptions.MaxRetryError(None, "/")
    with patch(REQUEST_PATH, side_effect=error):
        client = Client(servers="localhost:4200 localhost:4201")
        with pytest.raises(ConnectionError):
            client.server_infos("http://localhost:4200")


def test_server_infos_401():
    """
    Verify that when a 401 status code is returned, a `ProgrammingError`
    is raised.
    """
    response = fake_response(401, "Unauthorized", "text/html")
    with patch(REQUEST_PATH, return_value=response):
        client = Client(servers="localhost:4200")
        with pytest.raises(
            ProgrammingError, match="401 Client Error: Unauthorized"
        ):
            client.server_infos("http://localhost:4200")


def test_credentials_derived():
    """
    Tests that Client correctly derives username and password from the url.
    """
    expected_user = "someuser"
    expected_password = "somepassword"
    client = Client(
        f"http://{expected_user}:{expected_password}@localhost:4200"
    )

    assert client.username == expected_user
    assert client.password == expected_password

    with patch("crate.client.http.urlparse", side_effect=Exception):
        Client("")

    actual_username = "actual_username"
    client = Client(
        username=actual_username,
        servers=[f"http://{expected_user}:{expected_password}@localhost:4200"],
    )
    assert client.username == actual_username
    assert client.password is None

    actual_password = "actual_password"
    client = Client(
        password=actual_password,
        servers=[f"http://{expected_user}:{expected_password}@localhost:4200"],
    )
    assert client.username == expected_user
    assert client.password == expected_password


def test_bad_bulk_400():
    """
    Verify that a 400 response when doing a bulk request raises
    a `ProgrammingException` with the error message of the response object's
    key `error_message`, several error messages can be returned by the database.
    """
    response = fake_response(400, "Bad Request")
    response.data = json.dumps(
        {
            "results": [
                {"rowcount": 1},
                {"error_message": "an error occurred"},
                {"error_message": "another error"},
                {"error_message": ""},
                {"error_message": None},
            ]
        }
    ).encode()

    client = Client(servers="localhost:4200")
    with patch(REQUEST_PATH, return_value=response):
        with pytest.raises(
            ProgrammingError, match="an error occurred\nanother error"
        ):
            client.sql(
                "Insert into users (name) values(?)",
                bulk_parameters=[["douglas"], ["monthy"]],
            )


def test_socket_options_contain_keepalive():
    """
    Verify that KEEPALIVE options are present at `socket_options`
    """
    server = "http://localhost:4200"
    client = Client(servers=server)
    conn_kw = client.server_pool[server].pool.conn_kw
    assert (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) in conn_kw[
        "socket_options"
    ]


def test_duplicate_key_error():
    """
    Verify that an `IntegrityError` is raised on duplicate key errors,
    instead of the more general `ProgrammingError`.
    """
    expected_error_msg = (
        r"DuplicateKeyException\[A document with "
        r"the same primary key exists already\]"
    )
    with patch(REQUEST_PATH, return_value=duplicate_key_exception()):
        client = Client(servers="localhost:4200")
        with pytest.raises(IntegrityError, match=expected_error_msg):
            client.sql("INSERT INTO testdrive (foo) VALUES (42)")


@patch(REQUEST_PATH, fail_sometimes)
def test_client_multithreaded():
    """
    Verify client multithreading using a pool of 5 Threads to emit commands to
     the multiple servers through one Client-instance.

    Checks if the number of servers in _inactive_servers and _active_servers
    always equals the number of servers initially given.

    Note:
        This test is probabilistic and does not ensure that the
        client is indeed thread-safe in all cases, it can only show that it
        withstands this scenario.

    """
    servers = [
        "127.0.0.1:44209",
        "127.0.0.2:44209",
        "127.0.0.3:44209",
    ]
    num_threads = 5
    num_commands = 1000
    thread_timeout = 10.0  # seconds

    gate = Event()
    error_queue = queue.Queue()

    client = Client(servers)
    client.retry_interval = 0.2  # faster retry

    def worker():
        """
        Worker that sends many requests, if the `num_server` is not the
        expected value at some point, an assertion will be added to the shared
        error queue.
        """
        gate.wait()  # wait for the others
        expected_num_servers = len(servers)
        for _ in range(num_commands):
            try:
                client.sql("select name from sys.cluster")
            except ConnectionError:
                # Sometimes it will fail.
                pass
            try:
                with client._lock:
                    num_servers = len(client._active_servers) + len(
                        client._inactive_servers
                    )
                    assert num_servers == expected_num_servers, (
                        f"expected {expected_num_servers} but got {num_servers}"
                    )
            except AssertionError as e:
                error_queue.put(e)

    threads = [Thread(target=worker, name=str(i)) for i in range(num_threads)]

    for thread in threads:
        thread.start()

    gate.set()

    for t in threads:
        t.join(timeout=thread_timeout)

    # If any thread is still alive after the timeout, consider it a failure.
    alive = [t.name for t in threads if t.is_alive()]
    if alive:
        pytest.fail(f"Threads did not finish within {thread_timeout}s: {alive}")

    if not error_queue.empty():
        # If an error happened, consider it a failure as well.
        first_error_trace = error_queue.get(block=False)
        pytest.fail(first_error_trace)


def test_params():
    """
    Verify client parameters translate correctly to query parameters.
    """
    client = Client(["127.0.0.1:4200"], error_trace=True)
    parsed = urlparse(client.path)
    params = parse_qs(parsed.query)

    assert params["error_trace"] == ["true"]
    assert params["types"] == ["true"]

    client = Client(["127.0.0.1:4200"])
    parsed = urlparse(client.path)
    params = parse_qs(parsed.query)

    # Default is False
    assert "error_trace" not in params
    assert params["types"] == ["true"]

    assert "/_sql?" in client.path


def test_client_ca():
    """
    Verify that if env variable `REQUESTS_CA_BUNDLE` is set,  certs are
    loaded into the pool.
    """
    with patch.dict(os.environ, {"REQUEST_PATH": certifi.where()}, clear=True):
        client = Client("http://127.0.0.1:4200")
        assert "ca_certs" in client._pool_kw


def test_remove_certs_for_non_https():
    """
    Verify that `_remove_certs_for_non_https` correctly removes ca_certs.
    """
    d = _remove_certs_for_non_https("https", {"ca_certs": 1})
    assert "ca_certs" in d

    kwargs = {"ca_certs": 1, "foobar": 2, "cert_file": 3}
    d = _remove_certs_for_non_https("http", kwargs)
    assert "ca_certs" not in d
    assert "cert_file" not in d
    assert "foobar" in d


def test_keep_alive(serve_http):
    """
    Verify that when launching several requests, the connection is kept
    alive and successfully terminates.

    This uses a real http sever that mocks CrateDB-like responses.
    """

    class ClientAddressRequestHandler(BaseHTTPRequestHandler):
        """
        http handler for use with HTTPServer

        returns client host and port in crate-conform-responses
        """

        protocol_version = "HTTP/1.1"

        def do_GET(self):
            content_length = self.headers.get("content-length")
            if content_length:
                self.rfile.read(int(content_length))

            response = json.dumps(
                {
                    "cols": ["host", "port"],
                    "rows": [self.client_address[0], self.client_address[1]],
                    "rowCount": 1,
                }
            )

            self.send_response(200)
            self.send_header("Content-Length", str(len(response)))
            self.send_header("Content-Type", "application/json; charset=UTF-8")
            self.end_headers()
            self.wfile.write(response.encode("UTF-8"))

        do_POST = do_GET

    with serve_http(ClientAddressRequestHandler) as (_, url):
        with connect(url) as conn:
            client = conn.client
            for _ in range(25):
                result = client.sql("select * from fake")

                another_result = client.sql("select again from fake")
                assert result == another_result


def test_no_retry_on_read_timeout(serve_http):
    timeout = 1

    class TimeoutRequestHandler(BaseHTTPRequestHandler):
        """
        HTTP handler for use with TestingHTTPServer
        updates the shared counter and waits so that the client times out
        """

        def do_POST(self):
            self.server.SHARED["count"] += 1
            time.sleep(timeout + 0.1)

        def do_GET(self):
            pass

    # Start the http server.
    with serve_http(TimeoutRequestHandler) as (server, url):
        # Connect to the server.
        with connect(url, timeout=timeout) as conn:
            # We expect it to raise a `ConnectionError`
            with pytest.raises(ConnectionError, match="Read timed out"):
                conn.client.sql("select * from fake")
            assert server.SHARED.get("count") == 1


class SharedStateRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP handler for use with TestingHTTPServer
    sets the shared state of the server and returns an empty response
    """

    def do_POST(self):
        self.server.SHARED["count"] += 1
        self.server.SHARED["schema"] = self.headers.get("Default-Schema")

        if self.headers.get("Authorization") is not None:
            auth_header = self.headers["Authorization"].replace("Basic ", "")
            credentials = b64decode(auth_header).decode("utf-8").split(":", 1)
            self.server.SHARED["username"] = credentials[0]
            if len(credentials) > 1 and credentials[1]:
                self.server.SHARED["password"] = credentials[1]
            else:
                self.server.SHARED["password"] = None
        else:
            self.server.SHARED["username"] = None

        if self.headers.get("X-User") is not None:
            self.server.SHARED["usernameFromXUser"] = self.headers["X-User"]
        else:
            self.server.SHARED["usernameFromXUser"] = None

        # send empty response
        response = "{}"
        self.send_response(200)
        self.send_header("Content-Length", len(response))
        self.send_header("Content-Type", "application/json; charset=UTF-8")
        self.end_headers()
        self.wfile.write(response.encode("utf-8"))

    def do_GET(self):
        pass


def test_default_schema(serve_http):
    """
    Verify that the schema is correctly sent.
    """
    test_schema = "some_schema"
    with serve_http(SharedStateRequestHandler) as (server, url):
        with connect(url, schema=test_schema) as conn:
            conn.client.sql("select 1;")
        assert server.SHARED.get("schema") == test_schema


def test_credentials(serve_http):
    """
    Verify credentials are correctly set in the connection and client.
    """
    with serve_http(SharedStateRequestHandler) as (server, url):
        # Nothing default
        with connect(url) as conn:
            assert not conn.client.username
            assert not conn.client.password

            conn.client.sql("select 1;")
            assert not server.SHARED["usernameFromXUser"]
            assert not server.SHARED["username"]
            assert not server.SHARED["password"]

        # Just the username
        username = "some_username"
        with connect(url, username=username) as conn:
            assert conn.client.username == username
            assert not conn.client.password

            conn.client.sql("select 2;")
            assert server.SHARED["usernameFromXUser"] == username
            assert server.SHARED["username"] == username
            assert not server.SHARED["password"]

        # Both username and password
        password = "some_password"
        with connect(url, username=username, password=password) as conn:
            assert conn.client.username == username
            assert conn.client.password == password
            conn.client.sql("select 3;")
            assert server.SHARED["usernameFromXUser"] == username
            assert server.SHARED["username"] == username
            assert server.SHARED["password"] == password
