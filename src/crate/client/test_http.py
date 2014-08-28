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
import time
import sys
from .compat import queue
from random import SystemRandom
import traceback
from unittest import TestCase
from mock import patch, MagicMock
from threading import Thread, Event
from multiprocessing import Process
import urllib3.exceptions

from .http import Client
from .exceptions import ConnectionError, ProgrammingError
from .compat import xrange, BaseHTTPServer, to_bytes


class FakeServerRaisingException(object):

    def __init__(self, *args, **kwargs):
        pass


class FakeServerRaisingGeneralException(FakeServerRaisingException):

    def request(self, method, path, data=None, stream=False, **kwargs):
        raise Exception("this shouldn't be raised")


class FakeServerRaisingMaxRetryError(FakeServerRaisingException):

    def request(self, method, path, data=None, stream=False, **kwargs):
        raise urllib3.exceptions.MaxRetryError(
                    None, path, "this shouldn't be raised")


class FakeServerErrorResponse(object):

    @property
    def status(self):
        raise NotImplemented

    @property
    def reason(self):
        raise NotImplemented

    content_type = "application/json"

    def __init__(self, *args, **kwargs):
        pass

    def request(self, method, path, data=None, stream=False, **kwargs):
        mock_response = MagicMock()
        mock_response.status = self.status
        mock_response.reason = self.reason
        mock_response.headers = {"content-type": self.content_type}
        return mock_response


class FakeServerServiceUnavailable(FakeServerErrorResponse):

    status = 503
    reason = "Service Unavailable"


class FakeServer50xResponse(FakeServerErrorResponse):

    counter = 0
    STATI = [200, 503]
    REASONS = ["Success", "Service Unavailable"]

    _status = 200
    _reason = "Success"

    @property
    def status(self):
        return self._status

    @property
    def reason(self):
        return self._reason

    def request(self, method, path, data=None, stream=False, **kwargs):
        self._reason = self.REASONS[self.counter % len(self.REASONS)]
        self._status = self.STATI[self.counter % len(self.STATI)]
        print(self.counter, self._status)
        self.counter += 1
        mock_response = MagicMock()
        mock_response.status = self._status
        mock_response.reason = self._reason
        mock_response.headers = {"content-type": self.content_type}
        return mock_response

class FakeServerUnauthorized(FakeServerErrorResponse):

    status = 401
    reason = "Unauthorized"
    content_type = "text/html"


class FakeServerBadBulkRequest(FakeServerErrorResponse):

    def request(self, method, path, data=None, stream=False, **kwargs):
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.reason = "Bad Request"
        mock_response.headers = {"content-type": self.content_type}
        mock_response.data = json.dumps({
                        "results": [
                            {
                                "rowcount": 1
                            },
                            {
                                "error_message": "an error occured"
                            },
                            {
                                "error_message": "another error"
                            },
                            {
                                "error_message": ""
                            },
                            {
                                "error_message": None
                            }
                        ]}).encode()
        return mock_response


class FakeServerFailSometimes(object):

    _rnd = SystemRandom(time.time())

    def request(self, method, path, data=None, stream=False, **kwargs):
        mock_response = MagicMock()
        if int(self._rnd.random() * 100) % 10 == 0:
            raise urllib3.exceptions.MaxRetryError(None, path, '')
        else:
            return mock_response


class FakeRedirectServer(object):

    """ server that generates a response with redirect location to

        http://localhost:4201
    """

    def request(self, method, path, data=None, stream=False, **kwargs):
        resp = MagicMock()
        resp.status = 307
        resp.get_redirect_location.return_value = 'http://localhost:4201'
        return resp


