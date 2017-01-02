# -*- coding: utf-8; -*-
#
# Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  Crate licenses
# this file to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
# However, if you have executed another commercial license agreement
# with Crate these terms will supersede the license and you may use the
# software solely pursuant to the terms of the relevant commercial agreement.

from unittest import TestCase
from unittest.mock import MagicMock

from crate.client import connect
from crate.client.http import Client


class CursorTest(TestCase):

    def test_execute_with_args(self):
        client = MagicMock(spec=Client)
        conn = connect(client=client)
        c = conn.cursor()
        statement = 'select * from locations where position = ?'
        c.execute(statement, 1)
        client.sql.assert_called_once_with(statement, 1, None)
        conn.close()

    def test_execute_with_bulk_args(self):
        client = MagicMock(spec=Client)
        conn = connect(client=client)
        c = conn.cursor()
        statement = 'select * from locations where position = ?'
        c.execute(statement, bulk_parameters=[[1]])
        client.sql.assert_called_once_with(statement, None, [[1]])
        conn.close()
