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
import unittest


class ClientMocked:
    active_servers = ["http://localhost:4200"]

    def __init__(self):
        self.response = {}
        self._server_infos = ("http://localhost:4200", "my server", "2.0.0")

    def sql(self, stmt=None, parameters=None, bulk_parameters=None):
        return self.response

    def server_infos(self, server):
        return self._server_infos

    def set_next_response(self, response):
        self.response = response

    def set_next_server_infos(self, server, server_name, version):
        self._server_infos = (server, server_name, version)

    def close(self):
        pass


class ParametrizedTestCase(unittest.TestCase):
    """
    TestCase classes that want to be parametrized should
    inherit from this class.

    https://eli.thegreenplace.net/2011/08/02/python-unit-testing-parametrized-test-cases
    """

    def __init__(self, methodName="runTest", param=None):
        super(ParametrizedTestCase, self).__init__(methodName)
        self.param = param

    @staticmethod
    def parametrize(testcase_klass, param=None):
        """Create a suite containing all tests taken from the given
        subclass, passing them the parameter 'param'.
        """
        testloader = unittest.TestLoader()
        testnames = testloader.getTestCaseNames(testcase_klass)
        suite = unittest.TestSuite()
        for name in testnames:
            suite.addTest(testcase_klass(name, param=param))
        return suite


class ExtraAssertions(unittest.TestCase):
    """
    Additional assert methods for unittest.

    - https://github.com/python/cpython/issues/71339
    - https://bugs.python.org/issue14819
    - https://bugs.python.org/file43047/extra_assertions.patch
    """

    def assertIsSubclass(self, cls, superclass, msg=None):
        try:
            r = issubclass(cls, superclass)
        except TypeError:
            if not isinstance(cls, type):
                self.fail(
                    self._formatMessage(msg, "%r is not a class" % (cls,))
                )
            raise
        if not r:
            self.fail(
                self._formatMessage(
                    msg, "%r is not a subclass of %r" % (cls, superclass)
                )
            )
