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
import sys

py2 = True
if sys.version_info[0] > 2:
    py2 = False


if py2:
    from exceptions import StandardError
    xrange = xrange
    raw_input = raw_input
    unicode = unicode

    def cprint(s):
        print(s)

    import Queue
    queue = Queue

    import BaseHTTPServer

    def to_bytes(data, *args, **kwargs):
        return data

else:
    StandardError = Exception
    xrange = range
    raw_input = input
    unicode = str

    def cprint(s):
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        print(s)

    import queue
    assert queue

    import http.server
    BaseHTTPServer = http.server
    to_bytes = bytes

assert StandardError
