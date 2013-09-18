
from unittest import TestCase
from mock import patch, MagicMock

from requests.exceptions import HTTPError

from .http import Client
from .exceptions import ConnectionError, ProgrammingError


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
