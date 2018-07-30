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
import socket
import multiprocessing
import sys
import os
import queue
import random
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import TestCase
from unittest.mock import patch, MagicMock
from threading import Thread, Event
from multiprocessing import Process
from decimal import Decimal
import datetime as dt
import urllib3.exceptions
from base64 import b64decode
from urllib.parse import urlparse, parse_qs
from setuptools.ssl_support import find_ca_bundle

from .http import Client, _remove_certs_for_non_https
from .exceptions import ConnectionError, ProgrammingError


REQUEST = 'crate.client.http.Server.request'
CA_CERT_PATH = find_ca_bundle()


def fake_request(response=None):
    def request(*args, **kwargs):
        if isinstance(response, list):
            resp = response.pop(0)
            response.append(resp)
            return resp
        elif response:
            return response
        else:
            return MagicMock(spec=urllib3.response.HTTPResponse)
    return request


def fake_response(status, reason=None, content_type='application/json'):
    m = MagicMock(spec=urllib3.response.HTTPResponse)
    m.status = status
    m.reason = reason or ''
    m.headers = {'content-type': content_type}
    return m


def fake_redirect(location):
    m = fake_response(307)
    m.get_redirect_location.return_value = location
    return m


def bad_bulk_response():
    r = fake_response(400, 'Bad Request')
    r.data = json.dumps({
        "results": [
            {"rowcount": 1},
            {"error_message": "an error occured"},
            {"error_message": "another error"},
            {"error_message": ""},
            {"error_message": None}
        ]}).encode()
    return r


def fail_sometimes(*args, **kwargs):
    if random.randint(1, 100) % 10 == 0:
        raise urllib3.exceptions.MaxRetryError(None, '/_sql', '')
    return fake_response(200)


