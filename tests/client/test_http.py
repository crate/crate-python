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

import datetime as dt
import json
import multiprocessing
import os
import queue
import random
import socket
import sys
import time
import traceback
import uuid
from base64 import b64decode
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from multiprocessing.context import ForkProcess
from threading import Event, Thread
from unittest import TestCase
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import certifi
import pytest
import urllib3.exceptions

from crate.client.exceptions import (
    ConnectionError,
    IntegrityError,
    ProgrammingError,
)
from crate.client.http import (
    Client,
    _get_socket_opts,
    _remove_certs_for_non_https,
    json_dumps,
)

REQUEST = "crate.client.http.Server.request"
CA_CERT_PATH = certifi.where()

mocked_request = MagicMock(spec=urllib3.response.HTTPResponse)


def fake_request(response=None):
    def request(*args, **kwargs):
        if isinstance(response, list):
            resp = response.pop(0)
            response.append(resp)
            return resp
        elif response:
            return response
        else:
            return mocked_request

    return request


def fake_response(status, reason=None, content_type="application/json"):
    m = MagicMock(spec=urllib3.response.HTTPResponse)
    m.status = status
    m.reason = reason or ""
    m.headers = {"content-type": content_type}
    return m


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


def fail_sometimes(*args, **kwargs):
    # random.randint(1, 10) % 2:
    if random.randint(1, 100) % 10 == 0:
        raise urllib3.exceptions.MaxRetryError(None, "/_sql", "")
    return fake_response(200)


def test_connection_reset_exception():
    """
    Verify that a HTTP 503 status code response raises an exception.
    """

    expected_exception_msg = ("No more Servers available,"
                              " exception from last server: Service Unavailable")
    with patch(REQUEST, side_effect=[
        fake_response(200),
        fake_response(104, "Connection reset by peer"),
        fake_response(503, "Service Unavailable"),
    ]):
        client = Client(servers="localhost:4200")
        client.sql("select 1")  # 200 response
        client.sql("select 2")  # 104 response
        assert list(client._active_servers) == ["http://localhost:4200"]

        with pytest.raises(ProgrammingError, match=expected_exception_msg):
            client.sql("select 3")  # 503 response
        assert not client._active_servers


def test_no_connection_exception():
    """
    Verify that when no connection can be made to the server, a `ConnectionError` is raised.
    """
    client = Client(servers="localhost:9999")
    with pytest.raises(ConnectionError):
        client.sql("")


def test_http_error_is_re_raised():
    """
    Verify that when calling `REQUEST` if any error occurs, a `ProgrammingError` exception
    is raised _from_ that exception.
    """
    client = Client()

    with patch(REQUEST, side_effect=Exception):
        client.sql("select foo")
        with pytest.raises(ProgrammingError) as e:
            client.sql("select foo")


def test_programming_error_contains_http_error_response_content():
    """
    Verify that when calling `REQUEST` if any error occurs,
    the raised `ProgrammingError` exception
    contains the error message from the original error.
    """
    expected_msg = "this message should appear"
    with patch(REQUEST, side_effect=Exception(expected_msg)):
        client = Client()
        with pytest.raises(ProgrammingError, match=expected_msg):
            client.sql("select 1")


def test_connect():
    """
    Verify the correctness `server` parameter in `Client` instantiation.
    """
    client = Client(servers="localhost:4200 localhost:4201")
    assert client._active_servers == \
           ["http://localhost:4200", "http://localhost:4201"]

    # By default, it's http://127.0.0.1:4200
    client = Client(servers=None)
    assert client._active_servers == ["http://127.0.0.1:4200"]

    with pytest.raises(TypeError, match='expected string or bytes'):
        Client(servers=[123, "127.0.0.1:4201", False])


def test_redirect_handling():
    """
    Verify that when a redirect happens, that redirect uri gets added to the server pool.
    """
    with patch(REQUEST, return_value=fake_redirect("http://localhost:4201")):
        client = Client(servers="localhost:4200")

        # Don't try to print the exception or use `match`, otherwise
        # the recursion will not be short-circuited and it will hang.
        with pytest.raises(ProgrammingError):
            # 4201 gets added to serverpool but isn't available
            # that's why we run into an infinite recursion
            # exception message is: maximum recursion depth exceeded
            client.blob_get("blobs", "fake_digest")

        assert sorted(client.server_pool.keys()) == ["http://localhost:4200",
                                                     "http://localhost:4201"]

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
    with patch(REQUEST, side_effect=error):
        client = Client(servers="localhost:4200 localhost:4201")
        with pytest.raises(ConnectionError):
            client.server_infos("http://localhost:4200")


