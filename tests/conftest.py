from unittest.mock import MagicMock

import pytest

import crate


@pytest.fixture
def mocked_connection():
    """
    Returns a crate connection with a mocked client

    Example:
        def test_conn(mocked_connection):
            cursor = mocked_connection.cursor()
            cursor.execute("select 1")
    """
    yield crate.client.connect(client=MagicMock(spec=crate.client.http.Client))
