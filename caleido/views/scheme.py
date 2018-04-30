import colander
from cornice.resource import resource, view
from cornice.validators import colander_body_validator, colander_validator
from pyramid.httpexceptions import HTTPNotFound

from caleido.utils import ErrorResponseSchema
from caleido.resources import TypeResource

def type_factory(request):
    if not 'id' in request.matchdict:
        return TypeResource(request.dbsession, None)
    scheme_id = request.matchdict['id']
    if scheme_id not in TypeResource.schemes:
        raise HTTPNotFound()
    return TypeResource(request.dbsession, request.matchdict['id'])

class TypeSchema(colander.MappingSchema):
    id = colander.SchemaNode(colander.String(), missing=colander.drop)

    @colander.instantiate()
    class values(colander.SequenceSchema):
        @colander.instantiate()
        class value(colander.MappingSchema):
            key = colander.SchemaNode(colander.String())
            label = colander.SchemaNode(colander.String())

class TypeResponseSchema(colander.MappingSchema):
    body = TypeSchema()

class TypeListingSchema(colander.MappingSchema):
    @colander.instantiate()
    class types(colander.SequenceSchema):
        scheme = TypeSchema()

class TypeListingResponseSchema(colander.MappingSchema):
    body = TypeListingSchema()


@resource(name='Type',
          collection_path='/api/v1/schemes/types',
          path='/api/v1/schemes/types/{id}',
          tags=['config'],
          api_security=[{'jwt':[]}],
          factory=type_factory)
class TypeAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          response_schemas={
        '200': TypeResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a Type Scheme"
        return TypeSchema().serialize(self.context.to_dict())

    @view(permission='edit',
          schema=TypeSchema(),
          validators=(colander_body_validator,),
          response_schemas={
        '200': TypeResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Update a Type Scheme"
        self.context.from_dict(self.request.validated)
        return TypeSchema().serialize(self.context.to_dict())


    @view(permission='view',
          response_schemas={
        '200': TypeListingResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        listing = self.context.list()
        return TypeListingSchema().serialize(listing)



class SettingsSchema(colander.MappingSchema):
    title = colander.SchemaNode(colander.String())

class SettingsResponseSchema(colander.MappingSchema):
    body = SettingsSchema()


@resource(name='Settings',
          collection_path='/api/v1/schemes/settngs',
          path='/api/v1/schemes/settings',
          tags=['config'],
          api_security=[{'jwt':[]}],
          factory=type_factory)
class SettingsAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          response_schemas={
        '200': SettingsResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve Settings"
        return self.request.repository.settings

    @view(permission='edit',
          schema=SettingsSchema(),
          validators=(colander_body_validator,),
          response_schemas={
        '200': TypeResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Update Settings"
        settings = self.request.json
        self.request.repository.update_settings(settings)
        return self.request.repository.settings

