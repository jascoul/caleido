from caleido.models import User

def add_role_principals(userid, request):
    return request.jwt_claims.get('principals') or []

def authenticator_factory(request):
    return BasicAuthenticator(request.dbsession)

class BasicAuthenticator(object):
    def __init__(self, session):
        self.session = session

    def existing_user(self, userid):
        user = self.session.query(User).filter(User.userid==userid).first()
        return user is not None
    
    def valid_user(self, userid, credentials):
        user = self.session.query(User).filter(User.userid==userid).first()
        if user is None or user.credentials != credentials:
            return False
        return True
        
    def principals(self, userid):
        user = self.session.query(User).filter(User.userid==userid).first()
        if user is None:
            return []
        return ['user:%s' % userid,
                {100: 'group:admin',
                 10: 'group:editor'}[user.user_group]]
        
