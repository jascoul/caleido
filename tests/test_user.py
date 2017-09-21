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
        assert admin.credential == 'admin'
        assert admin.user_group == 100
        
        
    def test_home(self):
        out = self.api.get('/')
        assert out.status_code == 200
        
