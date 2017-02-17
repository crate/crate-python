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

from .compat import StandardError


class Error(StandardError):

    def __init__(self, msg=None, error_trace=None):
        # for py33 compat.
        # The Exception base class doesn't set the message attribute
        if msg:
            self.message = msg
        super(Error, self).__init__(msg)
        self.error_trace = error_trace


class Warning(StandardError):
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class InternalError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class DataError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass


# exceptions not in db api

class ConnectionError(OperationalError):
    pass


class BlobException(Exception):
    def __init__(self, table, digest):
        self.table = table
        self.digest = digest

    def __str__(self):
        return "{table}/{digest}".format(table=self.table, digest=self.digest)


class DigestNotFoundException(BlobException):
    pass


class BlobLocationNotFoundException(BlobException):
    pass


class TimezoneUnawareException(Error):
    pass
