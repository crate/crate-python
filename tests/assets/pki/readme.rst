#########################
Generate new certificates
#########################


*****
About
*****

For conducting TLS connectivity tests, there are a few X.509 certificates at
`tests/assets/pki/*.pem`_. The instructions here outline how to renew them.

In order to invoke the corresponding test cases, run::

    ./bin/test -t https.rst


*******
Details
*******


``*_valid.pem``
===============

By example, this will renew the ``server_valid.pem`` and ``client_valid.pem``
X.509 certificates.

Create keys and certificates for certificate authority and one application/user::

    brew install minica
    minica -ca-alg rsa -domains localhost

Combine private key and certificate into single PEM file::

    cat minica-key.pem > cacert_valid.pem; cat minica.pem >> cacert_valid.pem
    cat localhost/key.pem > server_valid.pem; cat localhost/cert.pem >> server_valid.pem
    cp server_valid.pem client_valid.pem

Display the certificates::

    openssl x509 -in cacert_valid.pem -text
    openssl x509 -in server_valid.pem -text
    openssl x509 -in client_valid.pem -text


``*_invalid.pem``
=================

This will renew the ``client_invalid.pem`` X.509 certificate.
In order to create an invalid certificate, it is using a wrong hostname.

- ``CN=horst`` and ``subjectAltName=DNS:horst`` do not match ``localhost``.

Create RSA private key and certificate request::

    openssl req -nodes \
        -newkey rsa:2048 -keyout invalid-key.pem -out invalid.csr \
        -subj "/C=AT/ST=Vorarlberg/L=Dornbirn/O=Crate.io/CN=horst/emailAddress=nobody@crate.io"

Create certificate::

    openssl x509 -req -in invalid.csr \
        -CA cacert_invalid.pem -CAkey cacert_invalid.pem -CAcreateserial -sha256 \
        -days 358000 \
        -out invalid.pem \
        -extfile - <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
subjectAltName=DNS:horst
EOF

Combine private key and certificate into single PEM file::

    cat invalid-key.pem > client_invalid.pem; cat invalid.pem >> client_invalid.pem


.. _tests/assets/pki/*.pem: https://github.com/crate/crate-python/tree/main/tests/assets/pki
