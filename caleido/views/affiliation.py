import datetime

from intervals import DateInterval
import colander
import sqlalchemy as sql
from sqlalchemy import func
from cornice.resource import resource, view
from cornice.validators import colander_validator
from cornice import Service

from caleido.models import Affiliation, Contributor, Group
from caleido.resources import ResourceFactory, AffiliationResource, GroupResource

from caleido.exceptions import StorageError
from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema,
                           OKStatusResponseSchema,
                           OKStatus,
                           JsonMappingSchemaSerializerMixin,
                           colander_bound_repository_body_validator,
                           )


class AffiliationSchema(colander.MappingSchema,
                        JsonMappingSchemaSerializerMixin):

    id = colander.SchemaNode(colander.Int())

    contributor_id = colander.SchemaNode(colander.Int())
    group_id = colander.SchemaNode(colander.Int())
    _group_name = colander.SchemaNode(colander.String(),
                                      missing=colander.drop)
    work_id = colander.SchemaNode(colander.Int())
    _work_name = colander.SchemaNode(colander.String(),
                                     missing=colander.drop)
    position = colander.SchemaNode(colander.Int())


class AffiliationPostSchema(AffiliationSchema):
    # similar to affiliation schema, but id is optional
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)

class AffiliationResponseSchema(colander.MappingSchema):
    body = AffiliationSchema()

class AffiliationListingResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        status = OKStatus
        total = colander.SchemaNode(colander.Int())
        offset = colander.SchemaNode(colander.Int())
        limit = colander.SchemaNode(colander.Int())

        @colander.instantiate()
        class records(colander.SequenceSchema):
            affiliation = AffiliationSchema()

        @colander.instantiate()
        class snippets(colander.SequenceSchema):
            @colander.instantiate()
            class snippet(colander.MappingSchema):
                contributor_id = colander.SchemaNode(colander.Int())
                group_id = colander.SchemaNode(colander.Int())
                group_name = colander.SchemaNode(colander.String())
                work_id = colander.SchemaNode(colander.Int())
                work_name = colander.SchemaNode(colander.String())

class AffiliationListingRequestSchema(colander.MappingSchema):
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
        query = colander.SchemaNode(colander.String(),
                                    missing=colander.drop)
        contributor_id = colander.SchemaNode(colander.Int(),
                                             missing=colander.drop)
        group_id = colander.SchemaNode(colander.Int(),
                                       missing=colander.drop)
        work_id = colander.SchemaNode(colander.Int(),
                                      missing=colander.drop)
        format = colander.SchemaNode(
            colander.String(),
            validator=colander.OneOf(['record', 'snippet']),
            missing=colander.drop)

class AffiliationBulkRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class records(colander.SequenceSchema):
        affiliation = AffiliationSchema()

@resource(name='Affiliation',
          collection_path='/api/v1/affiliation/records',
          path='/api/v1/affiliation/records/{id}',
          tags=['affiliation'],
          cors_origins=('*', ),
          api_security=[{'jwt':[]}],
          factory=ResourceFactory(AffiliationResource))
class AffiliationRecordAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          response_schemas={
        '200': AffiliationResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve an Affiliation"
        return AffiliationSchema().to_json(self.context.model.to_dict())

    @view(permission='edit',
          schema=AffiliationSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '200': AffiliationResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Modify an affiliation"
        body = self.request.validated
        body['id'] = int(self.request.matchdict['id'])
        self.context.model.update_dict(body)
        try:
            self.context.put()
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return
        return AffiliationSchema().to_json(self.context.model.to_dict())


    @view(permission='delete',
          response_schemas={
        '200': StatusResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def delete(self):
        "Delete an Affiliation"
        self.context.delete()
        return {'status': 'ok'}

    @view(permission='add',
          schema=AffiliationPostSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '201': AffiliationResponseSchema(description='Created'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new Affiliation"
        affiliation = Affiliation.from_dict(self.request.validated)
        try:
            self.context.put(affiliation)
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return
        self.request.response.status = 201
        return AffiliationSchema().to_json(affiliation.to_dict())

    @view(permission='view',
          schema=AffiliationListingRequestSchema(),
          validators=(colander_validator),
          cors_origins=('*', ),
          response_schemas={
        '200': AffiliationListingResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        qs = self.request.validated['querystring']
        offset = qs['offset']
        limit = qs['limit']
        group_id = qs.get('group_id')
        work_id = qs.get('group_id')
        format = qs.get('format')
        order_by = []
        filters = []
        if work_id:
            filters.append(Affiliation.work_id == work_id)
        if group_id:
            if qs['transitive']:
                # find
                group_ids = [group_id]
                group_ids.extend(ResourceFactory(GroupResource)(
                    self.request, group_id).child_groups())
                filters.append(
                    sql.or_(*[Affiliation.group_id == g for g in group_ids]))
            else:
                filters.append(Affiliation.group_id == group_id)


        cte_total = None
        from_query=None
        query_callback = None
        if format == 'record':
            format = None
        elif format == 'snippet':
            from_query = self.context.session.query(Contributor)

        listing = self.context.search(
            from_query=from_query,
            filters=filters,
            offset=offset,
            limit=limit,
            order_by=order_by,
            post_query_callback=query_callback,
            apply_limits_post_query={'snippet': True}.get(format, False),
            principals=self.request.effective_principals)
        schema = AffiliationSchema()
        result = {'total': listing['total'] or cte_total,
                  'records': [],
                  'snippets': [],
                  'limit': limit,
                  'status': 'ok',
                  'offset': offset}

        if format == 'snippet':
            snippets = []
            for hit in listing['hits']:
                snippets.append({'id': hit.id,
                                 'contributor_id': hit.contributor_id,
                                 'group_id': hit.group_id,
                                 'group_name': hit.group_name,
                                 'work_id': hit.work_id,
                                 'work_name': hit.work_name})
            result['snippets'] = snippets
        else:
            result['records'] = [schema.to_json(affiliation.to_dict())
                                 for affiliation in listing['hits']]

        return result

affiliation_bulk = Service(name='AffiliationBulk',
                     path='/api/v1/affiliation/bulk',
                     factory=ResourceFactory(AffiliationResource),
                     api_security=[{'jwt':[]}],
                     tags=['affiliation'],
                     cors_origins=('*', ),
                     schema=AffiliationBulkRequestSchema(),
                     validators=(colander_bound_repository_body_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@affiliation_bulk.post(permission='import')
def affiliation_bulk_import_view(request):
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
