.. _blobs:

=====
Blobs
=====

The CrateDB Python client library provides full access to the powerful
:ref:`blob storage capabilities <crate-reference:blob_support>` of your
CrateDB cluster.

.. rubric:: Table of contents

.. contents::
   :local:

Get a blob container
====================

The first thing you will need to do is connect to CrateDB. Follow the
instructions in the :ref:`connection document <connect>` for more detailed
information.

For the sake of this example, we will do the following:

    >>> from crate import client
    >>> connection = client.connect("http://localhost:4200/")

This is a simple connection that connects to a CrateDB node running on
the local host with the :ref:`crate-reference:interface-http` listening
on port 4200 (the default).

To work with blobs in CrateDB, you must specifically create
:ref:`blob tables <crate-reference:blob_support>`.

The CrateDB Python client allows you to interact with these blob tables via a
blob container, which you can create like this:

    >>> blob_container = connection.get_blob_container('my_blobs')
    >>> blob_container
    <BlobContainer 'my_blobs'>

Here, we have created a ``BlobContainer`` for the ``my_blobs`` table, using
``connection`` object.

Now we can start working with our blob container.

Working with the blob container
===============================

Upload blobs
------------

The blob container can work with files or *file-like objects*, as long as
produce bytes when read.

What is a file-like object? Well, to put it simply, any object that provides a
``read()`` method.

The stream objects provided by the Python standard library :mod:`py:io` and
:mod:`py:tempfile` modules are the most commonly used file-like objects.

The :class:`py:io.StringIO` class is not suitable, as it produces Unicode strings when
read. But you can easily encode a Unicode string and feed it to a :class:`py:io.BytesIO`
object.

Here's a trivial example:

    >>> import io
    >>> bytestream = "An example sentence.".encode("utf8")
    >>> file = io.BytesIO(bytestream)

This file can then be uploaded to the blob table using the ``put`` method:

    >>> blob_container.put(file)
    '6f10281ad07d4a35c6ec2f993e6376032b77181d'

Notice that this method computes and returns an `SHA-1 digest`_. This is
necessary for attempting to save the blob to CrateDB.

If you already have the SHA-1 digest computed, or are able to compute it as part
of an existing read, this may improve the performance of your application.

If you pass in a SHA-1 digest, it will not be recomputed:

    >>> file.seek(0) # seek to the beginning before attempting to re-upload

    >>> digest = "6f10281ad07d4a35c6ec2f993e6376032b77181d"
    >>> blob_container.put(file, digest=digest)
    False

Notice that the method returned ``False`` this time. If you specify a digest,
the return value of the ``put`` method is a boolean indicating whether the
object was written or not. In this instance, it was not written, because the
digest is the same as an existing object.

Let's make a new object:

    >>> bytestream = "Another example sentence.".encode("utf8")
    >>> digest = hashlib.sha1(bytestream).hexdigest()
    >>> another_file = io.BytesIO(bytestream)

And upload it:

    >>> blob_container.put(another_file, digest)
    True

The ``put`` method returns ``True``, indicating that the object has been
written to the blob container.

Retrieve blobs
--------------

To retrieve a blob, you need to know its digest.

Let's use the ``digest`` variable we created before to check whether that object
exists with the ``exists`` method:

    >>> blob_container.exists(digest)
    True

This method returns a boolean value. And in this instance, ``True`` indicates
that the blob we're interested in is contained within the blob container.

You can get the blob, with the ``get`` method, like so:

    >>> blob_generator = blob_container.get(digest)

Blobs are read in chunks. The default size of these chunks is 128 kilobytes,
but this can be changed by supplying the desired chunk size to the ``get``
method, like so:

    >>> res = blob_container.get(digest, 1024 * 128)

The ``blob`` object is a Python :term:`py:generator`, meaning that you can call
``next(blob)`` for each new chunk you want to read, until you encounter a
``StopIteration`` exception.

Instead of calling ``next()`` manually, the idiomatic way to iterate over a
generator is like so:

    >>> blob_content = b''
    >>> for chunk in blob_container.get(digest):
    ...     blob_content += chunk


Delete blobs
------------

You can delete a blob with the ``delete`` method and the blob digest, like so:

    >>> blob_container.delete(digest)
    True

This method returns a boolean status value. In this instance, ``True``
indicates that the blob was deleted.

We can verify that, like so:

    >>> blob_container.exists(digest)
    False

.. _SHA-1 digest: https://en.wikipedia.org/wiki/SHA-1
