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
        principals = ['user:%s' % userid,
                      {100: 'group:admin',
                       80: 'group:manager',
                       60: 'group:editor',
                       40: 'group:owner',
                       10: 'group:viewer'}[user.user_group]]
        for owner in user.owns:
            if owner.person_id:
                principals.append('owner:person:%s' % owner.person_id)
            elif owner.group_id:
                principals.append('owner:group:%s' % owner.group_id)
        return principals
