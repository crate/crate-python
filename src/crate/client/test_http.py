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

from requests.exceptions import HTTPError, ConnectionError as RequestsConnectionError


from .http import Client
from .exceptions import ConnectionError, ProgrammingError
from .compat import xrange, BaseHTTPServer, to_bytes


class FakeSession(object):
    def request(self, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.content = "this shouldn't be raised"
        raise HTTPError(response=mock_response)


class FakeSessionLazyRaise(object):
    def request(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.content = "this shouldn't be raised"

        def raise_for_status():
            raise HTTPError(response=mock_response)
        mock_response.raise_for_status = raise_for_status
        return mock_response


class FakeSessionFailSometimes(object):
    _rnd = SystemRandom(time.time())

    def request(self, *args, **kwargs):
        mock_response = MagicMock()
        if int(self._rnd.random()*100) % 10 == 0:
            raise RequestsConnectionError()
        else:
            return mock_response


class HttpClientTest(TestCase):

    def test_no_connection_exception(self):
        client = Client()
        self.assertRaises(ConnectionError, client.sql, 'select 1')

    @patch('requests.sessions.Session', FakeSession)
    def test_http_error_is_re_raised(self):
        client = Client()
        self.assertRaises(ProgrammingError, client.sql, 'select 1')

    @patch('requests.sessions.Session', FakeSession)
    def test_programming_error_contains_http_error_response_content(self):
        client = Client()
        try:
            client.sql('select 1')
        except ProgrammingError as e:
            self.assertEquals("this shouldn't be raised", e.message)
        else:
            self.assertTrue(False)

    @patch('requests.sessions.Session', FakeSessionLazyRaise)
    def test_http_error_is_re_raised_in_raise_for_status(self):
        client = Client()
        self.assertRaises(ProgrammingError, client.sql, 'select 1')

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


class ThreadSafeHttpClientTest(TestCase):
    """
    Using a pool of 5 Threads to emit commands to the multiple servers through one Client-instance

    check if number of servers in _inactive_servers and _active_servers always euqals the number
    of servers initially given.
    """
    servers = [
        "127.0.0.1:44200",
        "127.0.0.2:44200",
        "127.0.0.3:44200",
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
        self.client._session = FakeSessionFailSometimes()  # patch the clients session

    def _run(self):
        self.event.wait()  # wait for the others
        expected_num_servers = len(self.servers)
        for x in xrange(self.num_commands):
            try:
                self.client._request('GET', "/")
            except RequestsConnectionError:
                pass
            try:
                with self.client._lock:
                    num_servers = len(self.client._active_servers) + len(self.client._inactive_servers)
                self.assertEquals(
                    expected_num_servers,
                    num_servers,
                    "expected %d but got %d" % (expected_num_servers, num_servers)
                )
            except AssertionError as e:
                self.err_queue.put(sys.exc_info())

    def test_client_threaded(self):
        """
        Testing if lists of servers is handled correctly when client is used from multiple threads
        with some requests failing.

        **ATTENTION:** this test is probabilistic and does not ensure that the client is
        indeed thread-safe in all cases, it can only show that it withstands this scenario.
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
