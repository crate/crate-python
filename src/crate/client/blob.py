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

import hashlib


class BlobContainer(object):
    """ class that represents a blob collection in crate.

    can be used to download, upload and delete blobs
    """

    def __init__(self, container_name, connection):
        self.container_name = container_name
        self.conn = connection

    def _compute_digest(self, f):
        f.seek(0)
        m = hashlib.sha1()
        while True:
            d = f.read(1024 * 32)
            if not d:
                break
            m.update(d)
        f.seek(0)
        return m.hexdigest()

    def put(self, f, digest=None):
        """
        Upload a blob

        :param f:
            File object to be uploaded (required to support seek if digest is
            not provided).
        :param digest:
            Optional SHA-1 hex digest of the file contents. Gets computed
            before actual upload if not provided, which requires an extra file
            read.
        :return:
            The hex digest of the uploaded blob if not provided in the call.
            Otherwise a boolean indicating if the blob has been newly created.
        """

        if digest:
            actual_digest = digest
        else:
            actual_digest = self._compute_digest(f)

        created = self.conn.client.blob_put(self.container_name,
                                            actual_digest, f)
        if digest:
            return created
        return actual_digest

    def get(self, digest):
        """
        Return the contents of a blob

        :param digest: the hex digest of the blob to return
        :return: generator returning chunks of data
        """
        return self.conn.client.blob_get(self.container_name, digest)

    def delete(self, digest):
        """
        Delete a blob

        :param digest: the hex digest of the blob to be deleted
        :return: True if blob existed
        """
        return self.conn.client.blob_del(self.container_name, digest)

    def exists(self, digest):
        """
        Check if a blob exists

        :param digest: Hex digest of the blob
        :return: Boolean indicating existence of the blob
        """
        return self.conn.client.blob_exists(self.container_name, digest)

    def __repr__(self):
        return "<BlobContainer '{0}'>".format(self.container_name)
