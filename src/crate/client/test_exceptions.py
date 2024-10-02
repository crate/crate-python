import unittest

from crate.client import Error


class ErrorTestCase(unittest.TestCase):

    def test_error_with_msg(self):
        err = Error("foo")
        self.assertEqual(str(err), "foo")

    def test_error_with_error_trace(self):
        err = Error("foo", error_trace="### TRACE ###")
        self.assertEqual(str(err), "foo\n### TRACE ###")
