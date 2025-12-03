from crate.client import Error
from crate.client.exceptions import BlobException


def test_error_with_msg():
    err = Error("foo")
    assert str(err) == "foo"


def test_error_with_error_trace():
    err = Error("foo", error_trace="### TRACE ###")
    assert str(err), "foo\n### TRACE ###"

def test_blob_exception():
    err = BlobException(table="sometable", digest="somedigest")
    assert str(err) == "BlobException('sometable/somedigest)'"
