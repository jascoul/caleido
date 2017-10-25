import colander
from cornice.resource import resource, view
from cornice.validators import colander_validator

from caleido.models import Actor
from caleido.resources import ResourceFactory, ActorResource

from caleido.exceptions import StorageError
from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema,
                           JsonMappingSchemaSerializerMixin,
                           colander_bound_repository_body_validator)

@colander.deferred
def deferred_actor_type_validator(node, kw):
    types = kw['repository'].type_config('actor_type')
    return colander.OneOf([t['key'] for t in types])

@colander.deferred
def deferred_account_type_validator(node, kw):
    types = kw['repository'].type_config('account_type')
    return colander.OneOf([t['key'] for t in types])


def actor_validator(node, kw):
    if kw['type'] == 'individual':
        required_name_field = 'family_name'
    else:
        required_name_field = 'corporate_international_name'
    if not kw.get(required_name_field):
        node.name = '%s.%s' % (node.name, required_name_field)
        raise colander.Invalid(node, node.get(required_name_field).missing_msg)

class ActorSchema(colander.MappingSchema, JsonMappingSchemaSerializerMixin):
    def __init__(self, *args, **kwargs):
        kwargs['validator'] = actor_validator
        super(ActorSchema, self).__init__(*args, **kwargs)

    id = colander.SchemaNode(colander.Int())
    type = colander.SchemaNode(colander.String(),
                               validator=deferred_actor_type_validator)
    name = colander.SchemaNode(colander.String(),
                                missing=colander.drop)
    family_name = colander.SchemaNode(colander.String(),
                                      missing=colander.drop)
    family_name_prefix = colander.SchemaNode(colander.String(),
                                             missing=colander.drop)
    family_name_suffix = colander.SchemaNode(colander.String(),
                                             missing=colander.drop)
    given_name = colander.SchemaNode(colander.String(), missing=colander.drop)
    initials = colander.SchemaNode(colander.String(), missing=colander.drop)
    corporate_international_name = colander.SchemaNode(colander.String(),
                                                       missing=colander.drop)
    corporate_native_name = colander.SchemaNode(colander.String(),
                                                missing=colander.drop)
    corporate_abbreviated_name = colander.SchemaNode(colander.String(),
                                                     missing=colander.drop)

    @colander.instantiate(missing=colander.drop)
    class accounts(colander.SequenceSchema):
        @colander.instantiate()
        class account(colander.MappingSchema):
            type = colander.SchemaNode(colander.String(),
                                       validator=deferred_account_type_validator)
            value = colander.SchemaNode(colander.String())

class ActorPostSchema(ActorSchema):
    # similar to actor schema, but id is optional
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)

class ActorResponseSchema(colander.MappingSchema):
    body = ActorSchema()

class ActorListingResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        @colander.instantiate()
        class records(colander.SequenceSchema):
            actor = ActorSchema()
        total = colander.SchemaNode(colander.Int())
        offset = colander.SchemaNode(colander.Int())
        limit = colander.SchemaNode(colander.Int())

class ActorListingRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class querystring(colander.MappingSchema):
        offset = colander.SchemaNode(colander.Int(),
                                   default=0,
                                   validator=colander.Range(min=0),
                                   missing=0)
        limit = colander.SchemaNode(colander.Int(),
                                    default=20,
                                    validator=colander.Range(0, 100),
                                    missing=20)

@resource(name='Actor',
          collection_path='/api/v1/actors',
          path='/api/v1/actors/{id}',
          tags=['actor'],
          api_security=[{'jwt':[]}],
          factory=ResourceFactory(ActorResource))
class ActorAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          response_schemas={
        '200': ActorResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a Actor"
        return ActorSchema().to_json(self.context.model.to_dict())

    @view(permission='edit',
          schema=ActorSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '200': ActorResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Modify an Actor"
        body = self.request.validated
        body['id'] = int(self.request.matchdict['id'])
        self.context.model.update_dict(body)
        try:
            self.context.put()
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return
        return ActorSchema().to_json(self.context.model.to_dict())


    @view(permission='delete',
          response_schemas={
        '200': StatusResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def delete(self):
        "Delete an Actor"
        self.context.delete()
        return {'status': 'ok'}

    @view(permission='add',
          schema=ActorPostSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '201': ActorResponseSchema(description='Created'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new Actor"
        actor = Actor.from_dict(self.request.validated)
        try:
            self.context.put(actor)
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return

        self.request.response.status = 201
        return ActorSchema().to_json(actor.to_dict())


    @view(permission='view',
          schema=ActorListingRequestSchema(),
          validators=(colander_validator),
          response_schemas={
        '200': ActorListingResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        offset = self.request.validated['querystring']['offset']
        limit = self.request.validated['querystring']['limit']
        listing = self.context.search(
            offset=offset,
            limit=limit,
            principals=self.request.effective_principals)
        schema = ActorSchema()
        return {'total': listing['total'],
                'records': [schema.to_json(actor.to_dict())
                            for actor in listing['hits']],
                'limit': limit,
                'offset': offset}

