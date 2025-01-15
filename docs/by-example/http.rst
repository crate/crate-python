===========
HTTP client
===========

.. rubric:: Table of Contents

.. contents::
   :local:


Introduction
============

The CrateDB Python driver package offers an HTTP client API object.

    >>> from crate.client import http
    >>> HttpClient = http.Client


Server configuration
====================

A list of servers can be passed while creating an instance of the http client:

    >>> http_client = HttpClient([crate_host])
    >>> http_client.close()

Its also possible to pass a single server as a string:

    >>> http_client = HttpClient(crate_host)
    >>> http_client.close()

If no ``server`` argument (or no argument at all) is passed, the default one
``127.0.0.1:4200`` is used:

    >>> http_client = HttpClient()
    >>> http_client._active_servers
    ['http://127.0.0.1:4200']
    >>> http_client.close()

When using a list of servers, the servers are selected by round-robin:

    >>> invalid_host = "invalid_host:9999"
    >>> even_more_invalid_host = "even_more_invalid_host:9999"
    >>> http_client = HttpClient([crate_host, invalid_host, even_more_invalid_host], timeout=0.3)
    >>> http_client._get_server()
    'http://127.0.0.1:44209'

    >>> http_client._get_server()
    'http://invalid_host:9999'

    >>> http_client._get_server()
    'http://even_more_invalid_host:9999'

    >>> http_client.close()

Servers with connection errors will be removed from the active server list:

    >>> http_client = HttpClient([invalid_host, even_more_invalid_host, crate_host], timeout=0.3)
    >>> result = http_client.sql('select name from locations')
    >>> http_client._active_servers
    ['http://127.0.0.1:44209']

Inactive servers will be re-added after a given time interval.
To validate this, set the interval and timeout very short, and
sleep after the first request::

    >>> http_client.retry_interval = 1
    >>> result = http_client.sql('select name from locations')
    >>> import time; time.sleep(1)
    >>> server = http_client._get_server()
    >>> http_client._active_servers
    ['http://invalid_host:9999',
     'http://even_more_invalid_host:9999',
     'http://127.0.0.1:44209']
    >>> http_client.close()

If no active servers are available and the retry interval is not reached, just use the oldest
inactive one:

    >>> http_client = HttpClient([invalid_host, even_more_invalid_host, crate_host], timeout=0.3)
    >>> result = http_client.sql('select name from locations')
    >>> http_client._active_servers = []
    >>> http_client._get_server()
    'http://invalid_host:9999'
    >>> http_client.close()

SQL Statements
==============

Issue a select statement against our with test data pre-filled crate instance:

    >>> http_client = HttpClient(crate_host)
    >>> result = http_client.sql('select name from locations order by name')
    >>> pprint(result)
    {'col_types': [4],
     'cols': ['name'],
     'duration': ...,
     'rowcount': 13,
     'rows': [['Aldebaran'],
              ['Algol'],
              ['Allosimanius Syneca'],
              ['Alpha Centauri'],
              ['Altair'],
              ['Argabuthon'],
              ['Arkintoofle Minor'],
              ['Bartledan'],
              ['Folfanga'],
              ['Galactic Sector QQ7 Active J Gamma'],
              ['Galaxy'],
              ['North West Ripple'],
              ['Outer Eastern Rim']]}

Blobs
=====

Check if a blob exists:

    >>> http_client.blob_exists('myfiles', '040f06fd774092478d450774f5ba30c5da78acc8')
    False

Trying to get a non-existing blob throws an exception:

    >>> http_client.blob_get('myfiles', '041f06fd774092478d450774f5ba30c5da78acc8')
    Traceback (most recent call last):
    ...
    crate.client.exceptions.DigestNotFoundException: myfiles/041f06fd774092478d450774f5ba30c5da78acc8

