import unittest

import transaction
from pyramid import testing
from webtest import TestApp as WebTestApp
import transaction
from scributor import main

class BaseTest(unittest.TestCase):
    
    def app_settings(self):
        return {
            'scributor.secret': 'sekret',
            'sqlalchemy.url': (
                'postgresql://scributor:scr1but0r@localhost/scributor')
        }
        
    def setUp(self):
        self.app = main({}, **self.app_settings())
        self.storage = self.app.registry['storage']
        self.api = WebTestApp(self.app)
        self.storage.drop_all()
        self.storage.create_all()
        with transaction.manager:
            self.storage.initialize('admin', 'admin')

        self.admin_token = 'JWT %s' % self.api.post_json(
            '/api/v1/auth/login',
            {'user': 'admin', 'password': 'admin'}).json['token']
        
    def tearDown(self):
        testing.tearDown()
        transaction.abort()

        
