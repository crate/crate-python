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

import os
import re
import socket
import unittest
import doctest
import tempfile
from zope.testing.renormalizing import RENormalizing
from .test_layer import LayerUtilsTest

def docs_path(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), *parts)

def crate_path(*parts):
    return os.path.abspath(docs_path('..', '..', 'parts', 'crate', *parts))


def setUp(test):
    test.globs['crate_path'] = crate_path
    test.globs['tempfile'] = tempfile
    test.globs['os'] = os


def test_suite():
    suite = unittest.TestSuite()
    checker = RENormalizing([
        (re.compile(r"u('[^']*')"), r"\1"),
        (re.compile(r"<type "), "<class "),
    ])

    s = doctest.DocFileSuite('layer.txt',
                             setUp=setUp,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                             doctest.ELLIPSIS,
                             checker=checker,
                             encoding='utf-8')
    suite.addTest(s)
    suite.addTest(unittest.makeSuite(LayerUtilsTest))
    return suite
