import doctest
import unittest

from .test_connection import ConnectionTest
from .test_cursor import CursorTest
from .test_http import HttpClientTest, KeepAliveClientTest, ThreadSafeHttpClientTest, ParamsTest, \
    RetryOnTimeoutServerTest, RequestsCaBundleTest, TestUsernameSentAsHeader, TestCrateJsonEncoder, \
    TestDefaultSchemaHeader
from .layer import makeSuite, setUpWithHttps, HttpsTestServerLayer, setUpCrateLayerBaseline, \
    tearDownDropEntitiesBaseline, ensure_cratedb_layer
from .test_result import BulkOperationTest


def test_suite():
    suite = unittest.TestSuite()
    flags = (doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)

    # Unit tests.
    suite.addTest(makeSuite(CursorTest))
    suite.addTest(makeSuite(HttpClientTest))
    suite.addTest(makeSuite(KeepAliveClientTest))
    suite.addTest(makeSuite(ThreadSafeHttpClientTest))
    suite.addTest(makeSuite(ParamsTest))
    suite.addTest(makeSuite(ConnectionTest))
    suite.addTest(makeSuite(RetryOnTimeoutServerTest))
    suite.addTest(makeSuite(RequestsCaBundleTest))
    suite.addTest(makeSuite(TestUsernameSentAsHeader))
    suite.addTest(makeSuite(TestCrateJsonEncoder))
    suite.addTest(makeSuite(TestDefaultSchemaHeader))
    suite.addTest(doctest.DocTestSuite('crate.client.connection'))
    suite.addTest(doctest.DocTestSuite('crate.client.http'))

    s = doctest.DocFileSuite(
        'docs/by-example/connection.rst',
        'docs/by-example/cursor.rst',
        module_relative=False,
        optionflags=flags,
        encoding='utf-8'
    )
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'docs/by-example/https.rst',
        module_relative=False,
        setUp=setUpWithHttps,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = HttpsTestServerLayer()
    suite.addTest(s)

    # Integration tests.
    layer = ensure_cratedb_layer()

    s = makeSuite(BulkOperationTest)
    s.layer = layer
    suite.addTest(s)

    s = doctest.DocFileSuite(
        'docs/by-example/http.rst',
        'docs/by-example/client.rst',
        'docs/by-example/blob.rst',
        module_relative=False,
        setUp=setUpCrateLayerBaseline,
        tearDown=tearDownDropEntitiesBaseline,
        optionflags=flags,
        encoding='utf-8'
    )
    s.layer = layer
    suite.addTest(s)

    return suite
