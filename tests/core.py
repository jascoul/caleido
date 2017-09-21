import unittest

import transaction
from pyramid import testing
from webtest import TestApp as WebTestApp

from scributor import main

class BaseTest(unittest.TestCase):
    
    def app_settings(self):
        return {
            'sqlalchemy.url': (
                'postgresql://scributor:scr1but0r@localhost/scributor')
        }
        
    def setUp(self):
        self.app = main({}, **self.app_settings())
        self.storage = self.app.registry['storage']
        self.api = WebTestApp(self.app)
    
    def init_database(self):
        self.storage.create_all()
        
    def tearDown(self):
        testing.tearDown()
        transaction.abort()
        self.storage.drop_all()

        
