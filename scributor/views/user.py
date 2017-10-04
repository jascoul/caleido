import colander
from cornice.resource import resource, view
from cornice.validators import colander_body_validator, colander_validator
from pyramid.httpexceptions import HTTPNotFound
import transaction

from scributor.models import User
from scributor.resources import UserResource

from scributor.utils import (ErrorResponseSchema,
                             StatusResponseSchema,
                             PagingInfoSchema,
                             OKStatus)
        
def user_factory(request):
    if not 'id' in request.matchdict:
        return UserResource(request.dbsession, None)
    user_id = request.matchdict['id']
    user = request.dbsession.query(User).filter(User.id==user_id).first()
    if user is None:
        raise HTTPNotFound
    return UserResource(request.dbsession, user)

class UserSchema(colander.MappingSchema):
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)
    user_group = colander.SchemaNode(colander.Int())
    userid = colander.SchemaNode(colander.String())
    credentials = colander.SchemaNode(colander.String())

class UserResponseSchema(colander.MappingSchema):
    body = UserSchema()

class UserListingResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        @colander.instantiate()
        class result(colander.SequenceSchema):
            user = UserSchema()
        status = OKStatus
        total = colander.SchemaNode(colander.Int())
        page = PagingInfoSchema()
        
class UserListingRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class querystring(colander.MappingSchema):
        page = colander.SchemaNode(colander.Int(),
                                   default=1,
                                   validator=colander.Range(min=1),
                                   missing=1)
        page_size = colander.SchemaNode(colander.Int(),
                                        default=20,
                                        validator=colander.Range(0, 100),
                                        missing=20)
    
@resource(name='User',
          collection_path='/api/v1/users',
          path='/api/v1/users/{id}',
          factory=user_factory)    
class UserAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context
        
    @view(permission='view',
          tags=['user'],
          api_security=[{'jwt':[]}],
          response_schemas={
        '200': UserResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a User"
        return UserSchema().serialize(self.context.to_dict())


    @view(permission='delete',
          tags=['user'],
          api_security=[{'jwt':[]}],
          response_schemas={
        '200': StatusResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def delete(self):
        "Delete a User"
        self.context.delete()
        return {'status': 'ok'}

    @view(permission='add',
          tags=['user'],
          api_security=[{'jwt':[]}],
          schema=UserSchema(),
          validators=(colander_body_validator,),
          response_schemas={
        '201': UserResponseSchema(description='Created'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new User"
        self.context.from_dict(self.request.validated)
        self.context.insert()
        # commit and reload user from db to trigger the credentials hashing
        self.context.reload()
        self.request.response.status = 201
        return UserSchema().serialize(self.context.to_dict())


    @view(permission='view',
          tags=['user'],
          api_security=[{'jwt':[]}],
          schema=UserListingRequestSchema(),
          validators=(colander_validator),
          response_schemas={
        '200': UserListingResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        query = self.context.listing_query()
        query = self.context.acl_filter(query,
                                        self.request.authenticated_userid,
                                        self.request.effective_principals)
        listing = self.context.list(
            query,
            page=self.request.validated['querystring']['page'],
            page_size=self.request.validated['querystring']['page_size'])
        schema = UserSchema()
        listing['result'] = [schema.serialize(user.to_dict())
                             for user in listing['result']]
        return listing
