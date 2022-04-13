#########################
Generate new certificates
#########################


*****
About
*****

By example, this will renew the ``client_valid.pem`` X.509 certificate.


*******
Details
*******

Create RSA private key and certificate request::

    openssl req -nodes \
        -newkey rsa:2048 -keyout key.pem -out request.csr \
        -subj "/C=AT/ST=Vorarlberg/L=Dornbirn/O=Crate/CN=localhost/emailAddress=nobody@crate.io"

Sign certificate request::

    openssl x509 -req -in request.csr \
        -CA cacert_valid.pem -CAkey cacert_valid.pem -CAcreateserial \
        -sha256 -out client.pem -days 358000

Combine private key and certificate into single PEM file::

    cat key.pem > client_valid.pem
    cat client.pem >> client_valid.pem

