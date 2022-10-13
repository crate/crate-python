# vi: set encoding=utf-8
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
from __future__ import absolute_import

import os


def docs_path(*parts):
    return os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)), *parts
        )
    )


def project_root(*parts):
    return os.path.abspath(
        os.path.join(docs_path("..", ".."), *parts)
    )


def crate_path(*parts):
    return os.path.abspath(
        project_root("parts", "crate", *parts)
    )


crate_port = 44209
crate_transport_port = 44309
localhost = '127.0.0.1'
crate_host = "{host}:{port}".format(host=localhost, port=crate_port)
crate_uri = "http://%s" % crate_host
