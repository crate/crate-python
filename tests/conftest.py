import urllib3
from unittest.mock import MagicMock

import pytest

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
            mocked_connection.client.sql.assert_called_once_with(statement, 1, None)
    """
    yield crate.client.connect(client=MagicMock(spec=crate.client.http.Client))
