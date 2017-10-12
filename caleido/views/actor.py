import colander
from cornice.resource import resource, view
from cornice.validators import colander_body_validator, colander_validator

from caleido.models import Actor
from caleido.resources import ResourceFactory, ActorResource

from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema)

@colander.deferred
def deferred_actor_type_validator(node, kw):
    types = kw['repository'].type_config('actor_type')
    return colander.OneOf([t['key'] for t in types])

class ActorSchema(colander.MappingSchema):
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)
    type = colander.SchemaNode(colander.String(),
                               validator=deferred_actor_type_validator)
    name = colander.SchemaNode(colander.String())



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

def colander_actor_validator(request, schema=None, deserializer=None, **kwargs):
    if schema:
        schema = schema.bind(repository=request.repository)
    for method in kwargs.get('response_schemas', {}):
        kwargs['response_schemas'][method] = kwargs[
            'response_schemas'][method].bind(repository=request.repository)
    return colander_body_validator(request, schema=schema, **kwargs)

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
        return ActorSchema().serialize(self.context.model.to_dict())

    @view(permission='edit',
          schema=ActorSchema(),
          validators=(colander_actor_validator,),
          response_schemas={
        '200': ActorResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Modify an Actor"
        self.context.model.update_dict(self.request.validated)
        self.context.put()
        return ActorSchema().serialize(self.context.model.to_dict())


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
          schema=ActorSchema(),
          validators=(colander_actor_validator,),
          response_schemas={
        '201': ActorResponseSchema(description='Created'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new Actor"
        actor = Actor.from_dict(self.request.validated)
        self.context.put(actor)
        self.request.response.status = 201
        return ActorSchema().serialize(actor.to_dict())


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
        return {'total': listing['total'],
                'records': [actor.to_dict() for actor in listing['hits']],
                'limit': limit,
                'offset': offset}

