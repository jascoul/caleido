import colander
from cornice.resource import resource, view
from cornice.validators import colander_validator
from cornice import Service

from caleido.models import Membership
from caleido.resources import ResourceFactory, MembershipResource

from caleido.exceptions import StorageError
from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema,
                           OKStatusResponseSchema,
                           JsonMappingSchemaSerializerMixin,
                           colander_bound_repository_body_validator)

class MembershipSchema(colander.MappingSchema, JsonMappingSchemaSerializerMixin):
    id = colander.SchemaNode(colander.Int())
    person_id = colander.SchemaNode(colander.Int())
    group_id = colander.SchemaNode(colander.Int())
    start_date = colander.SchemaNode(colander.Date(),
                                     missing=colander.drop)
    end_date = colander.SchemaNode(colander.Date(),
                                   missing=colander.drop)

class MembershipPostSchema(MembershipSchema):
    # similar to membership schema, but id is optional
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)

class MembershipResponseSchema(colander.MappingSchema):
    body = MembershipSchema()

class MembershipListingResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        @colander.instantiate()
        class records(colander.SequenceSchema):
            membership = MembershipSchema()
        total = colander.SchemaNode(colander.Int())
        offset = colander.SchemaNode(colander.Int())
        limit = colander.SchemaNode(colander.Int())

class MembershipListingRequestSchema(colander.MappingSchema):
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

class MembershipBulkRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class records(colander.SequenceSchema):
        membership = MembershipSchema()

@resource(name='Membership',
          collection_path='/api/v1/membership/records',
          path='/api/v1/membership/records/{id}',
          tags=['membership'],
          api_security=[{'jwt':[]}],
          factory=ResourceFactory(MembershipResource))
class MembershipRecordAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          response_schemas={
        '200': MembershipResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a Membership"
        return MembershipSchema().to_json(self.context.model.to_dict())

    @view(permission='edit',
          schema=MembershipSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '200': MembershipResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Modify a Membership"
        body = self.request.validated
        body['id'] = int(self.request.matchdict['id'])
        self.context.model.update_dict(body)
        try:
            self.context.put()
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return
        return MembershipSchema().to_json(self.context.model.to_dict())


    @view(permission='delete',
          response_schemas={
        '200': StatusResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def delete(self):
        "Delete an Membership"
        self.context.delete()
        return {'status': 'ok'}

    @view(permission='add',
          schema=MembershipPostSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '201': MembershipResponseSchema(description='Created'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new Membership"
        membership = Membership.from_dict(self.request.validated)
        try:
            self.context.put(membership)
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return

        self.request.response.status = 201
        return MembershipSchema().to_json(membership.to_dict())


    @view(permission='view',
          schema=MembershipListingRequestSchema(),
          validators=(colander_validator),
          cors_origins=('*', ),
          response_schemas={
        '200': MembershipListingResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        offset = self.request.validated['querystring']['offset']
        limit = self.request.validated['querystring']['limit']
        order_by = [Membership.name.asc()]
        listing = self.context.search(
            offset=offset,
            limit=limit,
            order_by=order_by,
            principals=self.request.effective_principals)
        schema = MembershipSchema()
        return {'total': listing['total'],
                'records': [schema.to_json(membership.to_dict())
                            for membership in listing['hits']],
                'limit': limit,
                'offset': offset}

membership_bulk = Service(name='MembershipBulk',
                     path='/api/v1/membership/bulk',
                     factory=ResourceFactory(MembershipResource),
                     api_security=[{'jwt':[]}],
                     tags=['membership'],
                     cors_origins=('*', ),
                     schema=MembershipBulkRequestSchema(),
                     validators=(colander_bound_repository_body_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@membership_bulk.post(permission='import')
def membership_bulk_import_view(request):
    # get existing resources from submitted bulk
    keys = [r['id'] for r in request.validated['records'] if r.get('id')]
    existing_records = {r.id:r for r in request.context.get_many(keys) if r}
    models = []
    for record in request.validated['records']:
        if record['id'] in existing_records:
            model = existing_records[record['id']]
            model.update_dict(record)
        else:
            model = request.context.orm_class.from_dict(record)
        models.append(model)
    models = request.context.put_many(models)
    request.response.status = 201
    return {'status': 'ok'}
