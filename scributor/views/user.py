import colander
from cornice.resource import resource, view
from cornice.validators import colander_body_validator
from pyramid.httpexceptions import HTTPNotFound
import transaction

from scributor.models import User
from scributor.utils import ErrorBodySchema
        
def user_factory(request):
    if not 'id' in request.matchdict:
        return UserResource(None)
    user_id = request.matchdict['id']
    session = request.storage.session()
    user = session.query(User).filter(User.id==user_id).first()
    if user is None:
        raise HTTPNotFound
    return UserResource(user)

class UserSchema(colander.MappingSchema):
    id = colander.SchemaNode(colander.Int(), missing=None)
    user_group = colander.SchemaNode(colander.Int())
    principal = colander.SchemaNode(colander.String())
    credential = colander.SchemaNode(colander.String())

class UserBodySchema(colander.MappingSchema):
    body = UserSchema()
    
class UserResource(object):
    def __init__(self, user):
        self.user = user
        
    def __acl__(self):
        import pdb;pdb.set_trace()
  
    def to_dict(self):
        return {'id': self.user.id,
                'user_group': self.user.user_group,
                'principal': self.user.principal,
                'credential': self.user.credential.hash.decode('utf8')}
    
    def from_dict(self, data):
        return User(**data)
    
@resource(name='User',
          collection_path='/api/v1/users',
          path='/api/v1/users/{id}',
          factory=user_factory)    
class UserAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context
        
    @view(permission='view',
          response_schemas={
        '200': UserBodySchema(description='User Response')})
    def get(self):
        "Retrieve a User"
        return UserSchema().serialize(self.context.to_dict())

    @view(permission='add',
          schema=UserSchema(),
          validators=(colander_body_validator,),
          response_schemas={
        '201': UserBodySchema(description='Created'),
        '400': ErrorBodySchema(description='Bad Request')})
    def collection_post(self):
        "Create a new User"
        user = self.context.from_dict(self.request.validated)
        session = self.request.storage.session()
        session.add(user)
        session.flush()
        new_user_id = user.id
        # commit and reload user from db to trigger the credential hashing
        transaction.commit()
        session = self.request.storage.session()
        user = session.query(User).filter(User.id==new_user_id).first()
        self.request.response.status = 201
        return UserSchema().serialize(UserResource(user).to_dict())
