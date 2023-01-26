#########################
Generate new certificates
#########################


*****
About
*****

For conducting TLS connectivity tests, there are a few X.509 certificates at
`src/crate/client/pki/*.pem`_. The instructions here outline how to renew them.

In order to invoke the corresponding test cases, run::

    ./bin/test -t https.rst


*******
Details
*******


``*_valid.pem``
===============

By example, this will renew the ``client_valid.pem`` X.509 certificate. The
``server_valid.pem`` certificate can be generated in the same manner.

Create RSA private key and certificate request::

    openssl req -nodes \
        -newkey rsa:2048 -keyout key.pem -out request.csr \
        -subj "/C=AT/ST=Vorarlberg/L=Dornbirn/O=Crate.io/CN=localhost/emailAddress=nobody@crate.io"

Display the certificate request::

    openssl req -in request.csr -text

Sign certificate request::

    openssl x509 -req -in request.csr \
        -CA cacert_valid.pem -CAkey cacert_valid.pem -CAcreateserial -sha256 \
        -days 358000 -extfile <(printf "subjectAltName=DNS:localhost") -out client.pem

Display the certificate::

    openssl x509 -in client.pem -text

Combine private key and certificate into single PEM file::

    cat key.pem > client_valid.pem
    cat client.pem >> client_valid.pem


``client_invalid.pem``
======================

This will renew the ``client_invalid.pem`` X.509 certificate. Please note that,
in order to create an invalid certificate, two attributes are used:

- ``CN=horst`` and ``subjectAltName=DNS:horst`` do not match ``localhost``.
- The validity end date will be adjusted a few years into the past, by using
  ``-days -36500``.

Create RSA private key and certificate request::

    openssl req -nodes \
        -newkey rsa:2048 -keyout invalid_key.pem -out invalid.csr \
        -subj "/C=AT/ST=Vorarlberg/L=Dornbirn/O=Crate.io/CN=horst/emailAddress=nobody@crate.io"

Display the certificate request::

    openssl req -in invalid.csr -text

Sign certificate request::

    openssl x509 -req -in invalid.csr \
        -CA cacert_valid.pem -CAkey cacert_valid.pem -CAcreateserial -sha256 \
        -days -36500 -extfile <(printf "subjectAltName=DNS:horst") -out invalid_cert.pem

Display the certificate::

    openssl x509 -in invalid_cert.pem -text

Combine private key and certificate into single PEM file::

    cat invalid_key.pem > client_invalid.pem
    cat invalid_cert.pem >> client_invalid.pem


.. _src/crate/client/pki/*.pem: https://github.com/crate/crate-python/tree/master/src/crate/client/pki
