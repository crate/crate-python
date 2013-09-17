import hashlib


class BlobContainer(object):

    """ class that represents a blob collection in crate.

    can be used to retrieve blob statistics, download, upload and delete files
    """

    def __init__(self, container_name, connection):
        self.container_name = container_name
        self.conn = connection

    def _compute_digest(self, f):
        f.seek(0)
        m = hashlib.sha1()
        while True:
            d = f.read()
            if d:
                m.update(d)
            else:
                f.seek(0)
                return m.hexdigest()

    def put(self, f, digest=None):
        if digest:
            actual_digest = digest
        else:
            actual_digest = self._compute_digest(f)

        created = self.conn.client.blob_put(self.container_name, actual_digest, f)
        if digest:
            return created
        else:
            return actual_digest

    def get(self, digest):
        return self.conn.client.blob_get(self.container_name, digest)

    def delete(self, digest):
        return self.conn.client.blob_del(self.container_name, digest)

    def exists(self, digest):
        return self.conn.client.blob_exists(self.container_name, digest)

    def __repr__(self):
        return "<BlobContainer '{}'>".format(self.container_name)

