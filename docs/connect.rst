.. _connect:

==================
Connect to CrateDB
==================

.. NOTE::

   This page documents the CrateDB `Database API`_ client.

   For help using the `SQLAlchemy`_ dialect, consult
   :ref:`the SQLAlchemy dialect documentation <using-sqlalchemy>`.

.. SEEALSO::

   Supplementary information about the CrateDB Database API client can be found
   in the :ref:`data types appendix <data-types-db-api>` and the
   :ref:`compatibility notes <compatibility>`.

   For general help using the Database API, consult `PEP 0249`_.

.. rubric:: Table of contents

.. contents::
   :local:

.. _single-node:

Connect to a single node
========================

To connect to a single CrateDB node, use the ``connect()`` function, like so:

    >>> connection = client.connect("<NODE_URL>", username="<USERNAME>")

Here, replace ``<NODE_URL>`` with a URL pointing to the `HTTP endpoint`_ of a
CrateDB node. Replace ``<USERNAME>`` with the username you are authenticating
as.

.. NOTE::

   This example authenticates as ``crate``, the default database user in
   CrateDB versions 2.1.x and later. This might not work for you.

   Consult the `Authentication`_ section for more information.

Example node URLs:

- ``http://localhost:4200/``
- ``http://crate-1.vm.example.com:4200/``
- ``http://198.51.100.1:4200/``

If the CrateDB hostname is ``crate-1.vm.example.com`` and CrateDB is listening
for HTTP requests on port 4200, the node URL would be
``http://crate-1.vm.example.com:4200/``.

.. TIP::

   If a ``<NODE_URL>`` argument is not provided, the library will attempt
   to connect to CrateDB on the local host with the default HTTP port number,
   i.e. ``http://localhost:4200/``.

   So, if you're just getting started with CrateDB, the first time you connect,
   you can probably omit this argument.

.. _multiple-nodes:

Connect to multiple nodes
=========================

To connect to one of multiple nodes, pass a list of database URLs to the
connect() function, like so:

    >>> connection = client.connect(["<NODE_1_URL>", "<NODE_2_URL>"], ...)

Here, ``<NODE_1_URL>`` and ``<NODE_2_URL>`` correspond to two node URLs, as
described in the previous section.

You can pass in as many node URLs as you like.

.. TIP::

    For every query, the client will attempt to connect to each node in sequence
    until a successful connection is made. Nodes are moved to the end of the
    list each time they are tried.

    Over multiple query executions, this behaviour functions as client-side
    *round-robin* load balancing. (This is analogous to `round-robin DNS`_.)

.. _connection-options:

Connection options
==================

HTTPS
-----

You can connect to a CrateDB client via HTTPS by specifying ``https`` in the
URL:

    >>> connection = client.connect('https://localhost:4200/', ...)

.. CAUTION::

    By default, server certificates are *not* verified.

.. SEEALSO::

    The CrateDB reference has a section on `setting up SSL`_. This will be
    useful background reading for the following two subsections.

Server verification
...................

You can enable server SSL certificate verification by passing in the
``verify_ssl_cert`` keyword argument and setting it to ``True``.

However, in order to do so, you also need to specify the certificate file of
the *Certificate Authority* (CA) used to sign the server SSL certificate. You
can do this using the ``ca_cert`` keyword argument.

Here's how you might do that::

    >>> connection = client.connect(..., ca_cert="<CA_CERT_FILE>", verify_ssl_cert=True)

Here, replace ``<CA_CERT_FILE>`` with the path to the CA certificate file.


Client verification
...................

The client also supports client verification via client certificates.

Here's how you might do that::

    >>> connection = client.connect(..., cert_file="<CERT_FILE>", key_file="<KEY_FILE>")

Here, replace ``<CERT_FILE>`` with the path to the client certificate file, and
``<KEY_FILE>`` with the path to the client private key file.

.. TIP::

    Often, you will want to perform server verification *and* client
    verification. In such circumstances, you can combine the two methods above
    to do both at once.

Timeout
-------

Connection timeouts (in seconds) can be configured with the optional
``timeout`` argument:

    >>> connection = client.connect(..., timeout=5)

Here, replace ``...`` with the rest of your arguments.

.. NOTE::

   If no timeout is specified, the client will use the default Python `socket
   timeout`_.

Tracebacks
----------

