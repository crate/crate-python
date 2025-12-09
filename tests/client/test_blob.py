from io import BytesIO
from unittest.mock import MagicMock

import pytest

from crate.client.blob import BlobContainer


def test_container():
    """Verify a container can be instantiated."""
    expected_name = "somename"
    container = BlobContainer(expected_name, MagicMock())
    assert container.container_name == expected_name


def test_container_digest():
    digester = BlobContainer("", MagicMock())._compute_digest

    # sha1 of some_data.
    some_data, expected_digest = (
        b"some_data_123456",
        "51bea75c0f26998083ef3717a489f2dc05818e8d",
    )
    result = digester(BytesIO(some_data))
    assert result == expected_digest

    with pytest.raises(AttributeError):
        digester("someundigestabledata")


def test_container_put():
    """Test the logic of container put method"""
    some_data, expected_digest = (
        b"some_data_123456",
        "51bea75c0f26998083ef3717a489f2dc05818e8d",
    )
    expected_container_name = "somename"
    m = MagicMock()
    m.client.blob_put = MagicMock()
    container = BlobContainer(expected_container_name, m)

    result = container.put(BytesIO(some_data))
    assert result == expected_digest

    new_digest = "asdfn"
    data = BytesIO(some_data)
    result = container.put(data, digest=new_digest)
    assert isinstance(result, MagicMock)
    assert m.client.blob_put.call_count == 2
    assert m.client.blob_put.call_args.args == (
        expected_container_name,
        new_digest,
        data,
    )
