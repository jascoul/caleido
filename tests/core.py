import unittest

import transaction
from pyramid import testing
from webtest import TestApp as WebTestApp

from caleido import main
from caleido.storage import Storage

class BaseTest(unittest.TestCase):

    def app_settings(self):
        return {
            'caleido.secret': 'sekret',
            'sqlalchemy.url': (
                'postgresql://caleido:c4l31d0@localhost/caleido')
        }

    def setUp(self):
        self.app = main({}, **self.app_settings())
        self.storage = self.app.registry['storage']
        self.api = WebTestApp(self.app)
        storage = Storage(self.app.registry)
        storage.drop_all()
        storage.create_all()
        storage.initialize('admin', 'admin')

    def admin_token(self):
        return self.api.post_json(
            '/api/v1/auth/login',
            {'user': 'admin', 'password': 'admin'}).json['token']

    def tearDown(self):
        testing.tearDown()
        transaction.abort()


