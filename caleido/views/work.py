from intervals import DateInterval

import colander
import sqlalchemy as sql
from sqlalchemy import func
from sqlalchemy.orm import Load

from cornice.resource import resource, view
from cornice.validators import colander_validator
from cornice import Service

from caleido.models import Work, Contributor, Affiliation, Person, Group
from caleido.resources import ResourceFactory, WorkResource, GroupResource

from caleido.exceptions import StorageError
from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema,
                           OKStatusResponseSchema,
                           OKStatus,
                           JsonMappingSchemaSerializerMixin,
                           colander_bound_repository_body_validator)

@colander.deferred
def deferred_work_type_validator(node, kw):
    types = kw['repository'].type_config('work_type')
    return colander.OneOf([t['key'] for t in types])

class WorkSchema(colander.MappingSchema, JsonMappingSchemaSerializerMixin):
    id = colander.SchemaNode(colander.Int())
    type = colander.SchemaNode(colander.String(),
                               validator=deferred_work_type_validator)
    title = colander.SchemaNode(colander.String())
    issued = colander.SchemaNode(colander.Date())
    start_date = colander.SchemaNode(colander.Date(), missing=None)
    end_date = colander.SchemaNode(colander.Date(), missing=None)

class WorkPostSchema(WorkSchema):
    # similar to group schema, but id is optional
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)

class WorkResponseSchema(colander.MappingSchema):
    body = WorkSchema()

class WorkListingResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        status = OKStatus
        total = colander.SchemaNode(colander.Int())
        offset = colander.SchemaNode(colander.Int())
        limit = colander.SchemaNode(colander.Int())

        @colander.instantiate()
        class records(colander.SequenceSchema):
            work = WorkSchema()

        @colander.instantiate()
        class snippets(colander.SequenceSchema):
            @colander.instantiate()
            class snippet(colander.MappingSchema):
                id = colander.SchemaNode(colander.Int())
                title = colander.SchemaNode(colander.String())
                type = colander.SchemaNode(colander.String())
                issued = colander.SchemaNode(colander.Date())

                @colander.instantiate()
                class contributors(colander.SequenceSchema):
                    @colander.instantiate()
                    class group(colander.MappingSchema):
                        id = colander.SchemaNode(colander.Int())
                        name = colander.SchemaNode(colander.String())

                @colander.instantiate()
                class affliations(colander.SequenceSchema):
                    @colander.instantiate()
                    class group(colander.MappingSchema):
                        id = colander.SchemaNode(colander.Int())
                        name = colander.SchemaNode(colander.String())

class WorkListingRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class querystring(colander.MappingSchema):
        query = colander.SchemaNode(colander.String(),
                                    missing=colander.drop)
        filter_type = colander.SchemaNode(colander.String(),
                                          missing=colander.drop)
        start_date = colander.SchemaNode(colander.Date(), missing=None)
        end_date = colander.SchemaNode(colander.Date(), missing=None)
        contributor_person_id = colander.SchemaNode(colander.Integer(),
                                                    missing=colander.drop)
        contributor_group_id = colander.SchemaNode(colander.Integer(),
                                                   missing=colander.drop)
        affiliation_group_id = colander.SchemaNode(colander.Integer(),
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

class WorkSearchRequestSchema(colander.MappingSchema):
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

class WorkBulkRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class records(colander.SequenceSchema):
        work = WorkSchema()

@resource(name='Work',
          collection_path='/api/v1/work/records',
          path='/api/v1/work/records/{id}',
          tags=['work'],
          cors_origins=('*', ),
          api_security=[{'jwt':[]}],
          factory=ResourceFactory(WorkResource))
class WorkRecordAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          response_schemas={
        '200': WorkResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a Work"
        return WorkSchema().to_json(self.context.model.to_dict())

    @view(permission='edit',
          schema=WorkSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '200': WorkResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Modify a Work"
        body = self.request.validated
        body['id'] = int(self.request.matchdict['id'])
        self.context.model.update_dict(body)
        try:
            self.context.put()
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return
        return WorkSchema().to_json(self.context.model.to_dict())


    @view(permission='delete',
          response_schemas={
        '200': StatusResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def delete(self):
        "Delete a Work"
        self.context.delete()
        return {'status': 'ok'}

    @view(permission='add',
          schema=WorkPostSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '201': WorkResponseSchema(description='Created'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new Work"
        work = Work.from_dict(self.request.validated)
        try:
            self.context.put(work)
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return

        self.request.response.status = 201
        return WorkSchema().to_json(work.to_dict())


    @view(permission='view',
          schema=WorkListingRequestSchema(),
          validators=(colander_validator),
          cors_origins=('*', ),
          response_schemas={
        '200': WorkListingResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        qs = self.request.validated['querystring']
        offset = qs['offset']
        limit = qs['limit']
        order_by = [func.lower(Work.during).desc()]
        format = qs.get('format')
        query = qs.get('query')
        filters = []
        if qs.get('start_date') or qs.get('end_date'):
            duration = DateInterval([qs.get('start_date'),
                                     qs.get('end_date')])
            filters.append(Work.during.op('&&')(duration))
        format = self.request.validated['querystring'].get('format')
        if format == 'record':
            format = None
        if query:
            filters.append(Work.title.ilike('%%%s%%' % query))
        filter_type = self.request.validated['querystring'].get('filter_type')
        if filter_type:
            filter_types = filter_type.split(',')
            filters.append(sql.or_(*[Work.type == f for f in filter_types]))

        from_query=None
        from_query_joined_tables=[]
        query_callback = None
        if format == 'snippet':
            from_query = self.context.session.query(Work)
            from_query = from_query.options(
                Load(Work).load_only('id',
                                      'type',
                                     'issued',
                                      'title'))
            if qs.get('contributor_person_id'):
                from_query = from_query.join(Contributor)
                filters.append(
                    Contributor.person_id == qs['contributor_person_id'])
                from_query_joined_tables.append(Contributor)
            if qs.get('contributor_group_id'):
                from_query = from_query.join(Contributor)
                filters.append(
                    Contributor.group_id == qs['contributor_group_id'])
                from_query_joined_tables.append(Contributor)
            if qs.get('affiliation_group_id'):
                from_query = from_query.join(Affiliation)
                group_id = qs['affiliation_group_id']
                group_ids = [group_id]
                group_ids.extend(ResourceFactory(GroupResource)(
                    self.request, group_id).child_groups())
                filters.append(
                    sql.or_(*[Affiliation.group_id == g for g in group_ids]))
                from_query_joined_tables.append(Affiliation)


            def query_callback(from_query):
                filtered_works = from_query.cte('filtered_works')
                with_contributors = self.context.session.query(
                    filtered_works.c.id.label('id'),
                    filtered_works.c.title.label('title'),
                    filtered_works.c.issued.label('issued'),
                    filtered_works.c.type.label('type'),
                    func.array_agg(sql.distinct(func.concat(Person.id,
                                                            ':',
                                                            Person.name))
                                   ).label('contributors'),
                    ).join(Contributor).join(Person).group_by(filtered_works)
                filtered_contributors = with_contributors.cte('contributors')
                with_aff_groups = self.context.session.query(
                    filtered_contributors,
                    func.array_agg(sql.distinct(func.concat(Group.id,
                                                            ':',
                                                            Group.name))
                                   ).label('affiliations'),
                    ).outerjoin(Affiliation).join(Group).group_by(filtered_contributors)
                return with_aff_groups
        listing = self.context.search(
            filters=filters,
            offset=offset,
            limit=limit,
            order_by=order_by,
            format=format,
            from_query=from_query,
            from_query_joined_tables=from_query_joined_tables,
            post_query_callback=query_callback,
            principals=self.request.effective_principals)
        schema = WorkSchema()
        result = {'total': listing['total'],
                  'records': [],
                  'snippets': [],
                  'limit': limit,
                  'offset': offset,
                  'status': 'ok'}

        if format == 'snippet':
            snippets = []
            for hit in listing['hits']:
                contributors = []
                for contributor in hit.contributors:
                    id, name = contributor.split(':', 1)
                    contributors.append(dict(id=id, name=name))
                affiliations = []
                for affiliation in hit.affiliations:
                    id, name = affiliation.split(':', 1)
                    affiliations.append(dict(id=id, name=name))
                snippets.append({'id': hit.id,
                                 'title': hit.title,
                                 'type': hit.type,
                                 'issued': hit.issued.strftime('%Y-%m-%d'),
                                 'affiliations': affiliations,
                                 'contributors': contributors})
            result['snippets'] = snippets
        else:
            result['records'] = [schema.to_json(work.to_dict())
                                 for work in listing['hits']]

        return result

work_bulk = Service(name='WorkBulk',
                     path='/api/v1/work/bulk',
                     factory=ResourceFactory(WorkResource),
                     api_security=[{'jwt':[]}],
                     tags=['work'],
                     cors_origins=('*', ),
                     schema=WorkBulkRequestSchema(),
                     validators=(colander_bound_repository_body_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@work_bulk.post(permission='import')
def work_bulk_import_view(request):
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

work_search = Service(name='WorkSearch',
                     path='/api/v1/work/search',
                     factory=ResourceFactory(WorkResource),
                     api_security=[{'jwt':[]}],
                     tags=['work'],
                     cors_origins=('*', ),
                     schema=WorkSearchRequestSchema(),
                     validators=(colander_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@work_search.get(permission='search')
def group_search_view(request):
    offset = request.validated['querystring']['offset']
    limit = request.validated['querystring']['limit']
    order_by = [Work.title.asc()]
    query = request.validated['querystring'].get('query')
    filters = []
    if query:
        filters.append(Work.title.ilike('%%%s%%' % query))
    from_query = request.context.session.query(Work)
    from_query = from_query.options(
        Load(Work).load_only('id', 'title'))

    # allow search listing with editor principals
    listing = request.context.search(
        filters=filters,
        offset=offset,
        limit=limit,
        order_by=order_by,
        format=format,
        from_query=from_query,
        principals=['group:editor'])
    snippets = []
    for hit in listing['hits']:
        snippets.append({'id': hit.id,
                         'title': hit.title})
    return {'total': listing['total'],
            'snippets': snippets,
            'limit': limit,
            'offset': offset,
            'status': 'ok'}

