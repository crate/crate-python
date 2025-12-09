import io
import ssl
import tempfile
from unittest.mock import patch

import urllib3

from crate.client.http import _update_pool_kwargs_for_ssl_minimum_version
from crate.client.http import super_len


def test_super_len_all():
    assert super_len([1, 2]) == 2
    assert super_len("abc") == 3
    assert super_len((1, 2, 3)) == 3

    class len_obj:
        def __init__(self, len_f):
            self.len = len_f

    assert super_len(len_obj(5)) == 5

    data = b"somedata"
    with tempfile.TemporaryFile() as f:
        f.write(data)
        f.flush()
        assert super_len(f) == len(data)

    class bad_fileno:
        def fileno(self):
            raise io.UnsupportedOperation

    assert super_len(bad_fileno()) is None

    class bad_fileno_with_getvalue:
        def fileno(self):
            raise io.UnsupportedOperation

        def getvalue(self):
            return b"abcde"

    assert super_len(bad_fileno_with_getvalue()) == 5

    buf = io.BytesIO(b"123456")
    assert super_len(buf) == 6

    class getvalue_obj:
        def getvalue(self):
            return "abcdef"

    assert super_len(getvalue_obj()) == 6

    class Empty:
        pass

    assert super_len(Empty()) is None


def test_update_pool_kwargs_for_ssl_minimum_version():
    """Test that the ssl_minimum_version is set correctly in the kwargs"""
    with patch.object(urllib3, "__version__", "2.0.0"):
        kwargs = {}
        _update_pool_kwargs_for_ssl_minimum_version(
            "https://example.com", kwargs
        )
        assert (
            kwargs.get("ssl_minimum_version")
            == ssl.TLSVersion.MINIMUM_SUPPORTED
        )

        # not https
        kwargs = {}
        _update_pool_kwargs_for_ssl_minimum_version(
            "http://example.com", kwargs
        )
        assert "ssl_minimum_version" not in kwargs

    with patch.object(urllib3, "__version__", "1.26.0"):
        kwargs = {}
        _update_pool_kwargs_for_ssl_minimum_version(
            "https://example.com", kwargs
        )
        assert "ssl_minimum_version" not in kwargs
