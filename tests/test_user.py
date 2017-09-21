from core import BaseTest
        
class UserTest(BaseTest):

    def test_home(self):
        out = self.api.get('/')
        assert out.status_code == 200
        