def test_server_infos_401():
    """
    Verify that when a 401 status code is returned, a `ProgrammingError` is raised.
    """
    response = fake_response(401, "Unauthorized", "text/html")
    with patch(REQUEST, return_value=response):
        client = Client(servers="localhost:4200")
        with pytest.raises(ProgrammingError, match="401 Client Error: Unauthorized"):
            client.server_infos("http://localhost:4200")


def test_bad_bulk_400():
    """
    Verify that a 400 response when doing a bulk request raises a `ProgrammingException` with
    the error message of the response object's key `error_message`, several error messages can
    be returned by the database.
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
    with patch(REQUEST, return_value=response):
        with pytest.raises(ProgrammingError, match='an error occurred\nanother error'):
            client.sql(
                "Insert into users (name) values(?)",
                bulk_parameters=[["douglas"], ["monthy"]]
            )


def test_decimal_serialization():
    """
    Verify that a `Decimal` type can be serialized and sent to the server.
    """
    with patch(REQUEST, return_value=fake_response(200)) as request:
        client = Client(servers="localhost:4200")

        dec = Decimal(0.12)
        client.sql("insert into users (float_col) values (?)", (dec,))
        data = json.loads(request.call_args[1]["data"])
        assert dec == Decimal(data["args"][0])



def test_datetime_is_converted_to_ts():
    """
    Verify that a `datetime.datetime` can be serialized.
    """
    with patch(REQUEST, return_value=fake_response(200)) as request:
        client = Client(servers="localhost:4200")

        datetime = dt.datetime(2015, 2, 28, 7, 31, 40)
        client.sql("insert into users (dt) values (?)", (datetime,))

        # convert string to dict
        # because the order of the keys isn't deterministic
        data = json.loads(request.call_args[1]["data"])
        assert data["args"][0] == 1425108700000


def test_date_is_converted_to_ts():
    """
    Verify that a `datetime.date` can be serialized.
    """
    with patch(REQUEST, return_value=fake_response(200)) as request:
        client = Client(servers="localhost:4200")

        day = dt.date(2016, 4, 21)
        client.sql("insert into users (dt) values (?)", (day,))
        data = json.loads(request.call_args[1]["data"])
        assert data["args"][0] == 1461196800000


def test_socket_options_contain_keepalive():
    client = Client(servers="http://localhost:4200")
    conn_kw = client.server_pool[server].pool.conn_kw
    assert (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) in conn_kw["socket_options"]


class HttpClientTest(TestCase):
    @patch(REQUEST, autospec=True)
    def test_uuid_serialization(self, request):
        client = Client(servers="localhost:4200")
        request.return_value = fake_response(200)

        uid = uuid.uuid4()
        client.sql("insert into my_table (str_col) values (?)", (uid,))

        data = json.loads(request.call_args[1]["data"])
        self.assertEqual(data["args"], [str(uid)])
        client.close()

    @patch(REQUEST, fake_request(duplicate_key_exception()))
    def test_duplicate_key_error(self):
        """
        Verify that an `IntegrityError` is raised on duplicate key errors,
        instead of the more general `ProgrammingError`.
        """
        client = Client(servers="localhost:4200")
        with self.assertRaises(IntegrityError) as cm:
            client.sql("INSERT INTO testdrive (foo) VALUES (42)")
        self.assertEqual(
            cm.exception.message,
            "DuplicateKeyException[A document with the "
            "same primary key exists already]",
        )


@patch(REQUEST, fail_sometimes)
class ThreadSafeHttpClientTest(TestCase):
    """
    Using a pool of 5 Threads to emit commands to the multiple servers through
    one Client-instance

    check if number of servers in _inactive_servers and _active_servers always
    equals the number of servers initially given.
    """

    servers = [
        "127.0.0.1:44209",
        "127.0.0.2:44209",
        "127.0.0.3:44209",
    ]
    num_threads = 5
    num_commands = 1000
    thread_timeout = 5.0  # seconds

    def __init__(self, *args, **kwargs):
        self.event = Event()
        self.err_queue = queue.Queue()
        super(ThreadSafeHttpClientTest, self).__init__(*args, **kwargs)

    def setUp(self):
        self.client = Client(self.servers)
        self.client.retry_interval = 0.2  # faster retry

    def tearDown(self):
        self.client.close()

    def _run(self):
        self.event.wait()  # wait for the others
        expected_num_servers = len(self.servers)
        for _ in range(self.num_commands):
            try:
                self.client.sql("select name from sys.cluster")
            except ConnectionError:
                pass
            try:
                with self.client._lock:
                    num_servers = len(self.client._active_servers) + len(
                        self.client._inactive_servers
                    )
                self.assertEqual(
                    expected_num_servers,
                    num_servers,
                    "expected %d but got %d"
                    % (expected_num_servers, num_servers),
                )
            except AssertionError:
                self.err_queue.put(sys.exc_info())

    def test_client_threaded(self):
        """
        Testing if lists of servers is handled correctly when client is used
        from multiple threads with some requests failing.

        **ATTENTION:** this test is probabilistic and does not ensure that the
        client is indeed thread-safe in all cases, it can only show that it
        withstands this scenario.
        """
        threads = [
            Thread(target=self._run, name=str(x))
            for x in range(self.num_threads)
        ]
        for thread in threads:
            thread.start()

        self.event.set()
        for t in threads:
            t.join(self.thread_timeout)

        if not self.err_queue.empty():
            self.assertTrue(
                False,
                "".join(
                    traceback.format_exception(*self.err_queue.get(block=False))
                ),
            )


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
        self.send_header("Content-Length", len(response))
        self.send_header("Content-Type", "application/json; charset=UTF-8")
        self.end_headers()
        self.wfile.write(response.encode("UTF-8"))

    do_POST = do_PUT = do_DELETE = do_HEAD = do_GET


class KeepAliveClientTest(TestCase):
    server_address = ("127.0.0.1", 65535)

    def __init__(self, *args, **kwargs):
        super(KeepAliveClientTest, self).__init__(*args, **kwargs)
        self.server_process = ForkProcess(target=self._run_server)

    def setUp(self):
        super(KeepAliveClientTest, self).setUp()
        self.client = Client(["%s:%d" % self.server_address])
        self.server_process.start()
        time.sleep(0.10)

    def tearDown(self):
        self.server_process.terminate()
        self.client.close()
        super(KeepAliveClientTest, self).tearDown()

    def _run_server(self):
        self.server = HTTPServer(
            self.server_address, ClientAddressRequestHandler
        )
        self.server.handle_request()

    def test_client_keepalive(self):
        for _ in range(10):
            result = self.client.sql("select * from fake")

            another_result = self.client.sql("select again from fake")
            self.assertEqual(result, another_result)


class ParamsTest(TestCase):
    def test_params(self):
        client = Client(["127.0.0.1:4200"], error_trace=True)
        parsed = urlparse(client.path)
        params = parse_qs(parsed.query)
        self.assertEqual(params["error_trace"], ["true"])
        client.close()

    def test_no_params(self):
        client = Client()
        self.assertEqual(client.path, "/_sql?types=true")
        client.close()


class RequestsCaBundleTest(TestCase):
    def test_open_client(self):
        os.environ["REQUESTS_CA_BUNDLE"] = CA_CERT_PATH
        try:
            Client("http://127.0.0.1:4200")
        except ProgrammingError:
            self.fail("HTTP not working with REQUESTS_CA_BUNDLE")
        finally:
            os.unsetenv("REQUESTS_CA_BUNDLE")
            os.environ["REQUESTS_CA_BUNDLE"] = ""

    def test_remove_certs_for_non_https(self):
        d = _remove_certs_for_non_https("https", {"ca_certs": 1})
        self.assertIn("ca_certs", d)

        kwargs = {"ca_certs": 1, "foobar": 2, "cert_file": 3}
        d = _remove_certs_for_non_https("http", kwargs)
        self.assertNotIn("ca_certs", d)
        self.assertNotIn("cert_file", d)
        self.assertIn("foobar", d)


class TimeoutRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP handler for use with TestingHTTPServer
    updates the shared counter and waits so that the client times out
    """

    def do_POST(self):
        self.server.SHARED["count"] += 1
        time.sleep(5)


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


