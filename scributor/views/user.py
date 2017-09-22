import colander
from cornice import Service
from cornice.resource import resource, view
from cornice.validators import colander_body_validator
from pyramid.httpexceptions import HTTPNotFound

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
    id = colander.SchemaNode(colander.Int())
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
  
    def to_json(self):
        user = self.user
        return {'id': user.id,
                'user_group': user.user_group,
                'principal': user.principal,
                'credential': user.credential.hash}
    
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
        return UserSchema().serialize(self.context.to_json())

    @view(permission='add',
          schema=UserSchema(),
          validators=(colander_body_validator,),
          response_schemas={
        '201': UserBodySchema(description='Created'),
        '400': ErrorBodySchema(description='Bad Request')})
    def collection_post(self):
        "Create a new User"
        import pdb;pdb.set_trace()
        
