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

from .cursor import Cursor
from .exceptions import ProgrammingError, ConnectionError
from .http import Client
from .blob import BlobContainer
from ._pep440 import Version


class Connection(object):

    def __init__(self,
                 servers=None,
                 timeout=None,
                 backoff_factor=0,
                 client=None,
                 verify_ssl_cert=True,
                 ca_cert=None,
                 error_trace=False,
                 cert_file=None,
                 key_file=None,
                 username=None,
                 password=None,
                 schema=None,
                 pool_size=None,
                 socket_keepalive=True,
                 socket_tcp_keepidle=None,
                 socket_tcp_keepintvl=None,
                 socket_tcp_keepcnt=None,
                 converter=None,
                 time_zone=None,
                 ):
        """
        :param servers:
            either a string in the form of '<hostname>:<port>'
            or a list of servers in the form of ['<hostname>:<port>', '...']
        :param timeout:
            (optional)
            define the retry timeout for unreachable servers in seconds
        :param backoff_factor:
            (optional)
            define the retry interval for unreachable servers in seconds
        :param client:
            (optional - for testing)
            client used to communicate with crate.
        :param verify_ssl_cert:
            if set to ``False``, disable SSL server certificate verification.
            defaults to ``True``
        :param ca_cert:
            a path to a CA certificate to use when verifying the SSL server
            certificate.
        :param error_trace:
            if set to ``True`` return a whole stacktrace of any server error if
            one occurs
        :param cert_file:
            a path to the client certificate to present to the server.
        :param key_file:
            a path to the client key to use when communicating with the server.
        :param username:
            the username in the database.
        :param password:
            the password of the user in the database.
        :param pool_size:
            (optional)
            Number of connections to save that can be reused.
            More than 1 is useful in multithreaded situations.
        :param socket_keepalive:
            (optional, defaults to ``True``)
            Enable TCP keepalive on socket level.
        :param socket_tcp_keepidle:
            (optional)
            Set the ``TCP_KEEPIDLE`` socket option, which overrides
            ``net.ipv4.tcp_keepalive_time`` kernel setting if ``socket_keepalive``
            is ``True``.
        :param socket_tcp_keepintvl:
            (optional)
            Set the ``TCP_KEEPINTVL`` socket option, which overrides
            ``net.ipv4.tcp_keepalive_intvl`` kernel setting if ``socket_keepalive``
            is ``True``.
        :param socket_tcp_keepcnt:
            (optional)
            Set the ``TCP_KEEPCNT`` socket option, which overrides
            ``net.ipv4.tcp_keepalive_probes`` kernel setting if ``socket_keepalive``
            is ``True``.
        :param converter:
            (optional, defaults to ``None``)
            A `Converter` object to propagate to newly created `Cursor` objects.
        :param time_zone:
            (optional, defaults to ``None``)
            A time zone specifier used for returning `TIMESTAMP` types as
            timezone-aware native Python `datetime` objects.

            Different data types are supported. Available options are:

            - ``datetime.timezone.utc``
            - ``datetime.timezone(datetime.timedelta(hours=7), name="MST")``
            - ``pytz.timezone("Australia/Sydney")``
            - ``zoneinfo.ZoneInfo("Australia/Sydney")``
            - ``+0530`` (UTC offset in string format)

            When `time_zone` is `None`, the returned `datetime` objects are
            "naive", without any `tzinfo`, converted using ``datetime.utcfromtimestamp(...)``.

            When `time_zone` is given, the returned `datetime` objects are "aware",
            with `tzinfo` set, converted using ``datetime.fromtimestamp(..., tz=...)``.
        """

        self._converter = converter
        self.time_zone = time_zone

        if client:
            self.client = client
        else:
            self.client = Client(servers,
                                 timeout=timeout,
                                 backoff_factor=backoff_factor,
                                 verify_ssl_cert=verify_ssl_cert,
                                 ca_cert=ca_cert,
                                 error_trace=error_trace,
                                 cert_file=cert_file,
                                 key_file=key_file,
                                 username=username,
                                 password=password,
                                 schema=schema,
                                 pool_size=pool_size,
                                 socket_keepalive=socket_keepalive,
                                 socket_tcp_keepidle=socket_tcp_keepidle,
                                 socket_tcp_keepintvl=socket_tcp_keepintvl,
                                 socket_tcp_keepcnt=socket_tcp_keepcnt,
                                 )
        self.lowest_server_version = self._lowest_server_version()
        self._closed = False

    def cursor(self, **kwargs) -> Cursor:
        """
        Return a new Cursor Object using the connection.
        """
        converter = kwargs.pop("converter", self._converter)
        time_zone = kwargs.pop("time_zone", self.time_zone)
        if not self._closed:
            return Cursor(
                connection=self,
                converter=converter,
                time_zone=time_zone,
            )
        else:
            raise ProgrammingError("Connection closed")

    def close(self):
        """
        Close the connection now
        """
        self._closed = True
        self.client.close()

    def commit(self):
        """
        Transactions are not supported, so ``commit`` is not implemented.
        """
        if self._closed:
            raise ProgrammingError("Connection closed")

    def get_blob_container(self, container_name):
        """ Retrieve a BlobContainer for `container_name`

        :param container_name: the name of the BLOB container.
        :returns: a :class:ContainerObject
        """
        return BlobContainer(container_name, self)

    def _lowest_server_version(self):
        lowest = None
        for server in self.client.active_servers:
            try:
                _, _, version = self.client.server_infos(server)
                version = Version(version)
            except (ValueError, ConnectionError):
                continue
            if not lowest or version < lowest:
                lowest = version
        return lowest or Version('0.0.0')

    def __repr__(self):
        return '<Connection {0}>'.format(repr(self.client))

    def __enter__(self):
        return self

    def __exit__(self, *excs):
        self.close()


# For backwards compatibility and not to break existing imports
connect = Connection
