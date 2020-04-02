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
from distutils.version import StrictVersion


class Connection(object):

    def __init__(self, servers=None, timeout=None, backoff_factor=0, client=None,
                 verify_ssl_cert=False, ca_cert=None, error_trace=False,
                 cert_file=None, key_file=None, username=None, password=None,
                 schema=None):
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
                                 schema=schema)
        self.lowest_server_version = self._lowest_server_version()
        self._closed = False

    def cursor(self):
        """
        Return a new Cursor Object using the connection.
        """
        if not self._closed:
            return Cursor(self)
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
                version = StrictVersion(version)
            except (ValueError, ConnectionError):
                continue
            if not lowest or version < lowest:
                lowest = version
        return lowest or StrictVersion('0.0.0')

    def __repr__(self):
        return '<Connection {0}>'.format(repr(self.client))

    def __enter__(self):
        return self

    def __exit__(self, *excs):
        self.close()


def connect(servers=None,
            timeout=None,
            backoff_factor=0,
            client=None,
            verify_ssl_cert=False,
            ca_cert=None,
            error_trace=False,
            cert_file=None,
            key_file=None,
            username=None,
            password=None,
            schema=None):
    """ Create a :class:Connection object

    :param servers:
        either a string in the form of '<hostname>:<port>'
        or a list of servers in the form of ['<hostname>:<port>', '...']
    :param timeout:
        (optional)
        define the retry timeout for unreachable servers in seconds
    :param client:
        (optional - for testing)
        client used to communicate with crate.
    :param verify_ssl_cert:
        if set to ``True`` verify the servers SSL server certificate.
        defaults to ``False``
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
    :param backoff_factor:
        (optional)
        define the retry interval for unreachable servers in seconds
    >>> connect(['host1:4200', 'host2:4200'])
    <Connection <Client ['http://host1:4200', 'http://host2:4200']>>
    """
    return Connection(servers=servers,
                      timeout=timeout,
                      backoff_factor=backoff_factor,
                      client=client,
                      verify_ssl_cert=verify_ssl_cert,
                      ca_cert=ca_cert,
                      error_trace=error_trace,
                      cert_file=cert_file,
                      key_file=key_file,
                      username=username,
                      password=password,
                      schema=schema)
