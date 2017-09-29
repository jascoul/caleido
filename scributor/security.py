import json

from scributor.models import User

def add_role_principals(userid, request):
    return request.jwt_claims.get('principals') or []

def authenticator_factory(request):
    return BasicAuthenticator(request.storage)

class BasicAuthenticator(object):
    def __init__(self, storage):
        self.storage = storage

    def principals(self, userid, credentials):
        user = self.storage.session.query(User).filter(User.userid==userid).first()
        if user is None or user.credentials != credentials:
            return
        
        return ['user:%s' % userid,
                {100: 'group:admin',
                 10: 'group:editor'}[user.user_group]]
        
