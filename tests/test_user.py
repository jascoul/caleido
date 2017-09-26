from core import BaseTest

from scributor.models import User
        
class UserTest(BaseTest):

    def test_initial_admin_user_has_been_created(self):
        # the base unittest sets up an initial admin user
        session = self.storage.session()
        users = session.query(User).all()
        assert len(users) == 1
        admin = users[0]
        assert admin.principal == 'admin'
        assert admin.user_group == 100
        # note that the credential column is not stored in plain text
        # but can be compared to plain text passwords
        assert admin.credential == 'admin'
        assert admin.credential.hash.startswith(b'$pbkdf2-sha512')

            
    def test_listing_users(self):
        self.api.get('/api/v1/users/1', status=200)
        self.api.get('/api/v1/users/2', status=404)

    def test_add_user(self):
        out = self.api.post_json('/api/v1/users',
                                 {'principal': 'john',
                                  'credential': 'j0hn',
                                  'user_group': 10})
        assert out.status_code == 201
        assert out.json['principal'] == 'john'
        assert out.json['credential'].startswith('$pbkdf2-sha512')
        
    def test_home(self):
        out = self.api.get('/')
        assert out.status_code == 200
        
