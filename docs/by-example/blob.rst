==================
Blob container API
==================

The connection object provides a convenience API for easy access to
:ref:`blob tables <crate-reference:blob_support>`.


Get blob container handle
=========================

Create a connection:

    >>> from crate.client import connect
    >>> client = connect([crate_host])

Get a blob container:

    >>> container = client.get_blob_container('myfiles')


Store blobs
===========

The container allows to store a blob without explicitly providing the hash
for the blob. This feature is possible if the blob is provided as a seekable
stream like object.

Store a ``StringIO`` stream:

    >>> from io import BytesIO
    >>> f = BytesIO(b'StringIO data')
    >>> stringio_bob = container.put(f)
    >>> stringio_bob
    '0cd4511d696823779692484029f234471cd21f28'

Store from a file:

    >>> from tempfile import TemporaryFile
    >>> f = TemporaryFile()
    >>> _ = f.write(b'File data')
    >>> _ = f.seek(0)
    >>> file_blob = container.put(f)
    >>> file_blob
    'ea6e03a4a4ee8a2366fe5a88af2bde61797973ea'
    >>> f.close()

If the blob data is not provided as a seekable stream the hash must be
provided explicitly:

    >>> import hashlib
    >>> string_data = b'String data'
    >>> string_blob = hashlib.sha1(string_data).hexdigest()
    >>> container.put(string_data, string_blob)
    True


Check for existence
===================

    >>> container.exists(string_blob)
    True
    >>> container.exists('unknown')
    False


Retrieve blobs
==============

Blobs can be retrieved using its hash:

    >>> blob_stream = container.get(string_blob)
    >>> blob_stream
    <generator ...>
    >>> data = next(blob_stream)
    >>> data == string_data
    True


Delete blobs
============

Blobs can be deleted using its hash:

    >>> container.delete(string_blob)
    True
    >>> container.exists(string_blob)
    False

Trying to delete a not existing blob:

    >>> container.delete(string_blob)
    False

Close connection
================

Close the connection to clear the connection pool:

    >>> client.close()
