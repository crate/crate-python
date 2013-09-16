

class BlobContainer(object):

    """ class that represents a blob collection in crate.

    can be used to retrieve blob statistics, download, upload and delete files
    """

    def __init__(self, container_name, connection):
        self.container_name = container_name
        self.conn = connection

    @property
    def _blob_path(self):
        return self.container_name + '/_blobs/'

    def stats(self):
        return self.conn.client._request('GET', self._blob_path)

    def __repr__(self):
        return "<BlobContainer '{}'>".format(self.container_name)
