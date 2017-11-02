import time

import jwt
import pytest
import transaction
from pyramid.httpexceptions import HTTPForbidden

from caleido.models import User
from caleido.resources import UserResource

from core import BaseTest


class UserAuthTest(BaseTest):

    def test_initial_admin_user_has_been_created(self):
        # the base unittest sets up an initial admin user
        session = self.storage.make_session(namespace='unittest')
        users = session.query(User).all()
        assert len(users) == 1
        admin = users[0]
        assert admin.userid == 'admin'
        assert admin.user_group == 100
        # note that the credentials column is not stored in plain text
        # but can be compared to plain text passwords
        assert admin.credentials == 'admin'
        assert admin.credentials.hash.startswith(b'$pbkdf2-sha512')


    def test_resource_methods_with_specified_principals(self):
        # this tests the explicity passing of principals into the
        # resource methods (get, put, delete).
        # With normal webrequests, this is evaluated before executing the
        # view by pyramid, so the principals do not need to be passed.

        session = self.storage.make_session(namespace='unittest')
        context = UserResource(self.storage.registry, session)
        # let's try to retrieve the admin user as user john
        with pytest.raises(HTTPForbidden):
            context.get(1, principals=['user:john'])
        # create user john as editor
        john = context.put(
            User(userid='john', credentials='j0hn', user_group=10),
            principals=['group:admin'])
        # user john should be retrievable by user john
        user = context.get(john.id, principals=['user:john'])
        assert user is not None
        assert user.id == john.id
        # john can not delete himself
        with pytest.raises(HTTPForbidden):
            context.delete(john, principals=['user:john'])
        # but an admin can
        context.delete(john, principals=['group:admin'])

class UserAuthWebTest(BaseTest):

    def test_authenticating_user(self):
        # valid login
        out = self.api.post_json('/api/v1/auth/login',
                                 {'user': 'admin', 'password': 'admin'},
                                 status=200)
        assert 'token' in out.json
        # login with unknown user
        self.api.post_json('/api/v1/auth/login',
                           {'user': 'john', 'password': 'admin'},
                           status=401)
        # login with known user, but wrong password
        self.api.post_json('/api/v1/auth/login',
                           {'user': 'admin', 'password': 'huh'},
                           status=401)

    def test_authorization_with_expired_token_and_renew_it(self):
        # first let's get a valid token
        out = self.api.post_json('/api/v1/auth/login',
                                 {'user': 'admin', 'password': 'admin'},
                                 status=200)
        old_token = out.json['token']
        decoded_token = jwt.decode(old_token, verify=False)
        old_expiration = decoded_token['exp']
        # now change the expiration time to the past
        decoded_token['exp'] = 0
        # encode the token again
        token = jwt.encode(decoded_token,
                           self.app_settings()['caleido.secret'],
                           algorithm='HS512').decode('utf8')
        # now let's try to retrieve the admin user, it should result in 403
        self.api.get('/api/v1/user/records/1',
                     headers={'Authorization': 'Bearer %s' % token},
                     status=403)
        # we can't renew the token, because it is expired
        out = self.api.post_json('/api/v1/auth/renew',
                                 {'token': token},
                                 status=401)
        assert out.json['errors'][0][
            'description'] == 'Invalid JWT token: Signature has expired'
        # let's wait one second, and renew the old valid token
        time.sleep(1)
        out = self.api.post_json('/api/v1/auth/renew',
                                 {'token': old_token})
        token = out.json['token']
        decoded_token = jwt.decode(token, verify=False)
        assert decoded_token['exp'] > old_expiration
        # now we should be able to retrieve the user
        out = self.api.get('/api/v1/user/records/1',
                           headers={'Authorization': 'Bearer %s' % token})

    def test_retreiving_user_info(self):
        # we must be logged in as an admin user to retrieve users
        out = self.api.get('/api/v1/user/records/1', status=401)
        assert out.headers['Location'].endswith('/api/v1/auth/login')
        # first get an auth token
        out = self.api.post_json('/api/v1/auth/login',
                                 {'user': 'admin', 'password': 'admin'})
        token = out.json['token']
        # now we can retrive the user info
        out = self.api.get('/api/v1/user/records/1',
                           headers={'Authorization': 'Bearer %s' % token})
        assert out.json['userid'] == 'admin'
        assert out.json['credentials'].startswith('$pbkdf2-sha512')

    def test_adding_users(self):
        # admin users can add users
        token = self.api.post_json(
            '/api/v1/auth/login',
            {'user': 'admin', 'password': 'admin'}).json['token']

        out = self.api.post_json('/api/v1/user/records',
                                 {'userid': 'john',
                                  'credentials': 'j0hn',
                                  'user_group': 10},
                                 headers={'Authorization': 'Bearer %s' % token})
        assert out.status_code == 201
        assert out.json['userid'] == 'john'
        assert out.json['credentials'].startswith('$pbkdf2-sha512')
        # login as john, adding users should fail with a 403 unauthorized
        # since john is not an admin but an editor
        token = self.api.post_json(
            '/api/v1/auth/login',
            {'user': 'john', 'password': 'j0hn'}).json['token']
        self.api.post_json('/api/v1/user/records',
                           {'userid': 'pete',
                            'credentials': 'p3t3',
                            'user_group': 10},
                           headers={'Authorization': 'Bearer %s' % token},
                           status=403)

    def test_remove_user(self):
        # first add a user
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json(
            '/api/v1/user/records',
            {'userid': 'john', 'credentials': 'j0hn', 'user_group': 10},
            headers=headers)
        john_id = out.json['id']
        # remove the user
        self.api.delete('/api/v1/user/records/%s' % john_id,
                        headers=headers,
                        status=200)
        # user gone
        self.api.get('/api/v1/user/records/%s' % john_id,
                     headers=headers,
                     status=404)

    def test_listing_users(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        # add a dozen users
        session = self.storage.make_session(namespace='unittest')
        for i in range(12):
            session.add(User(userid='user_%s' % i,
                             credentials='user_%s' % i,
                             user_group=10))
        session.flush()
        transaction.commit()
        # admin user can retrieve all users
        out = self.api.get('/api/v1/user/records?limit=10', headers=headers)
        assert len(out.json['records']) == 10
        assert out.json['total'] == 13
        # lets retrieve the next page with the remaining users
        out = self.api.get('/api/v1/user/records?offset=10', headers=headers)
        assert len(out.json['records']) == 3
        assert out.json['total'] == 13
        # non admin users can only retrieve themselves
        token = self.api.post_json(
            '/api/v1/auth/login',
            {'user': 'user_4', 'password': 'user_4'}).json['token']
        out = self.api.get('/api/v1/user/records',
                           headers={'Authorization': 'Bearer %s' % token})
        assert len(out.json['records']) == 1
        assert out.json['records'][0]['userid'] == 'user_4'
