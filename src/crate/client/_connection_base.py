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
import typing as t

from verlib2 import Version

from ._cursor_base import CursorBase
from .exceptions import ConnectionError, ProgrammingError

CursorT = t.TypeVar("CursorT", bound=CursorBase)


class ConnectionBase(t.Generic[CursorT]):
    """
    Connection state shared by the sync and async connections.

    Public methods that do IO, or that are coroutines on the async
    connection, live on the subclasses.
    """

    client: t.Any

    @property
    def _cursor_class(self) -> t.Type[CursorT]:
        """The class `cursor()` creates."""
        raise NotImplementedError

    @property
    def _blob_container_class(self) -> t.Type[t.Any]:
        """The class `get_blob_container()` creates."""
        raise NotImplementedError

    def __init__(self, converter=None, time_zone=None):
        self._converter = converter
        self.time_zone = time_zone
        self._closed = False

    def cursor(self, **kwargs) -> CursorT:
        """
        Return a new Cursor Object using the connection.
        """
        converter = kwargs.pop("converter", self._converter)
        time_zone = kwargs.pop("time_zone", self.time_zone)
        self._check_open()
        return self._cursor_class(
            connection=self,
            converter=converter,
            time_zone=time_zone,
        )

    def get_blob_container(self, container_name):
        """Retrieve a BlobContainer for `container_name`

        :param container_name: the name of the BLOB container.
        :returns: a :class:ContainerObject
        """
        return self._blob_container_class(container_name, self)

    def _check_open(self):
        if self._closed:
            raise ProgrammingError("Connection closed")

    @staticmethod
    def _lowest_version(
        versions: t.Iterable[t.Union[str, BaseException]],
    ) -> Version:
        """
        Return the lowest of the versions reported by the servers.
        """
        lowest = None
        connection_errors = []
        for version in versions:
            if isinstance(version, ConnectionError):
                connection_errors.append(version)
                continue
            if isinstance(version, ValueError):
                continue
            if isinstance(version, BaseException):
                raise version
            try:
                parsed = Version(version)
            except ValueError:
                continue
            if not lowest or parsed < lowest:
                lowest = parsed
        if connection_errors and not lowest:
            raise ConnectionError("; ".join(str(e) for e in connection_errors))
        return lowest or Version("0.0.0")

    def __repr__(self):
        return f"<{self.__class__.__qualname__} {self.client!r}>"
