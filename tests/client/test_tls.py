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
import ssl
from unittest.mock import patch

import pytest
from urllib3.util.ssl_ import create_urllib3_context

from crate.client import exceptions
from crate.client._tls import make_ssl_context, resolve_ca_cert
from crate.client.http import Client

from .settings import assets_path

CA_VALID = assets_path("pki/cacert_valid.pem")
CA_INVALID = assets_path("pki/cacert_invalid.pem")
CLIENT_CERT = assets_path("pki/client_valid.pem")


def test_resolve_ca_cert():
    with patch.dict(os.environ, {}, clear=True):
        assert resolve_ca_cert(None) is None
        assert resolve_ca_cert(CA_VALID) == CA_VALID


def test_resolve_ca_cert_from_environment():
    with patch.dict(os.environ, {"REQUESTS_CA_BUNDLE": CA_VALID}, clear=True):
        assert resolve_ca_cert(None) == CA_VALID
        # An explicit bundle wins.
        assert resolve_ca_cert(CA_INVALID) == CA_INVALID


def test_resolve_ca_cert_missing_file():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(IOError, match="does not exist"):
            resolve_ca_cert("/nonexistent")
        with pytest.raises(IOError, match="does not exist"):
            Client("https://localhost:4200", ca_cert="/nonexistent")
    env = {"REQUESTS_CA_BUNDLE": "/nonexistent"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(IOError, match="does not exist"):
            resolve_ca_cert(None)


def test_ssl_context_matches_urllib3():
    """
    The context has the settings that urllib3 uses for the sync client.
    """
    expected = create_urllib3_context(cert_reqs=ssl.CERT_REQUIRED)
    context = make_ssl_context(True, CA_VALID)
    assert context.minimum_version == expected.minimum_version
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert context.maximum_version == expected.maximum_version
    assert context.options == expected.options
    assert context.verify_flags == expected.verify_flags
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED


def test_ssl_context_without_verification():
    expected = create_urllib3_context(cert_reqs=ssl.CERT_NONE)
    context = make_ssl_context(False, CA_VALID)
    assert context.options == expected.options
    assert context.check_hostname is False
    assert context.verify_mode == ssl.CERT_NONE


def test_ssl_context_relaxed_minimum_version():
    """
    The same as the sync client's `ssl_minimum_version` override.
    """
    context = make_ssl_context(True, CA_VALID, ssl_relax_minimum_version=True)
    assert context.minimum_version == ssl.TLSVersion.MINIMUM_SUPPORTED
    assert context.check_hostname is True


def test_ssl_context_default_certs():
    with patch.dict(os.environ, {}, clear=True):
        context = make_ssl_context(True)
    assert context.verify_mode == ssl.CERT_REQUIRED


def test_ssl_context_client_certificate():
    """
    The test client certificate file holds the key too.
    """
    make_ssl_context(True, CA_VALID, cert_file=CLIENT_CERT)
    make_ssl_context(
        True, CA_VALID, cert_file=CLIENT_CERT, key_file=CLIENT_CERT
    )
    with pytest.raises(ssl.SSLError):
        make_ssl_context(
            True, CA_VALID, cert_file=assets_path("pki/readme.rst")
        )


def _handshake(context: ssl.SSLContext, host: str, port: int) -> None:
    with socket.create_connection((host, port), timeout=5) as sock:
        with context.wrap_socket(sock, server_hostname=host):
            pass


def test_handshake_valid_ca(https_server):
    """
    The sync client and the shared context both accept the test server's
    certificate with the test CA.
    """
    host, port = "localhost", https_server.server_address[1]
    url = f"https://{host}:{port}"
    client = Client(servers=url, ca_cert=CA_VALID)
    try:
        assert client.server_infos(url)[1] == "test"
    finally:
        client.close()
    _handshake(make_ssl_context(True, CA_VALID), host, port)


def test_handshake_invalid_ca(https_server):
    """
    The sync client and the shared context both reject the test server's
    certificate with another CA, and both accept it without verification.
    """
    host, port = "localhost", https_server.server_address[1]
    url = f"https://{host}:{port}"
    client = Client(servers=url, ca_cert=CA_INVALID)
    try:
        with pytest.raises(
            exceptions.ConnectionError, match="certificate verify failed"
        ):
            client.server_infos(url)
    finally:
        client.close()
    with pytest.raises(ssl.SSLCertVerificationError):
        _handshake(make_ssl_context(True, CA_INVALID), host, port)
    _handshake(make_ssl_context(False, CA_INVALID), host, port)
