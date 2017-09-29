import colander
from cornice.resource import resource, view
from cornice.validators import colander_body_validator
from pyramid.httpexceptions import HTTPNotFound
import transaction

from scributor.models import User
from scributor.resources import UserResource

from scributor.utils import ErrorBodySchema, StatusBodySchema
        
def user_factory(request):
    if not 'id' in request.matchdict:
        return UserResource(request.storage, None)
    user_id = request.matchdict['id']
    user = request.storage.session.query(User).filter(User.id==user_id).first()
    if user is None:
        raise HTTPNotFound
    return UserResource(request.storage, user)

class UserSchema(colander.MappingSchema):
    id = colander.SchemaNode(colander.Int(), missing=None)
    user_group = colander.SchemaNode(colander.Int())
    userid = colander.SchemaNode(colander.String())
    credentials = colander.SchemaNode(colander.String())

class UserBodySchema(colander.MappingSchema):
    body = UserSchema()
    
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
        '200': UserBodySchema(description='User Response'),
        '401': ErrorBodySchema(description='Unauthorized'),
        '403': ErrorBodySchema(description='Forbidden'),
        '404': ErrorBodySchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a User"
        return UserSchema().serialize(self.context.to_dict())


    @view(permission='delete',
          response_schemas={
        '200': StatusBodySchema(description='Ok'),
        '401': ErrorBodySchema(description='Unauthorized'),
        '403': ErrorBodySchema(description='Forbidden'),
        '404': ErrorBodySchema(description='Not Found'),
        })
    def delete(self):
        "Delete a User"
        self.context.delete()
        return {'status': 'ok'}

    @view(permission='add',
          schema=UserSchema(),
          validators=(colander_body_validator,),
          response_schemas={
        '201': UserBodySchema(description='Created'),
        '400': ErrorBodySchema(description='Bad Request'),
        '401': ErrorBodySchema(description='Unauthorized'),
        '403': ErrorBodySchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new User"
        self.context.from_dict(self.request.validated)
        self.context.insert()
        # commit and reload user from db to trigger the credentials hashing
        self.context.reload()
        self.request.response.status = 201
        return UserSchema().serialize(self.context.to_dict())
