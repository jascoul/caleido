import unittest

import transaction
from pyramid import testing
from webtest import TestApp

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
        self.config = testing.setUp(settings=self.app_settings())
        
        self.config.include('scributor.models')
        settings = self.config.get_settings()

        from scributor.models import (
            get_engine,
            get_session_factory,
            get_tm_session,
            )

        self.engine = get_engine(settings)
        session_factory = get_session_factory(self.engine)

        self.session = get_tm_session(session_factory, transaction.manager)

    def init_database(self):
        from scributor.models import Base
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        from scributor.models import Base

        testing.tearDown()
        transaction.abort()
        Base.metadata.drop_all(self.engine)

class ScributorTest(BaseTest):

    def test_case(self):
        app = TestApp(main({}, **self.app_settings()))
        app.get('/status', status=404)
        
