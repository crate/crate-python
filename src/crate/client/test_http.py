import time
import sys
from .compat import queue
from random import SystemRandom
import traceback
from unittest import TestCase
from mock import patch, MagicMock
from threading import Thread, Event

from requests.exceptions import HTTPError, ConnectionError as RequestsConnectionError


from .http import Client
from .exceptions import ConnectionError, ProgrammingError
from .compat import xrange


def fake_request(*args, **kwargs):
    mock_response = MagicMock()
    mock_response.content = "this shouldn't be raised"
    raise HTTPError(response=mock_response)


def fake_request_lazy_raise(*args, **kwargs):
    mock_response = MagicMock()
    mock_response.content = "this shouldn't be raised"

    def raise_for_status():
        raise HTTPError(response=mock_response)
    mock_response.raise_for_status = raise_for_status
    return mock_response


_rnd = SystemRandom(time.time())
def fail_sometimes_fake_request(*args, **kwargs):
    mock_response = MagicMock()
    if int(_rnd.random()*100) % 10 == 0:
        raise RequestsConnectionError()
    else:
        return mock_response


class HttpClientTest(TestCase):

    def test_no_connection_exception(self):
        client = Client()
        self.assertRaises(ConnectionError, client.sql, 'select 1')

    @patch('requests.request', fake_request)
    def test_http_error_is_re_raised(self):
        client = Client()
        self.assertRaises(ProgrammingError, client.sql, 'select 1')

    @patch('requests.request', fake_request)
    def test_programming_error_contains_http_error_response_content(self):
        client = Client()
        try:
            client.sql('select 1')
        except ProgrammingError as e:
            self.assertEquals("this shouldn't be raised", e.message)
        else:
            self.assertTrue(False)

    @patch('requests.request', fake_request_lazy_raise)
    def test_http_error_is_re_raised_in_raise_for_status(self):
        client = Client()
        self.assertRaises(ProgrammingError, client.sql, 'select 1')


class ThreadSafeHttpClientTest(TestCase):
    """
    Using a pool of 5 Threads to emit commands to the multiple servers through one Client-instance

    check if number of servers in _inactive_servers and _active_servers always euqals the number
    of servers initially given.
    """
    servers = [
        "127.0.0.1:9200",
        "127.0.0.2:9200",
        "127.0.0.3:9200",
    ]
    num_threads = 5
    num_commands = 1000
    thread_timeout = 5.0  # seconds

    def __init__(self, *args, **kwargs):
        self.client = Client(self.servers)
        self.client.retry_interval = 0.0001  # faster retry
        self.event = Event()
        self.err_queue = queue.Queue()
        super(ThreadSafeHttpClientTest, self).__init__(*args, **kwargs)

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

    @patch("requests.request", fail_sometimes_fake_request)
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
