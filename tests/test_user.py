import unittest

import transaction
from pyramid import testing
from webtest import TestApp as WebTestApp

from scributor import main

def dummy_request(dbsession):
    return testing.DummyRequest(dbsession=dbsession)

class BaseTest(unittest.TestCase):
    
    def app_settings(self, **settings):
        app_settings = {
            'sqlalchemy.url': 'postgresql://scributor:scr1but0r@localhost/scributor'
        }
        app_settings.update(settings)
        return app_settings
        
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
        
class ScributorTest(BaseTest):

    def test_case(self):
        self.api.get('/status', status=404)
        
