from core import BaseTest

from scributor.models import User
        
class UserAuthTest(BaseTest):

    def test_initial_admin_user_has_been_created(self):
        # the base unittest sets up an initial admin user
        users = self.storage.session.query(User).all()
        assert len(users) == 1
        admin = users[0]
        assert admin.userid == 'admin'
        assert admin.user_group == 100
        # note that the credentials column is not stored in plain text
        # but can be compared to plain text passwords
        assert admin.credentials == 'admin'
        assert admin.credentials.hash.startswith(b'$pbkdf2-sha512')

    def test_authenticating_user(self):
        # valid login
        self.api.post_json('/api/v1/auth/login',
                           {'user': 'admin', 'password': 'admin'},
                           status=200)
        # login with unknown user
        self.api.post_json('/api/v1/auth/login',
                           {'user': 'john', 'password': 'admin'},
                           status=401)
        # login with known user, but wrong password
        self.api.post_json('/api/v1/auth/login',
                           {'user': 'admin', 'password': 'huh'},
                           status=401)

            
    def test_retreiving_user_info(self):
        # we must be logged in as an admin user to retrieve users
        out = self.api.get('/api/v1/users/1', status=401)
        assert out.headers['Location'].endswith('/api/v1/auth/login')
        # first get an auth token
        out = self.api.post_json('/api/v1/auth/login',
                                 {'user': 'admin', 'password': 'admin'})
        token = out.json['token']
        # now we can retrive the user info
        out = self.api.get('/api/v1/users/1',
                           headers={'Authorization': 'JWT %s' % token})
        assert out.json['userid'] == 'admin'
        assert out.json['credentials'].startswith('$pbkdf2-sha512')
        
    def test_adding_users(self):
        # admin users can add users
        token = self.api.post_json(
            '/api/v1/auth/login',
            {'user': 'admin', 'password': 'admin'}).json['token']
        
        out = self.api.post_json('/api/v1/users',
                                 {'userid': 'john',
                                  'credentials': 'j0hn',
                                  'user_group': 10},
                                 headers={'Authorization': 'JWT %s' % token})
        assert out.status_code == 201
        assert out.json['userid'] == 'john'
        assert out.json['credentials'].startswith('$pbkdf2-sha512')
        # login as john, adding users should fail with a 403 unauthorized
        # since john is not an admin but an editor
        token = self.api.post_json(
            '/api/v1/auth/login',
            {'user': 'john', 'password': 'j0hn'}).json['token']
        self.api.post_json('/api/v1/users',
                           {'userid': 'pete',
                            'credentials': 'p3t3',
                            'user_group': 10},
                           headers={'Authorization': 'JWT %s' % token},
                           status=403)
        
    def test_remove_user(self):
        # add a user
        out = self.api.post_json(
            '/api/v1/users',
            {'userid': 'john', 'credentials': 'j0hn', 'user_group': 10},
            headers=dict(Authorization=self.admin_token))
        john_id = out.json['id']
        # remove the user
        self.api.delete('/api/v1/users/%s' % john_id,
                        headers=dict(Authorization=self.admin_token),
                        status=200)
        # user gone
        self.api.get('/api/v1/users/%s' % john_id,
                     headers=dict(Authorization=self.admin_token),
                     status=404)
        
    def test_home(self):
        out = self.api.get('/')
        assert out.status_code == 200
        
