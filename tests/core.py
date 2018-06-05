import unittest

import transaction
from pyramid import testing
from webtest import TestApp as WebTestApp

from caleido import main
from caleido.storage import Storage
from caleido.models import User, Owner
from caleido.resources import UserResource

class BaseTest(unittest.TestCase):

    def app_settings(self):
        return {
            'caleido.secret': 'sekret',
            'caleido.blob_path': '/tmp/caleido.files',
            'caleido.blob_storage': 'local',
            'caleido.blob_api': 'http://unittest.localhost/api/v1/blob/upload/',
            'sqlalchemy.url': (
                'postgresql://caleido:c4l31d0@localhost/caleido')
        }

    def setUp(self):
        self.app = main({}, **self.app_settings())
        self.storage = self.app.registry['storage']
        self.api = WebTestApp(self.app,
                              extra_environ={'HTTP_HOST': 'unittest.localhost'})
        storage = Storage(self.app.registry)
        self.session = storage.make_session()
        if 'unittest' in storage.repository_info(self.session):
            storage.drop_repository(self.session, 'unittest')
            transaction.commit()
        storage.create_repository(self.session, 'unittest', 'unittest.localhost')
        storage.initialize_repository(self.session, 'unittest', 'admin', 'admin')
        transaction.commit()

    def admin_token(self):
        return self.api.post_json(
            '/api/v1/auth/login',
            {'user': 'admin', 'password': 'admin'}).json['token']

    def generate_test_token(self, user_group_password, owners=None):
        """Returns a token for owner / editor / admin / viewer
        If the user does not exist, a new user is created
        """
        response = self.api.post_json(
                '/api/v1/auth/login',
                {'user': user_group_password,
                 'password': user_group_password}
                ,status=[200, 401])
        if response.status_code == 401:
            context = UserResource(self.storage.registry, self.session)
            context.put(
                User(userid=user_group_password,
                     credentials=user_group_password,
                     owns=[Owner(**d) for d in (owners or [])],
                     user_group={'admin': 100,
                                 'manager': 80,
                                 'editor': 60,
                                 'owner': 40,
                                 'viewer': 10}[user_group_password]),
                principals=['group:admin'])
            transaction.commit()
            response = self.api.post_json(
                '/api/v1/auth/login',
                {'user': user_group_password, 'password': user_group_password})
        return response.json['token']

    def tearDown(self):
        testing.tearDown()
        transaction.abort()