`Tracebacks`_ in the event of a connection error will be printed if you set
the optional ``error_trace`` argument to ``True``, like so::

    >>> connection = client.connect(..., error_trace=True)

Backoff Factor
--------------

When attempting to make a request, the connection can be configured so that
retries are made in increasing time intervals. This can be configured like so::

    >>> connection = client.connect(..., backoff_factor=0.1)

If ``backoff_factor`` is set to 0.1, then the delay between retries will be 0.0,
0.1, 0.2, 0.4 etc. The maximum backoff factor cannot exceed 120 seconds and by
default its value is 0.

Socket Options
--------------

Creating connections uses `urllib3 default socket options`_ but additionally
enables TCP keepalive by setting ``socket.SO_KEEPALIVE`` to ``1``.

Keepalive can be disabled using the ``socket_keepalive`` argument, like so::

    >>> connection = client.connect(..., socket_keepalive=False)

If keepalive is enabled (default), there are three additional, optional socket
options that can be configured via connection arguments.

:``socket_tcp_keepidle``:

    Set the ``TCP_KEEPIDLE`` socket option, which overrides
    ``net.ipv4.tcp_keepalive_time`` kernel setting if ``socket_keepalive`` is
    ``True``.

:``socket_tcp_keepintvl``:

    Set the ``TCP_KEEPINTVL`` socket option, which overrides
    ``net.ipv4.tcp_keepalive_intvl`` kernel setting if ``socket_keepalive`` is
    ``True``.

:``socket_tcp_keepcnt``:

    Set the ``TCP_KEEPCNT`` socket option, which overrides
    ``net.ipv4.tcp_keepalive_probes`` kernel setting if ``socket_keepalive`` is
    ``True``.

.. _authentication:

Authentication
==============

.. NOTE::

   Authentication was introduced in CrateDB versions 2.1.x.

   If you are using CrateDB 2.1.x or later, you must supply a username. If you
   are using earlier versions of CrateDB, this argument is not supported.

   See the :ref:`compatibility notes <cratedb-versions>` for more information.

You can authenticate with CrateDB like so:

    >>> connection = client.connect(..., username="<USERNAME>", password="<PASSWORD>")

Here, replace ``<USERNAME>`` and ``<PASSWORD>`` with the appropriate username
and password.

.. TIP::

   If you have not configured a custom `database user`_, you probably want to
   authenticate as the CrateDB superuser, which is ``crate``. The superuser
   does not have a password, so you can omit the ``password`` argument.

.. _schema-selection:

Schema selection
================

You can select a schema using the optional ``schema`` argument, like so:

    >>> connection = client.connect(..., schema="<SCHEMA>")

Here, replace ``<SCHEMA>`` with the name of your schema, and replace ``...``
with the rest of your arguments.

.. TIP::

   The default CrateDB schema is ``doc``, and if you do not specify a schema,
   this is what will be used.

   However, you can query any schema you like by specifying it in the query.

Next steps
==========

Once you're connected, you can :ref:`query CrateDB <query>`.

.. SEEALSO::

   Check out the `sample application`_ (and the corresponding `documentation`_)
   for a practical demonstration of this driver in use.

.. _client-side random load balancing: https://en.wikipedia.org/wiki/Load_balancing_(computing)#Client-side_random_load_balancing
.. _Database API: http://www.python.org/dev/peps/pep-0249/
.. _database user: https://crate.io/docs/crate/reference/en/latest/admin/user-management.html
.. _documentation: https://github.com/crate/crate-sample-apps/blob/master/python/documentation.md
.. _HTTP endpoint: https://crate.io/docs/crate/reference/en/latest/interfaces/http.html
.. _PEP 0249: http://www.python.org/dev/peps/pep-0249/
.. _round-robin DNS: https://en.wikipedia.org/wiki/Round-robin_DNS
.. _sample application: https://github.com/crate/crate-sample-apps/tree/master/python
.. _setting up SSL: https://crate.io/docs/crate/reference/en/latest/admin/ssl.html
.. _socket timeout: https://docs.python.org/2/library/socket.html#socket.getdefaulttimeout
.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _tracebacks: https://docs.python.org/3/library/traceback.html
.. _urllib3 default socket options: https://urllib3.readthedocs.io/en/latest/reference/urllib3.connection.html#urllib3.connection.HTTPConnection
