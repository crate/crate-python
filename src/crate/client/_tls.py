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
import ssl
import typing as t

from urllib3.util.ssl_ import create_urllib3_context


def resolve_ca_cert(ca_cert: t.Optional[str]) -> t.Optional[str]:
    """
    Return the CA bundle to use, falling back to ``REQUESTS_CA_BUNDLE``.
    """
    ca_cert = ca_cert or os.environ.get("REQUESTS_CA_BUNDLE", None)
    if ca_cert and not os.path.exists(ca_cert):
        # Sanity check
        raise IOError('CA bundle file "{}" does not exist.'.format(ca_cert))
    return ca_cert


def make_ssl_context(
    verify_ssl_cert: bool = True,
    ca_cert: t.Optional[str] = None,
    cert_file: t.Optional[str] = None,
    key_file: t.Optional[str] = None,
    ssl_relax_minimum_version: bool = False,
) -> ssl.SSLContext:
    """
    Build the `SSLContext` that urllib3 builds for the same options.
    """
    context = create_urllib3_context(
        cert_reqs=ssl.CERT_REQUIRED if verify_ssl_cert else ssl.CERT_NONE,
        ssl_minimum_version=(
            ssl.TLSVersion.MINIMUM_SUPPORTED
            if ssl_relax_minimum_version
            else None
        ),
    )
    ca_cert = resolve_ca_cert(ca_cert)
    if ca_cert:
        context.load_verify_locations(cafile=ca_cert)
    else:
        context.load_default_certs()
    if cert_file:
        context.load_cert_chain(cert_file, key_file)
    return context
