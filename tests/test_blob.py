import transaction

from core import BaseTest
from caleido.models import User

class BlobStorageTest(BaseTest):

    def test_blob_upload_as_admin(self):
        content = 'This is a test!'.encode('utf8')
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/blob/records',
                                 {'name': 'test.txt',
                                  'bytes': str(len(content)),
                                  'format': 'text/plain'},
                                 headers=headers,
                                 status=201)
        blob_key = out.json.get('blob_key')
        assert blob_key is not None
        upload_url = out.json['upload_url']
        upload_headers = headers.copy()
        upload_headers['Content-Length'] = str(len(content))
        upload_headers['Content-Type'] = 'text/plain'
        out = self.api.post(upload_url,
                            content,
                            headers=upload_headers,
                            status=200)
        # there is no way to download a blob, it has to be connected
        # to a work first.
        out = self.api.get('/api/v1/blob/records/%s' % out.json['id'],
                           headers=headers,
                           status=200)
        assert out.json['checksum'] == '702edca0b2181c15d457eacac39de39b'
