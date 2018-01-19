import colander
from cornice.resource import resource, view
from cornice.validators import colander_body_validator, colander_validator

from caleido.models import User
from caleido.resources import ResourceFactory, UserResource

from caleido.exceptions import StorageError
from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema,
                           OKStatus,
                           JsonMappingSchemaSerializerMixin)


def owner_validator(node, kw):
    if not kw.get('person_id') and not kw.get('group_id'):
        node.name = '%s.person_id' % node.name
        raise colander.Invalid(
            node, "Required: supply one of 'person_id' or 'group_id'")

class UserSchema(colander.MappingSchema, JsonMappingSchemaSerializerMixin):
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)
    user_group = colander.SchemaNode(colander.Int())
    userid = colander.SchemaNode(colander.String())
    credentials = colander.SchemaNode(colander.String())
    @colander.instantiate(missing=colander.drop)
    class owns(colander.SequenceSchema):
        @colander.instantiate(validator=owner_validator)
        class owner(colander.MappingSchema):
            person_id = colander.SchemaNode(colander.Integer(),
                                            missing=colander.drop)
            _person_name = colander.SchemaNode(colander.String(),
                                               missing=colander.drop)
            group_id = colander.SchemaNode(colander.Integer(),
                                           missing=colander.drop)
            _group_name = colander.SchemaNode(colander.String(),
                                              missing=colander.drop)

class UserResponseSchema(colander.MappingSchema,
                         JsonMappingSchemaSerializerMixin):
    body = UserSchema()

class UserListingResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        @colander.instantiate()
        class records(colander.SequenceSchema):
            user = UserSchema()
        status = OKStatus
        total = colander.SchemaNode(colander.Int())
        offset = colander.SchemaNode(colander.Int())
        limit = colander.SchemaNode(colander.Int())

class UserListingRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class querystring(colander.MappingSchema):
        query = colander.SchemaNode(colander.String(),
                                    missing=colander.drop)
        offset = colander.SchemaNode(colander.Int(),
                                   default=0,
                                   validator=colander.Range(min=0),
                                   missing=0)
        limit = colander.SchemaNode(colander.Int(),
                                    default=20,
                                    validator=colander.Range(0, 100),
                                    missing=20)
        format = colander.SchemaNode(
            colander.String(),
            validator=colander.OneOf(['record', 'snippet']),
            missing=colander.drop)

@resource(name='User',
          collection_path='/api/v1/user/records',
          path='/api/v1/user/records/{id}',
          tags=['user'],
          cors_origins=('*', ),
          api_security=[{'jwt':[]}],
          factory=ResourceFactory(UserResource))
class UserAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          cors_origins=('*', ),
          response_schemas={
        '200': UserResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a User"
        return UserSchema().to_json(self.context.model.to_dict())


    @view(permission='edit',
          schema=UserSchema(),
          validators=(colander_body_validator,),
          cors_origins=('*', ),
          response_schemas={
        '200': UserResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Modify a User"
        body = self.request.validated
        body['id'] = int(self.request.matchdict['id'])
        if body['credentials'].startswith('$pbkdf2'):
            del body['credentials']

        self.context.model.update_dict(body)
        try:
            self.context.put()
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return
        return UserSchema().to_json(self.context.model.to_dict())


    @view(permission='delete',
          cors_origins=('*', ),
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
          cors_origins=('*', ),
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
        user = User.from_dict(self.request.validated)
        self.context.put(user)
        # force reload the user from db to retrieve the credentials hash
        self.context.session.refresh(user)
        user = self.context.get(user.id)
        self.request.response.status = 201
        return UserSchema().to_json(user.to_dict())


    @view(permission='view',
          cors_origins=('*', ),
          schema=UserListingRequestSchema(),
          validators=(colander_validator),
          response_schemas={
        '200': UserListingResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        offset = self.request.validated['querystring']['offset']
        limit = self.request.validated['querystring']['limit']
        order_by = [User.userid.asc()]
        format = self.request.validated['querystring'].get('format')
        if format == 'record':
            format = None

        query = self.request.validated['querystring'].get('query')
        filters = []
        if query:
            filters.append(User.userid.like(query + '%'))
        listing = self.context.search(
            filters=filters,
            offset=offset,
            limit=limit,
            order_by=order_by,
            format=format,
            principals=self.request.effective_principals)

        schema = UserSchema()
        result = {'total': listing['total'],
                  'records': [],
                  'snippets': [],
                  'limit': limit,
                  'offset': offset,
                  'status': 'ok'}

        if format == 'snippet':
            result['snippets'] = [schema.to_json(user.to_dict())
                                  for user in listing['hits']]
        else:
            result['records'] = [schema.to_json(user.to_dict())
                                 for user in listing['hits']]

        return result


        listing = self.context.search(
            offset=offset,
            limit=limit,
            principals=self.request.effective_principals)
        schema = UserSchema()
        format = self.request.validated['querystring'].get('format')
        if format == 'record':
            format = None
        return {'total': listing['total'],
                'records': [schema.to_json(user.to_dict()) for user in listing['hits']],
                'limit': limit,
                'offset': offset,
                'status': 'ok'}
