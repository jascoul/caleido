import os
import uuid
import hashlib

from zope.interface import implementer

from caleido.interfaces import IBlobStoreBackend

class BlobStore(object):
    def __init__(self, backend):
        self.backend = backend

    def new_blobkey(self):
        return uuid.uuid4().hex

    def blob_exists(self, blob_key):
        return self.backend.blob_exists(blob_key)

    def upload_url(self, blob_key):
        return self.backend.upload_url(blob_key)

    def download_url(self, blob_key):
        return self.backend.download_url(blob_key)

    def receive_blob(self, request, blob):
        return self.backend.receive_blob(request, blob)

    def serve_blob(self, request, response, blob):
        return self.backend.serve_blob(request, response, blob)

    def finalize_blob(self, blob):
        if not self.backend.blob_exists(blob.model.blob_key):
            return False
        if not blob.model.checksum:
            blob.model.checksum = self.backend.blob_checksum(blob.model.blob_key)
            blob.put()
        return True

@implementer(IBlobStoreBackend)
class LocalBlobStore(object):

    def __init__(self, repo_config):
        self.repository = repo_config
        self._path = self._get_root_path(
            repo_config.registry.settings['caleido.blob_path'])

    def _get_root_path(self, path):
        if path.startswith('/'):
            root = path
        else:
            root = os.path.dirname(__file__)
            root = os.path.dirname(root)
            assert root.endswith('src')
            root = os.path.dirname(root)
            root = os.path.join(root,
                                path,
                                self.repository.namespace)
        return root

    def _blob_key_path(self, blob_key, makedirs=False):
        directory = os.path.join(self._path, blob_key[-3:])
        if makedirs and not os.path.isdir(directory):
            os.makedirs(directory)
        return os.path.join(directory, blob_key)


    def blob_exists(self, blob_key):
        "Determine if a blob exists in the filesystem"
        return os.path.isfile(self._blob_key_path(blob_key))

    def upload_url(self, blob_key):
        "Create an upload url that can be used to POST bytes"
        return '%s/api/v1/blob/upload/%s' % (self.repository.api_host_url,
                                             blob_key)
    def download_url(self, blob_key):
        return '%s/api/v1/blob/download/%s' % (self.repository.api_host_url,
                                               blob_key)

    def serve_blob(self, request, response, blob):
        "Modify the response to servce bytes from blob_key"
        response.content_type = blob.model.format
        path = self._blob_key_path(blob.model.blob_key)
        with open(path, 'rb') as fp:
            response.body = fp.read()
        return response


    def receive_blob(self, request, blob):
        path = self._blob_key_path(blob.model.blob_key, makedirs=True)
        with open(path, 'wb') as fp:
            fp.write(request.body)
        blob.model.checksum = hashlib.md5(request.body).hexdigest()
        blob.put()

def includeme(config):
    config.registry.registerUtility(LocalBlobStore, IBlobStoreBackend, 'local')

