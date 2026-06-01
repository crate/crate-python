import doctest
from pprint import pprint

from tests.client.settings import assets_path

from .conftest import HttpsServer, crate_host


def cprint(s):
    if isinstance(s, bytes):
        s = s.decode("utf-8")
    print(s)  # noqa: T201


def test_docs(doctest_node, https_server):
    flags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    globs = {
        "pprint": pprint,
        "print": cprint,
        "crate_host": crate_host,
        "https_host": f"https://{HttpsServer.HOST}:{HttpsServer.PORT}",
        "cacert_valid": assets_path("pki/cacert_valid.pem"),
        "cacert_invalid": assets_path("pki/cacert_invalid.pem"),
        "clientcert_valid": assets_path("pki/client_valid.pem"),
        "clientcert_invalid": assets_path("pki/client_invalid.pem"),
    }

    def test(path):
        failures, tests = doctest.testfile(path, optionflags=flags, globs=globs)
        assert not failures

    test("../docs/by-example/connection.rst")
    test("../docs/by-example/cursor.rst")
    test("../docs/by-example/http.rst")
    test("../docs/by-example/client.rst")
    test("../docs/by-example/blob.rst")
    test("../docs/by-example/https.rst")
