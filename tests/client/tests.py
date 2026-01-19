import doctest
import sys
import unittest

from .layer import (
    HttpsTestServerLayer,
    ensure_cratedb_layer,
    setUpCrateLayerBaseline,
    setUpWithHttps,
    tearDownDropEntitiesBaseline,
)


def test_suite():
    suite = unittest.TestSuite()
    flags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS

    # Unit tests.
    suite.addTest(doctest.DocTestSuite("crate.client.connection"))
    suite.addTest(doctest.DocTestSuite("crate.client.http"))

    if sys.version_info >= (3, 10):
        # This suite includes converter tests,
        # which are only available with Python 3.10 and newer.
        s = doctest.DocFileSuite(
            "docs/by-example/connection.rst",
            "docs/by-example/cursor.rst",
            module_relative=False,
            optionflags=flags,
            encoding="utf-8",
        )
        suite.addTest(s)

    s = doctest.DocFileSuite(
        "docs/by-example/https.rst",
        module_relative=False,
        setUp=setUpWithHttps,
        optionflags=flags,
        encoding="utf-8",
    )
    s.layer = HttpsTestServerLayer()
    suite.addTest(s)

    # Integration tests.
    layer = ensure_cratedb_layer()

    s = doctest.DocFileSuite(
        "docs/by-example/http.rst",
        "docs/by-example/client.rst",
        "docs/by-example/blob.rst",
        module_relative=False,
        setUp=setUpCrateLayerBaseline,
        tearDown=tearDownDropEntitiesBaseline,
        optionflags=flags,
        encoding="utf-8",
    )
    s.layer = layer
    suite.addTest(s)

    return suite