class TestingHTTPServer(HTTPServer):
    """
    http server providing a shared dict
    """

    manager = multiprocessing.Manager()
    SHARED = manager.dict()
    SHARED["count"] = 0
    SHARED["usernameFromXUser"] = None
    SHARED["username"] = None
    SHARED["password"] = None
    SHARED["schema"] = None

    @classmethod
    def run_server(cls, server_address, request_handler_cls):
        cls(server_address, request_handler_cls).serve_forever()


class TestingHttpServerTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assertIsNotNone(self.request_handler)
        self.server_address = ("127.0.0.1", random.randint(65000, 65535))
        self.server_process = ForkProcess(
            target=TestingHTTPServer.run_server,
            args=(self.server_address, self.request_handler),
        )

    def setUp(self):
        self.server_process.start()
        self.wait_for_server()

    def wait_for_server(self):
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(self.server_address)
            except Exception:
                time.sleep(0.25)
            else:
                break

    def tearDown(self):
        self.server_process.terminate()

    def clientWithKwargs(self, **kwargs):
        return Client(["%s:%d" % self.server_address], timeout=1, **kwargs)


class RetryOnTimeoutServerTest(TestingHttpServerTestCase):
    request_handler = TimeoutRequestHandler

    def setUp(self):
        super().setUp()
        self.client = self.clientWithKwargs()

    def tearDown(self):
        super().tearDown()
        self.client.close()

    def test_no_retry_on_read_timeout(self):
        try:
            self.client.sql("select * from fake")
        except ConnectionError as e:
            self.assertIn(
                "Read timed out",
                e.message,
                msg="Error message must contain: Read timed out",
            )
        self.assertEqual(TestingHTTPServer.SHARED["count"], 1)


