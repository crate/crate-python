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

import sqlalchemy as sa
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base


class FunctionTest(TestCase):
    def setUp(self):
        Base = declarative_base(bind=sa.create_engine("crate://"))

        class Character(Base):
            __tablename__ = "characters"
            name = sa.Column(sa.String, primary_key=True)
            timestamp = sa.Column(sa.DateTime)

        self.Character = Character

    def test_date_trunc_type_is_timestamp(self):
        f = sa.func.date_trunc("minute", self.Character.timestamp)
        self.assertEqual(len(f.base_columns), 1)
        for col in f.base_columns:
            self.assertIsInstance(col.type, TIMESTAMP)
