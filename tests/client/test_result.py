import sys
import unittest

from crate import client
from crate.client.exceptions import ProgrammingError
from .layer import setUpCrateLayerBaseline, tearDownDropEntitiesBaseline
from .settings import crate_host


class BulkOperationTest(unittest.TestCase):

    def setUp(self):
        setUpCrateLayerBaseline(self)

    def tearDown(self):
        tearDownDropEntitiesBaseline(self)

    @unittest.skipIf(sys.version_info < (3, 8), "BulkResponse needs Python 3.8 or higher")
    def test_executemany_with_bulk_response_partial(self):

        # Import at runtime is on purpose, to permit skipping the test case.
        from crate.client.result import BulkResponse

        connection = client.connect(crate_host)
        cursor = connection.cursor()

        # Run SQL DDL.
        cursor.execute("CREATE TABLE foobar (id INTEGER PRIMARY KEY, name STRING);")

        # Run a batch insert that only partially succeeds.
        invalid_records = [(1, "Hotzenplotz 1"), (1, "Hotzenplotz 2")]
        result = cursor.executemany("INSERT INTO foobar (id, name) VALUES (?, ?)", invalid_records)

        # Verify CrateDB response.
        self.assertEqual(result, [{"rowcount": 1}, {"rowcount": -2}])

        # Verify decoded response.
        bulk_response = BulkResponse(invalid_records, result)
        self.assertEqual(bulk_response.failed_records, [(1, "Hotzenplotz 2")])
        self.assertEqual(bulk_response.record_count, 2)
        self.assertEqual(bulk_response.success_count, 1)
        self.assertEqual(bulk_response.failed_count, 1)

        cursor.execute("REFRESH TABLE foobar;")
        cursor.execute("SELECT * FROM foobar;")
        result = cursor.fetchall()
        self.assertEqual(result, [[1, "Hotzenplotz 1"]])

        cursor.close()
        connection.close()

    @unittest.skipIf(sys.version_info < (3, 8), "BulkResponse needs Python 3.8 or higher")
    def test_executemany_empty(self):

        connection = client.connect(crate_host)
        cursor = connection.cursor()

        # Run SQL DDL.
        cursor.execute("CREATE TABLE foobar (id INTEGER PRIMARY KEY, name STRING);")

        # Run a batch insert that is empty.
        with self.assertRaises(ProgrammingError) as cm:
            cursor.executemany("INSERT INTO foobar (id, name) VALUES (?, ?)", [])
        self.assertEqual(
            str(cm.exception),
            "SQLParseException[The query contains a parameter placeholder $1, "
            "but there are only 0 parameter values]")

        cursor.close()
        connection.close()

    @unittest.skipIf(sys.version_info < (3, 8), "BulkResponse needs Python 3.8 or higher")
    def test_bulk_response_empty_records_or_results(self):

        # Import at runtime is on purpose, to permit skipping the test case.
        from crate.client.result import BulkResponse

        with self.assertRaises(ValueError) as cm:
            BulkResponse(records=None, results=None)
        self.assertEqual(
            str(cm.exception),
            "Processing a bulk response without records is an invalid operation")

        with self.assertRaises(ValueError) as cm:
            BulkResponse(records=[], results=None)
        self.assertEqual(
            str(cm.exception),
            "Processing a bulk response without results is an invalid operation")