class HttpClientTest(TestCase):

    def test_no_connection_exception(self):
        client = Client()
        self.assertRaises(ConnectionError, client.sql, 'select 1')

    @patch('crate.client.http.Server', FakeServerRaisingGeneralException)
    def test_http_error_is_re_raised(self):
        client = Client()
        self.assertRaises(ProgrammingError, client.sql, 'select 1')

    @patch('crate.client.http.Server', FakeServerRaisingGeneralException)
    def test_programming_error_contains_http_error_response_content(self):
        client = Client()
        try:
            client.sql('select 1')
        except ProgrammingError as e:
            self.assertEquals("this shouldn't be raised", e.message)
        else:
            self.assertTrue(False)

    @patch('crate.client.http.Server', FakeServer50xResponse)
    def test_server_error_50x(self):
        client = Client(servers="localhost:4200 localhost:4201")
        client.sql('select 1')
        client.sql('select 2')
        try:
            client.sql('select 3')
        except ProgrammingError as e:
            self.assertEqual("No more Servers available, exception from last server: Service Unavailable",
                             e.message)
        self.assertEqual([], list(client._active_servers))

    def test_connect(self):
        client = Client(servers="localhost:4200 localhost:4201")
        self.assertEqual(client._active_servers,
                         ["http://localhost:4200", "http://localhost:4201"])

        client = Client(servers="localhost:4200")
        self.assertEqual(client._active_servers, ["http://localhost:4200"])

        client = Client(servers=["localhost:4200"])
        self.assertEqual(client._active_servers, ["http://localhost:4200"])

        client = Client(servers=["localhost:4200", "127.0.0.1:4201"])
        self.assertEqual(client._active_servers,
                         ["http://localhost:4200", "http://127.0.0.1:4201"])

    def test_redirect_handling(self):
        client = Client(servers='localhost:4200')
        client.server_pool['http://localhost:4200'] = FakeRedirectServer()
        try:
            client.blob_get('blobs', 'fake_digest')
        except ProgrammingError:
            # 4201 gets added to serverpool but isn't available
            pass
        self.assertEqual(
            ['http://localhost:4200', 'http://localhost:4201'],
            sorted(list(client.server_pool.keys()))
        )

    @patch('crate.client.http.Server', FakeServerRaisingMaxRetryError)
    def test_server_infos(self):
        client = Client(servers="localhost:4200 localhost:4201")
        self.assertRaises(ConnectionError,
                          client.server_infos,
                          client._get_server())

    @patch('crate.client.http.Server', FakeServerServiceUnavailable)
    def test_server_infos_503(self):
        client = Client(servers="localhost:4200 localhost:4201")
        self.assertRaises(ConnectionError,
                          client.server_infos,
                          client._get_server())

    @patch('crate.client.http.Server', FakeServerUnauthorized)
    def test_server_infos_401(self):
        client = Client(servers="localhost:4200 localhost:4201")
        try:
            client.server_infos(client._get_server())
        except ProgrammingError as e:
            self.assertEqual("401 Client Error: Unauthorized", e.message)
        else:
            self.assertTrue(False, msg="Exception should have been raised")

    @patch('crate.client.http.Server', FakeServerBadBulkRequest)
    def test_bad_bulk_400(self):
        client = Client(servers="localhost:4200")
        try:
            client.sql("Insert into users (name) values(?)", bulk_parameters=[["douglas"], ["monthy"]])
        except ProgrammingError as e:
            self.assertEqual("an error occured\nanother error", e.message)
        else:
            self.assertTrue(False, msg="Exception should have been raised")


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
        super(ThreadSafeHttpClientTest, self).setUp()
        self.client = Client(self.servers)
        self.client.retry_interval = 0.0001  # faster retry
        for server in list(self.client.server_pool.keys()):
            self.client.server_pool[server] = FakeServerFailSometimes()

    def _run(self):
        self.event.wait()  # wait for the others
        expected_num_servers = len(self.servers)
        for x in xrange(self.num_commands):
            try:
                self.client._request('GET', "/")
            except (ConnectionError, ProgrammingError):
                pass
            try:
                with self.client._lock:
                    num_servers = len(self.client._active_servers) + len(self.client._inactive_servers)
                self.assertEquals(
                    expected_num_servers,
                    num_servers,
                    "expected %d but got %d" % (expected_num_servers, num_servers)
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
        pool = [
            Thread(target=self._run, name=str(x))
            for x in xrange(self.num_threads)
        ]
        for thread in pool:
            thread.start()

        self.event.set()
        while True:
            try:
                thread = pool.pop()
                thread.join(self.thread_timeout)
            except IndexError:
                break

        if not self.err_queue.empty():
            self.assertTrue(
                False,
                "".join(
                    traceback.format_exception(
                        *self.err_queue.get(block=False)
                    )
                )
            )


class ClientAddressRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    http handler for use with BaseHTTPServer

    returns client host and port in crate-conform-responses
    """
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        content_length = self.headers.get("content-length")
        if content_length:
            self.rfile.read(int(content_length))
        response = json.dumps({
            "cols": ["host", "port"],
            "rows": [
                self.client_address[0],
                self.client_address[1]
            ],
            "rowCount": 1,
        })
        self.send_response(200)
        self.send_header("Content-Length", len(response))
        self.send_header("Content-Type", "application/json; charset=UTF-8")
        self.end_headers()
        self.wfile.write(to_bytes(response, 'UTF-8'))

    do_POST = do_PUT = do_DELETE = do_HEAD = do_GET


class KeepAliveClientTest(TestCase):

    server_address = ("127.0.0.1", 65535)

    def __init__(self, *args, **kwargs):
        super(KeepAliveClientTest, self).__init__(*args, **kwargs)
        self.server_process = Process(target=self._run_server)

    def setUp(self):
        super(KeepAliveClientTest, self).setUp()
        self.client = Client(["%s:%d" % self.server_address])
        self.server_process.start()
        time.sleep(.10)

    def tearDown(self):
        self.server_process.terminate()
        super(KeepAliveClientTest, self).tearDown()

    def _run_server(self):
        self.server = BaseHTTPServer.HTTPServer(self.server_address, ClientAddressRequestHandler)
        self.server.handle_request()

    def test_client_keepalive(self):
        for x in range(10):
            result = self.client.sql("select * from fake")

            another_result = self.client.sql("select again from fake")
            self.assertEqual(result, another_result)


class ParamsTest(TestCase):

    def test_params(self):
        client = Client(['127.0.0.1:4200'], error_trace=True)
        from six.moves.urllib.parse import urlparse, parse_qs
        parsed = urlparse(client.path)
        params = parse_qs(parsed.query)
        self.assertEquals(params["error_trace"], ["1"])

    def test_no_params(self):
        client = Client(['127.0.0.1:4200'])
        self.assertEqual(client.path, "_sql")