class TestDefaultSchemaHeader(TestingHttpServerTestCase):
    request_handler = SharedStateRequestHandler

    def setUp(self):
        super().setUp()
        self.client = self.clientWithKwargs(schema="my_custom_schema")

    def tearDown(self):
        self.client.close()
        super().tearDown()

    def test_default_schema(self):
        self.client.sql("SELECT 1")
        self.assertEqual(TestingHTTPServer.SHARED["schema"], "my_custom_schema")


class TestUsernameSentAsHeader(TestingHttpServerTestCase):
    request_handler = SharedStateRequestHandler

    def setUp(self):
        super().setUp()
        self.clientWithoutUsername = self.clientWithKwargs()
        self.clientWithUsername = self.clientWithKwargs(username="testDBUser")
        self.clientWithUsernameAndPassword = self.clientWithKwargs(
            username="testDBUser", password="test:password"
        )

    def tearDown(self):
        self.clientWithoutUsername.close()
        self.clientWithUsername.close()
        self.clientWithUsernameAndPassword.close()
        super().tearDown()

    def test_username(self):
        self.clientWithoutUsername.sql("select * from fake")
        self.assertEqual(TestingHTTPServer.SHARED["usernameFromXUser"], None)
        self.assertEqual(TestingHTTPServer.SHARED["username"], None)
        self.assertEqual(TestingHTTPServer.SHARED["password"], None)

        self.clientWithUsername.sql("select * from fake")
        self.assertEqual(
            TestingHTTPServer.SHARED["usernameFromXUser"], "testDBUser"
        )
        self.assertEqual(TestingHTTPServer.SHARED["username"], "testDBUser")
        self.assertEqual(TestingHTTPServer.SHARED["password"], None)

        self.clientWithUsernameAndPassword.sql("select * from fake")
        self.assertEqual(
            TestingHTTPServer.SHARED["usernameFromXUser"], "testDBUser"
        )
        self.assertEqual(TestingHTTPServer.SHARED["username"], "testDBUser")
        self.assertEqual(TestingHTTPServer.SHARED["password"], "test:password")


class TestCrateJsonEncoder(TestCase):
    def test_naive_datetime(self):
        data = dt.datetime.fromisoformat("2023-06-26T09:24:00.123")
        result = json_dumps(data)
        self.assertEqual(result, b"1687771440123")

    def test_aware_datetime(self):
        data = dt.datetime.fromisoformat("2023-06-26T09:24:00.123+02:00")
        result = json_dumps(data)
        self.assertEqual(result, b"1687764240123")
