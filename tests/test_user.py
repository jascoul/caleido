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
            
        
    def test_home(self):
        out = self.api.get('/')
        assert out.status_code == 200
        
