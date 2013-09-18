
from unittest import TestCase
from mock import MagicMock

from crate.client import connect
from crate.client.http import Client


class CursorTest(TestCase):

    def test_execute_with_args(self):
        client = MagicMock(spec=Client)
        conn = connect(client=client)
        c = conn.cursor()
        statement = 'select * from locations where position = ?'
        c.execute(statement, 1)
        client.sql.assert_called_once_with(statement, 1)
