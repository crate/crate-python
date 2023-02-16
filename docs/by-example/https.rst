.. _https_connection:

========================
HTTPS connection support
========================

This documentation section outlines different options to connect to CrateDB
using SSL/TLS.

.. rubric:: Table of Contents

.. contents::
   :local:


Introduction
============

The CrateDB client is able to connect via HTTPS.

A check against a specific CA certificate can be made by creating the client
with the path to the CA certificate file using the keyword argument
``ca_cert``.

.. note::

    By default, SSL server certificates are verified. To disable verification,
    use the keyword argument ``verify_ssl_cert``. If it is set to ``False``,
    server certificate validation will be skipped.

All the following examples will connect to a host using a self-signed
certificate.

The CrateDB Python driver package offers a HTTP client API object.

    >>> from crate.client import http
    >>> HttpClient = http.Client


With certificate verification
=============================

When using a valid CA certificate, the connection will be successful:

    >>> client = HttpClient([crate_host], ca_cert=cacert_valid)
    >>> client.server_infos(client._get_server())
    ('https://localhost:65534', 'test', '0.0.0')

When not providing a ``ca_cert`` file, the connection will fail:

    >>> client = HttpClient([crate_host])
    >>> client.server_infos(crate_host)
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ConnectionError: Server not available, ...certificate verify failed...

Also, when providing an invalid ``ca_cert``, an error is raised:

    >>> client = HttpClient([crate_host], ca_cert=cacert_invalid)
    >>> client.server_infos(crate_host)
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ConnectionError: Server not available, ...certificate verify failed...


Without certificate verification
================================

When turning off certificate verification, calling the server will succeed,
even when not providing a valid CA certificate:

    >>> client = HttpClient([crate_host], verify_ssl_cert=False)
    >>> client.server_infos(crate_host)
    ('https://localhost:65534', 'test', '0.0.0')

Without verification, calling the server will even work when using an invalid
``ca_cert``:

    >>> client = HttpClient([crate_host], verify_ssl_cert=False, ca_cert=cacert_invalid)
    >>> client.server_infos(crate_host)
    ('https://localhost:65534', 'test', '0.0.0')



X.509 client certificate
========================

The CrateDB driver also supports client certificates.

The ``HttpClient`` constructor takes two keyword arguments: ``cert_file`` and
``key_file``. Both should be strings pointing to the path of the client
certificate and key file:

    >>> client = HttpClient([crate_host], ca_cert=cacert_valid, cert_file=clientcert_valid, key_file=clientcert_valid)
    >>> client.server_infos(crate_host)
    ('https://localhost:65534', 'test', '0.0.0')

When using an invalid client certificate, the connection will fail:

    >>> client = HttpClient([crate_host], ca_cert=cacert_valid, cert_file=clientcert_invalid, key_file=clientcert_invalid)
    >>> client.server_infos(crate_host)
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ConnectionError: Server not available, exception: HTTPSConnectionPool...

The connection will also fail when providing an invalid CA certificate:

    >>> client = HttpClient([crate_host], ca_cert=cacert_invalid, cert_file=clientcert_valid, key_file=clientcert_valid)
    >>> client.server_infos(crate_host)
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ConnectionError: Server not available, exception: HTTPSConnectionPool...


Relaxing minimum SSL version
============================

urrlib3 v2 dropped support for TLS 1.0 and TLS 1.1 by default, see `Modern security by default -
HTTPS requires TLS 1.2+`_. If you need to re-enable it, use the ``ssl_relax_minimum_version`` flag,
which will configure ``kwargs["ssl_minimum_version"] = ssl.TLSVersion.MINIMUM_SUPPORTED``.

    >>> client = HttpClient([crate_host], ssl_relax_minimum_version=True, verify_ssl_cert=False)
    >>> client.server_infos(crate_host)
    ('https://localhost:65534', 'test', '0.0.0')


.. _Modern security by default - HTTPS requires TLS 1.2+: https://urllib3.readthedocs.io/en/latest/v2-migration-guide.html#https-requires-tls-1-2
