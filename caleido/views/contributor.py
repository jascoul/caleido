import datetime

from intervals import DateInterval
import colander
import sqlalchemy as sql
from sqlalchemy import func
from cornice.resource import resource, view
from cornice.validators import colander_validator
from cornice import Service

from caleido.models import Contributor, Person, Group
from caleido.resources import ResourceFactory, ContributorResource, GroupResource

from caleido.exceptions import StorageError
from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema,
                           OKStatusResponseSchema,
                           OKStatus,
                           JsonMappingSchemaSerializerMixin,
                           colander_bound_repository_body_validator,
                           )
@colander.deferred
def deferred_contributor_role_validator(node, kw):
    types = kw['repository'].type_config('contributor_role')
    return colander.OneOf([t['key'] for t in types])

def contributor_validator(node, kw):
    if not kw.get('group_id') and not kw.get('person_id'):
        node.name = '%s.person_id' % node.name
        raise colander.Invalid(
            node, "Required: supply either 'person_id' or 'group_id'")


class ContributorSchema(colander.MappingSchema,
                        JsonMappingSchemaSerializerMixin):
    def __init__(self, *args, **kwargs):
        kwargs['validator'] = contributor_validator
        super(ContributorSchema, self).__init__(*args, **kwargs)

    id = colander.SchemaNode(colander.Int())
    role = colander.SchemaNode(colander.String(),
                               validator=deferred_contributor_role_validator)

    person_id = colander.SchemaNode(colander.Int(), missing=None)
    _person_name = colander.SchemaNode(colander.String(),
                                       missing=colander.drop)
    group_id = colander.SchemaNode(colander.Int(), missing=None)
    _group_name = colander.SchemaNode(colander.String(),
                                      missing=colander.drop)
    work_id = colander.SchemaNode(colander.Int())
    _work_name = colander.SchemaNode(colander.String(),
                                     missing=colander.drop)
    start_date = colander.SchemaNode(colander.Date(),
                                     missing=colander.drop)
    end_date = colander.SchemaNode(colander.Date(),
                                   missing=colander.drop)
    location = colander.SchemaNode(colander.String(), missing=None)
    position = colander.SchemaNode(colander.Int())


    @colander.instantiate(missing=colander.drop)
    class affiliations(colander.SequenceSchema):
        @colander.instantiate()
        class affiliation(colander.MappingSchema):
            id = colander.SchemaNode(colander.Int())
            group_id = colander.SchemaNode(colander.Int())
            _group_name = colander.SchemaNode(colander.String(),
                                      missing=colander.drop)
            position = colander.SchemaNode(colander.Int())


class ContributorPostSchema(ContributorSchema):
    # similar to contributor schema, but id is optional
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)

class ContributorResponseSchema(colander.MappingSchema):
    body = ContributorSchema()

class ContributorListingResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        status = OKStatus
        total = colander.SchemaNode(colander.Int())
        offset = colander.SchemaNode(colander.Int())
        limit = colander.SchemaNode(colander.Int())

        @colander.instantiate()
        class records(colander.SequenceSchema):
            contributor = ContributorSchema()

        @colander.instantiate()
        class snippets(colander.SequenceSchema):
            @colander.instantiate()
            class snippet(colander.MappingSchema):
                person_id = colander.SchemaNode(colander.Int())
                role = colander.SchemaNode(colander.String())
                person_name = colander.SchemaNode(colander.String())
                group_id = colander.SchemaNode(colander.Int())
                group_name = colander.SchemaNode(colander.String())
                work_id = colander.SchemaNode(colander.Int())
                work_name = colander.SchemaNode(colander.String())

class ContributorListingRequestSchema(colander.MappingSchema):
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
        person_id = colander.SchemaNode(colander.Int(),
                                        missing=colander.drop)
        group_id = colander.SchemaNode(colander.Int(),
                                       missing=colander.drop)
        work_id = colander.SchemaNode(colander.Int(),
                                      missing=colander.drop)
        format = colander.SchemaNode(
            colander.String(),
            validator=colander.OneOf(['record', 'snippet']),
            missing=colander.drop)

class ContributorBulkRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class records(colander.SequenceSchema):
        contributor = ContributorSchema()

@resource(name='Contributor',
          collection_path='/api/v1/contributor/records',
          path='/api/v1/contributor/records/{id}',
          tags=['contributor'],
          cors_origins=('*', ),
          api_security=[{'jwt':[]}],
          factory=ResourceFactory(ContributorResource))
class ContributorRecordAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          response_schemas={
        '200': ContributorResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a Contributor"
        return ContributorSchema().to_json(self.context.model.to_dict())

    @view(permission='edit',
          schema=ContributorSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '200': ContributorResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Modify a Contributor"
        body = self.request.validated
        body['id'] = int(self.request.matchdict['id'])
        self.context.model.update_dict(body)
        try:
            self.context.put()
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return
        return ContributorSchema().to_json(self.context.model.to_dict())


    @view(permission='delete',
          response_schemas={
        '200': StatusResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def delete(self):
        "Delete a Contributor"
        self.context.delete()
        return {'status': 'ok'}

    @view(permission='add',
          schema=ContributorPostSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '201': ContributorResponseSchema(description='Created'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new Contributor"
        contributor = Contributor.from_dict(self.request.validated)
        try:
            self.context.put(contributor)
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return

        self.request.response.status = 201
        return ContributorSchema().to_json(contributor.to_dict())


    @view(permission='view',
          schema=ContributorListingRequestSchema(),
          validators=(colander_validator),
          cors_origins=('*', ),
          response_schemas={
        '200': ContributorListingResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        qs = self.request.validated['querystring']
        offset = qs['offset']
        limit = qs['limit']
        person_id = qs.get('person_id')
        group_id = qs.get('group_id')
        work_id = qs.get('group_id')
        format = qs.get('format')
        order_by = []
        query = qs.get('query')
        filters = []
        if person_id:
            filters.append(Contributor.person_id == person_id)
        if work_id:
            filters.append(Contributor.work_id == work_id)
        if group_id:
            if qs['transitive']:
                # find
                group_ids = [group_id]
                group_ids.extend(ResourceFactory(GroupResource)(
                    self.request, group_id).child_groups())
                filters.append(
                    sql.or_(*[Contributor.group_id == g for g in group_ids]))
            else:
                filters.append(Contributor.group_id == group_id)


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
        schema = ContributorSchema()
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
                                 'person_id': hit.person_id,
                                 'person_name': hit.person_name,
                                 'group_id': hit.group_id,
                                 'group_name': hit.group_name,
                                 'work_id': hit.work_id,
                                 'work_name': hit.work_name})
            result['snippets'] = snippets
        else:
            result['records'] = [schema.to_json(contributor.to_dict())
                                 for contributor in listing['hits']]

        return result



contributor_bulk = Service(name='ContributorBulk',
                     path='/api/v1/contributor/bulk',
                     factory=ResourceFactory(ContributorResource),
                     api_security=[{'jwt':[]}],
                     tags=['contributor'],
                     cors_origins=('*', ),
                     schema=ContributorBulkRequestSchema(),
                     validators=(colander_bound_repository_body_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@contributor_bulk.post(permission='import')
def contributor_bulk_import_view(request):
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