Creating a new blob - this method returns ``True`` if the blob was newly created:

    >>> from tempfile import TemporaryFile
    >>> f = TemporaryFile()
    >>> _ = f.write(b'content')
    >>> _ = f.seek(0)
    >>> http_client.blob_put(
    ...     'myfiles', '040f06fd774092478d450774f5ba30c5da78acc8', f)
    True

Uploading the same content again returns ``False``:

    >>> _ = f.seek(0)
    >>> http_client.blob_put(
    ...     'myfiles', '040f06fd774092478d450774f5ba30c5da78acc8', f)
    False

Now the blob exist:

    >>> http_client.blob_exists('myfiles', '040f06fd774092478d450774f5ba30c5da78acc8')
    True

Blobs are returned as generators, generating a chunk on each call:

    >>> g = http_client.blob_get('myfiles', '040f06fd774092478d450774f5ba30c5da78acc8')
    >>> print(next(g))
    content

The chunk_size can be set explicitly on get:

    >>> g = http_client.blob_get(
    ...     'myfiles', '040f06fd774092478d450774f5ba30c5da78acc8', 5)
    >>> print(next(g))
    conte

    >>> print(next(g))
    nt

Deleting a blob - this method returns true if the blob existed:

    >>> http_client.blob_del('myfiles', '040f06fd774092478d450774f5ba30c5da78acc8')
    True

    >>> http_client.blob_del('myfiles', '040f06fd774092478d450774f5ba30c5da78acc8')
    False

Uploading a blob to a table with disabled blob support throws an exception:

    >>> _ = f.seek(0)
    >>> http_client.blob_put(
    ...     'locations', '040f06fd774092478d450774f5ba30c5da78acc8', f)
    Traceback (most recent call last):
    ...
    crate.client.exceptions.BlobLocationNotFoundException: locations/040f06fd774092478d450774f5ba30c5da78acc8

    >>> http_client.close()
    >>> f.close()


Error Handling
==============

Create a function that takes a lot of time to return so we can run into a
timeout exception:

    >>> http_client = HttpClient(crate_host)
    >>> http_client.sql('''
    ... CREATE FUNCTION fib(LONG) RETURNS LONG
    ... LANGUAGE JAVASCRIPT AS '
    ...   var fib = function fib(n) { return n < 2 ? n : fib(n-1) + fib(n-2); }
    ... '
    ... ''')
    {...}
    >>> http_client.close()

It is possible to define a HTTP timeout in seconds when creating a client
object, so an exception is raised when the timeout expires:

    >>> http_client = HttpClient(crate_host, timeout=0.01)
    >>> http_client.sql('select fib(32)')
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ConnectionError: No more Servers available, exception from last server: ...
    >>> http_client.close()

In order to adjust the connect- vs. read-timeout values individually,
please use the ``urllib3.Timeout`` object like:

    >>> import urllib3
    >>> http_client = HttpClient(crate_host, timeout=urllib3.Timeout(connect=1.11, read=0.01))
    >>> http_client.sql('select fib(32)')
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ConnectionError: No more Servers available, exception from last server: ...
    >>> http_client.close()

When connecting to non-CrateDB servers, the HttpClient will raise a ConnectionError like this:

    >>> http_client = HttpClient(["https://example.org/"])
    >>> http_client.server_infos(http_client._get_server())
    Traceback (most recent call last):
    ...
    crate.client.exceptions.ProgrammingError: Invalid server response of content-type 'text/html':
    ...
    >>> http_client.close()

When using the ``error_trace`` kwarg a full traceback of the server exception
will be provided:

    >>> from crate.client.exceptions import ProgrammingError
    >>> http_client = HttpClient([crate_host], error_trace=True)
    >>> try:
    ...     http_client.sql("select grmpf form error arrrggghh")
    ... except ProgrammingError as e:
    ...     trace = 'TRACE: ' + str(e.error_trace)

    >>> print(trace)
    TRACE: ... mismatched input 'error' expecting {<EOF>, ...
    at io.crate...
    >>> http_client.close()
