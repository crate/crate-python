import io
import tempfile

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
