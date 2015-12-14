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

import os
import socket
import unittest
import doctest

def docs_path(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), *parts)

def crate_path(*parts):
    return os.path.abspath(docs_path('..', '..', 'parts', 'crate', *parts))

def public_ip():
    """
    take first public interface
    sorted by getaddrinfo - see RFC 3484
    should have the real public IPv4 address as first address.
    At the moment the test layer is not able to handle v6 addresses
    """
    for addrinfo in socket.getaddrinfo(socket.gethostname(), None):
        if addrinfo[1] in (socket.SOCK_STREAM, socket.SOCK_DGRAM) and \
                addrinfo[0] == socket.AF_INET:
            return addrinfo[4][0]
    # fallback
    return socket.gethostbyname(socket.gethostname())

def setUp(test):
    test.globs['crate_path'] = crate_path
    test.globs['public_ip'] = public_ip()

def test_suite():
    suite = unittest.TestSuite()

    s = doctest.DocFileSuite('layer.txt',
                             setUp=setUp,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                             doctest.ELLIPSIS,
                             encoding='utf-8')
    suite.addTest(s)
    return suite