class HttpClientTest(TestCase):

    @patch(REQUEST, fake_request([fake_response(200),
                                  fake_response(104, 'Connection reset by peer'),
                                  fake_response(503, 'Service Unavailable')]))
    def test_connection_reset_exception(self):
        client = Client(servers="localhost:4200")
        client.sql('select 1')
        client.sql('select 2')
        self.assertEqual(['http://localhost:4200'], list(client._active_servers))
        try:
            client.sql('select 3')
        except ProgrammingError:
            self.assertEqual([], list(client._active_servers))
        else:
            self.assertTrue(False)
        finally:
            client.close()

    def test_no_connection_exception(self):
        client = Client()
        self.assertRaises(ConnectionError, client.sql, 'select foo')

    @patch(REQUEST)
    def test_http_error_is_re_raised(self, request):
        request.side_effect = Exception

        client = Client()
        self.assertRaises(ProgrammingError, client.sql, 'select foo')

    @patch(REQUEST)
    def test_programming_error_contains_http_error_response_content(self, request):
        request.side_effect = Exception("this shouldn't be raised")

        client = Client()
        try:
            client.sql('select 1')
        except ProgrammingError as e:
            self.assertEqual("this shouldn't be raised", e.message)
        else:
            self.assertTrue(False)
        finally:
            client.close()

    @patch(REQUEST, fake_request([fake_response(200),
                                  fake_response(503, 'Service Unavailable')]))
    def test_server_error_50x(self):
        client = Client(servers="localhost:4200 localhost:4201")
        client.sql('select 1')
        client.sql('select 2')
        try:
            client.sql('select 3')
        except ProgrammingError as e:
            self.assertEqual("No more Servers available, " +
                             "exception from last server: Service Unavailable",
                             e.message)
            self.assertEqual([], list(client._active_servers))
        else:
            self.assertTrue(False)
        finally:
            client.close()

    def test_connect(self):
        client = Client(servers="localhost:4200 localhost:4201")
        self.assertEqual(client._active_servers,
                         ["http://localhost:4200", "http://localhost:4201"])
        client.close()

        client = Client(servers="localhost:4200")
        self.assertEqual(client._active_servers, ["http://localhost:4200"])
        client.close()

        client = Client(servers=["localhost:4200"])
        self.assertEqual(client._active_servers, ["http://localhost:4200"])
        client.close()

        client = Client(servers=["localhost:4200", "127.0.0.1:4201"])
        self.assertEqual(client._active_servers,
                         ["http://localhost:4200", "http://127.0.0.1:4201"])
        client.close()

    @patch(REQUEST, fake_request(fake_redirect('http://localhost:4201')))
    def test_redirect_handling(self):
        client = Client(servers='localhost:4200')
        try:
            client.blob_get('blobs', 'fake_digest')
        except ProgrammingError:
            # 4201 gets added to serverpool but isn't available
            # that's why we run into an infinite recursion
            # exception message is: maximum recursion depth exceeded
            pass
        self.assertEqual(
            ['http://localhost:4200', 'http://localhost:4201'],
            sorted(list(client.server_pool.keys()))
        )
        # the new non-https server must not contain any SSL only arguments
        # regression test for github issue #179/#180
        self.assertEqual(
            {},
            client.server_pool['http://localhost:4201'].pool.conn_kw
        )
        client.close()

    @patch(REQUEST)
    def test_server_infos(self, request):
        request.side_effect = urllib3.exceptions.MaxRetryError(
            None, '/', "this shouldn't be raised")
        client = Client(servers="localhost:4200 localhost:4201")
        self.assertRaises(
            ConnectionError, client.server_infos, 'http://localhost:4200')
        client.close()

    @patch(REQUEST, fake_request(fake_response(503)))
    def test_server_infos_503(self):
        client = Client(servers="localhost:4200")
        self.assertRaises(
            ConnectionError, client.server_infos, 'http://localhost:4200')
        client.close()

    @patch(REQUEST, fake_request(
        fake_response(401, 'Unauthorized', 'text/html')))
    def test_server_infos_401(self):
        client = Client(servers="localhost:4200")
        try:
            client.server_infos('http://localhost:4200')
        except ProgrammingError as e:
            self.assertEqual("401 Client Error: Unauthorized", e.message)
        else:
            self.assertTrue(False, msg="Exception should have been raised")
        finally:
            client.close()

    @patch(REQUEST, fake_request(bad_bulk_response()))
    def test_bad_bulk_400(self):
        client = Client(servers="localhost:4200")
        try:
            client.sql("Insert into users (name) values(?)",
                       bulk_parameters=[["douglas"], ["monthy"]])
        except ProgrammingError as e:
            self.assertEqual("an error occured\nanother error", e.message)
        else:
            self.assertTrue(False, msg="Exception should have been raised")
        finally:
            client.close()

    @patch(REQUEST, autospec=True)
    def test_decimal_serialization(self, request):
        client = Client(servers="localhost:4200")
        request.return_value = fake_response(200)

        dec = Decimal(0.12)
        client.sql('insert into users (float_col) values (?)', (dec,))

        data = json.loads(request.call_args[1]['data'])
        self.assertEqual(data['args'], [str(dec)])
        client.close()

    @patch(REQUEST, autospec=True)
    def test_datetime_is_converted_to_ts(self, request):
        client = Client(servers="localhost:4200")
        request.return_value = fake_response(200)

        datetime = dt.datetime(2015, 2, 28, 7, 31, 40)
        client.sql('insert into users (dt) values (?)', (datetime,))

        # convert string to dict
        # because the order of the keys isn't deterministic
        data = json.loads(request.call_args[1]['data'])
        self.assertEqual(data['args'], [1425108700000])
        client.close()

    @patch(REQUEST, autospec=True)
    def test_date_is_converted_to_ts(self, request):
        client = Client(servers="localhost:4200")
        request.return_value = fake_response(200)

        day = dt.date(2016, 4, 21)
        client.sql('insert into users (dt) values (?)', (day,))
        data = json.loads(request.call_args[1]['data'])
        self.assertEqual(data['args'], [1461196800000])
        client.close()


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
        self.client.retry_interval = 0.1  # faster retry

    def tearDown(self):
        self.client.close()

    def _run(self):
        self.event.wait()  # wait for the others
        expected_num_servers = len(self.servers)
        for x in range(self.num_commands):
            try:
                self.client.sql('select name from sys.cluster')
            except ConnectionError:
                pass
            try:
                with self.client._lock:
                    num_servers = len(self.client._active_servers) + \
                        len(self.client._inactive_servers)
                self.assertEqual(
                    expected_num_servers,
                    num_servers,
                    "expected %d but got %d" % (expected_num_servers,
                                                num_servers)
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
            self.assertTrue(False, "".join(
                traceback.format_exception(*self.err_queue.get(block=False))))


class ClientAddressRequestHandler(BaseHTTPRequestHandler):
    """
    http handler for use with HTTPServer

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
        self.wfile.write(response.encode('UTF-8'))

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
        self.client.close()
        super(KeepAliveClientTest, self).tearDown()

    def _run_server(self):
        self.server = HTTPServer(self.server_address,
                                 ClientAddressRequestHandler)
        self.server.handle_request()

    def test_client_keepalive(self):
        for x in range(10):
            result = self.client.sql("select * from fake")

            another_result = self.client.sql("select again from fake")
            self.assertEqual(result, another_result)


class ParamsTest(TestCase):

    def test_params(self):
        client = Client(['127.0.0.1:4200'], error_trace=True)
        parsed = urlparse(client.path)
        params = parse_qs(parsed.query)
        self.assertEqual(params["error_trace"], ["true"])
        client.close()

    def test_no_params(self):
        client = Client()
        self.assertEqual(client.path, "/_sql")
        client.close()


class RequestsCaBundleTest(TestCase):

    def test_open_client(self):
        os.environ["REQUESTS_CA_BUNDLE"] = CA_CERT_PATH
        try:
            Client('http://127.0.0.1:4200')
        except ProgrammingError:
            self.fail("HTTP not working with REQUESTS_CA_BUNDLE")
        finally:
            os.unsetenv('REQUESTS_CA_BUNDLE')
            os.environ["REQUESTS_CA_BUNDLE"] = ''

    def test_remove_certs_for_non_https(self):
        d = _remove_certs_for_non_https('https', {"ca_certs": 1})
        self.assertTrue('ca_certs' in d)

        kwargs = {'ca_certs': 1, 'foobar': 2, 'cert_file': 3}
        d = _remove_certs_for_non_https('http', kwargs)
        self.assertTrue('ca_certs' not in d)
        self.assertTrue('cert_file' not in d)
        self.assertTrue('foobar' in d)


class TimeoutRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP handler for use with TestingHTTPServer
    updates the shared counter and waits so that the client times out
    """

    def do_POST(self):
        self.server.SHARED['count'] += 1
        time.sleep(5)


class SharedStateRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP handler for use with TestingHTTPServer
    sets the shared state of the server and returns an empty response
    """

    def do_POST(self):
        self.server.SHARED['count'] += 1
        self.server.SHARED['schema'] = self.headers.get('Default-Schema')

        if self.headers.get('Authorization') is not None:
            auth_header = self.headers['Authorization'].replace('Basic ', '')
            credentials = b64decode(auth_header).decode('utf-8').split(":", 1)
            self.server.SHARED['username'] = credentials[0]
            if len(credentials) > 1 and credentials[1]:
                self.server.SHARED['password'] = credentials[1]
            else:
                self.server.SHARED['password'] = None
        else:
            self.server.SHARED['username'] = None

        if self.headers.get('X-User') is not None:
            self.server.SHARED['usernameFromXUser'] = self.headers['X-User']
        else:
            self.server.SHARED['usernameFromXUser'] = None

        # send empty response
        response = '{}'
        self.send_response(200)
        self.send_header("Content-Length", len(response))
        self.send_header("Content-Type", "application/json; charset=UTF-8")
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))


class TestingHTTPServer(HTTPServer):
    """
    http server providing a shared dict
    """
    manager = multiprocessing.Manager()
    SHARED = manager.dict()
    SHARED['count'] = 0
    SHARED['usernameFromXUser'] = None
    SHARED['username'] = None
    SHARED['password'] = None
    SHARED['schema'] = None

    @classmethod
    def run_server(cls, server_address, request_handler_cls):
        cls(server_address, request_handler_cls).serve_forever()


class TestingHttpServerTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assertIsNotNone(self.request_handler)
        self.server_address = ('127.0.0.1', random.randint(65000, 65535))
        self.server_process = Process(target=TestingHTTPServer.run_server,
                                      args=(self.server_address, self.request_handler))

    def setUp(self):
        self.server_process.start()
        self.wait_for_server()

    def wait_for_server(self):
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(self.server_address)
            except Exception:
                time.sleep(.25)
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
            self.assertTrue('Read timed out' in e.message,
                            msg='Error message must contain: Read timed out')
        self.assertEqual(TestingHTTPServer.SHARED['count'], 1)


class TestDefaultSchemaHeader(TestingHttpServerTestCase):

    request_handler = SharedStateRequestHandler

    def setUp(self):
        super().setUp()
        self.client = self.clientWithKwargs(schema='my_custom_schema')

    def tearDown(self):
        super().tearDown()
        self.client.close()

    def test_default_schema(self):
        self.client.sql('SELECT 1')
        self.assertEqual(TestingHTTPServer.SHARED['schema'], 'my_custom_schema')


class TestUsernameSentAsHeader(TestingHttpServerTestCase):

    request_handler = SharedStateRequestHandler

    def setUp(self):
        super().setUp()
        self.clientWithoutUsername = self.clientWithKwargs()
        self.clientWithUsername = self.clientWithKwargs(username='testDBUser')
        self.clientWithUsernameAndPassword = self.clientWithKwargs(username='testDBUser',
                                                                   password='test:password')

    def tearDown(self):
        self.clientWithoutUsername.close()
        self.clientWithUsername.close()
        self.clientWithUsernameAndPassword.close()
        super().tearDown()

    def test_username(self):
        self.clientWithoutUsername.sql("select * from fake")
        self.assertEqual(TestingHTTPServer.SHARED['usernameFromXUser'], None)
        self.assertEqual(TestingHTTPServer.SHARED['username'], None)
        self.assertEqual(TestingHTTPServer.SHARED['password'], None)

        self.clientWithUsername.sql("select * from fake")
        self.assertEqual(TestingHTTPServer.SHARED['usernameFromXUser'], 'testDBUser')
        self.assertEqual(TestingHTTPServer.SHARED['username'], 'testDBUser')
        self.assertEqual(TestingHTTPServer.SHARED['password'], None)

        self.clientWithUsernameAndPassword.sql("select * from fake")
        self.assertEqual(TestingHTTPServer.SHARED['usernameFromXUser'], 'testDBUser')
        self.assertEqual(TestingHTTPServer.SHARED['username'], 'testDBUser')
        self.assertEqual(TestingHTTPServer.SHARED['password'], 'test:password')
