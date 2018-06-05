from zope.interface import Interface, Attribute

class IBlobStoreBackend(Interface):

    repository = Attribute('repository config')

    def blob_exists(self, blob_key):
        "Determine if a blob exists in the filesystem"
        pass

    def upload_url(self, blob_key):
        "Create an upload url that can be used to POST bytes"
        pass

    def receive_blob(self, request, blob):
        """Optionally do something with the upload request

        The local backend (which is not suitable for production)
        will receive the POST request with the full body here,
        The NGINX backend works similar, but only receives a
        header with file information.
        In case of the GCS blobstore, this method will not be called.

        Note that some backends can add the checksum to the blob object here
        this way, an additional call to blob_checksum is not needed later on.
        """
        pass

    def blob_checksum(self, blobkey):
        """Optionally return md5 checksum for blobkey,
        only called when receive_blob() has not returned a checksum
        """
        pass

    def serve_blob(self, request, response, blob):
        "Modify the response to servce bytes from blob_key"
        pass

    def local_path(self, blob):
        """Returns a local path to the blob.
        This means the blob has to be downloaded to the server
        for some backends"""
        pass


class IBlobTransform(Interface):
    name = Attribute('The name of the transform')
    supported_formats = Attribute('''
    list of mimetypes to which this transform can be applied.
    Wildcards are allowed (image/*)''')
    returns_bytes = Attribute('Boolean indicating transform returns binary data')
    returns_text = Attribute('Boolean indicating transform returns textual data')
    returns_obj = Attribute('Boolean indicating transform returns object data')

    def execute(self, blob_path):
        "run the transform returning the bytes/text or dict result"
