from intervals import DateInterval
import datetime

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

@colander.deferred
def deferred_identifier_type_validator(node, kw):
    types = kw['repository'].type_config('identifier_type')
    return colander.OneOf([t['key'] for t in types])

@colander.deferred
def deferred_contributor_role_validator(node, kw):
    types = kw['repository'].type_config('contributor_role')
    return colander.OneOf([t['key'] for t in types])

@colander.deferred
def deferred_relation_type_validator(node, kw):
    types = kw['repository'].type_config('relation_type')
    return colander.OneOf([t['key'] for t in types])

@colander.deferred
def deferred_description_type_validator(node, kw):
    types = kw['repository'].type_config('description_type')
    return colander.OneOf([t['key'] for t in types])

@colander.deferred
def deferred_description_format_validator(node, kw):
    types = kw['repository'].type_config('description_format')
    return colander.OneOf([t['key'] for t in types])

@colander.deferred
def deferred_measure_type_validator(node, kw):
    types = kw['repository'].type_config('measure_type')
    return colander.OneOf([t['key'] for t in types])

class WorkSchema(colander.MappingSchema, JsonMappingSchemaSerializerMixin):
    id = colander.SchemaNode(colander.Int())
    type = colander.SchemaNode(colander.String(),
                               validator=deferred_work_type_validator)
    title = colander.SchemaNode(colander.String())
    issued = colander.SchemaNode(colander.Date())
    start_date = colander.SchemaNode(colander.Date(), missing=None)
    end_date = colander.SchemaNode(colander.Date(), missing=None)

    @colander.instantiate(missing=colander.drop)
    class identifiers(colander.SequenceSchema):
        @colander.instantiate()
        class identifier(colander.MappingSchema):
            type = colander.SchemaNode(
                colander.String(),
                validator=deferred_identifier_type_validator)
            value = colander.SchemaNode(colander.String())

    @colander.instantiate(missing=colander.drop)
    class measures(colander.SequenceSchema):
        @colander.instantiate()
        class measure(colander.MappingSchema):
            type = colander.SchemaNode(
                colander.String(),
                validator=deferred_measure_type_validator)
            value = colander.SchemaNode(colander.String())

    @colander.instantiate(missing=colander.drop)
    class descriptions(colander.SequenceSchema):
        @colander.instantiate()
        class description(colander.MappingSchema):
            type = colander.SchemaNode(
                colander.String(),
                validator=deferred_description_type_validator)
            format = colander.SchemaNode(
                colander.String(),
                missing='text',
                validator=deferred_description_format_validator)
            value = colander.SchemaNode(colander.String(), missing=None)
            position = colander.SchemaNode(colander.Integer(),
                                           missing=colander.drop)
            id = colander.SchemaNode(colander.Integer(), missing=colander.drop)
            target_id = colander.SchemaNode(colander.Integer(), missing=None)
            _target_name = colander.SchemaNode(colander.String(),
                                               missing=colander.drop)



    @colander.instantiate(missing=colander.drop)
    class relations(colander.SequenceSchema):
        @colander.instantiate()
        class relation(colander.MappingSchema):
            type = colander.SchemaNode(
                colander.String(),
                validator=deferred_relation_type_validator)
            position = colander.SchemaNode(colander.Integer(),
                                           missing=colander.drop)
            id = colander.SchemaNode(colander.Integer(), missing=colander.drop)
            target_id = colander.SchemaNode(colander.Integer())
            _target_name = colander.SchemaNode(colander.String(),
                                               missing=colander.drop)
            _target_type = colander.SchemaNode(colander.String(),
                                               missing=colander.drop)
            start_date = colander.SchemaNode(colander.Date(), missing=None)
            end_date = colander.SchemaNode(colander.Date(), missing=None)
            starting = colander.SchemaNode(colander.String(), missing=None)
            ending = colander.SchemaNode(colander.String(), missing=None)
            total = colander.SchemaNode(colander.String(), missing=None)
            volume = colander.SchemaNode(colander.String(), missing=None)
            issue = colander.SchemaNode(colander.String(), missing=None)
            description = colander.SchemaNode(colander.String(), missing=None)
            location = colander.SchemaNode(colander.String(), missing=None)
            number = colander.SchemaNode(colander.String(), missing=None)


    @colander.instantiate(missing=colander.drop)
    class contributors(colander.SequenceSchema):
        @colander.instantiate()
        class contributor(colander.MappingSchema):
            role = colander.SchemaNode(
                colander.String(),
                validator=deferred_contributor_role_validator)
            position = colander.SchemaNode(colander.Integer(),
                                           missing=colander.drop)
            id = colander.SchemaNode(colander.Integer(), missing=colander.drop)
            person_id = colander.SchemaNode(colander.Integer())
            _person_name = colander.SchemaNode(colander.String(),
                                               missing=colander.drop)
            start_date = colander.SchemaNode(colander.Date(), missing=None)
            end_date = colander.SchemaNode(colander.Date(), missing=None)
            description = colander.SchemaNode(colander.String(), missing=None)
            location = colander.SchemaNode(colander.String(), missing=None)

            @colander.instantiate(missing=colander.drop)
            class affiliations(colander.SequenceSchema):
                @colander.instantiate()
                class affiliation(colander.MappingSchema):
                    id = colander.SchemaNode(colander.Int(),
                                             missing=colander.drop)
                    group_id = colander.SchemaNode(colander.Int())
                    _group_name = colander.SchemaNode(colander.String(),
                                              missing=colander.drop)
                    position = colander.SchemaNode(colander.Int(),
                                                   missing=colander.drop)



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
        related_work_id = colander.SchemaNode(colander.Integer(),
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
            validator=colander.OneOf(['snippet', 'csl']),
            missing=colander.drop)

class WorkSearchRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class querystring(colander.MappingSchema):
        query = colander.SchemaNode(colander.String(),
                                    missing=colander.drop)
        type = colander.SchemaNode(colander.String(),
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
        if query:
            filters.append(Work.search_terms.match(query))
        filter_type = self.request.validated['querystring'].get('filter_type')
        if filter_type:
            filter_types = filter_type.split(',')
            filters.append(sql.or_(*[Work.type == f for f in filter_types]))

        from_query=None
        listing = self.context.search(
            filters=filters,
            offset=offset,
            limit=limit,
            order_by=order_by,
            format=format,
            from_query=from_query,
            principals=self.request.effective_principals)
        schema = WorkSchema()
        result = {'total': listing['total'],
                  'records': [schema.to_json(work.to_dict())
                              for work in listing['hits']],
                  'snippets': [],
                  'limit': limit,
                  'offset': offset,
                  'status': 'ok'}
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

work_listing = Service(name='WorkListing',
                     path='/api/v1/work/listing',
                     factory=ResourceFactory(WorkResource),
                     api_security=[{'jwt':[]}],
                     tags=['work'],
                     cors_origins=('*', ),
                     schema=WorkListingRequestSchema(),
                     validators=(colander_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@work_listing.get(permission='view')
def work_listing_view(request):
    qs = request.validated['querystring']
    params = dict(offset = qs['offset'],
                  limit = qs['limit'],
                  text_query = qs.get('query'),
                  order_by = qs.get('order_by'),
                  start_date = qs.get('start_date'),
                  end_date = qs.get('end_date'),
                  type = qs.get('filter_type'),
                  principals=request.effective_principals)
    if qs.get('contributor_person_id'):
        params['contributor_person_ids'] = [qs['contributor_person_id']]
    if qs.get('contributor_group_id'):
        params['contributor_group_ids'] = [qs['contributor_group_id']]
    if qs.get('affiliation_group_id'):
        params['affiliation_group_ids'] = [qs['affiliation_group_id']]
        params['affiliation_group_ids'].extend(ResourceFactory(GroupResource)(
            request, qs['affiliation_group_id']).child_groups())
    if qs.get('related_work_id'):
        params['related_work_ids'] = [qs['related_work_id']]

    result = request.context.listing(**params)

    def csl_convert(item):
        issued = datetime.datetime.strptime(item['issued'], '%Y-%m-%d')
        date_parts = [issued.year]
        if not (issued.month == 1 and issued.day == 1):
            date_parts.append(issued.month)
            if issued.day != 1:
                date_parts.append(issued.day)

        authors = []
        editors = []
        for c in item['contributors']:
            contributor = {
                'given': c.get('given_name') or c.get('initials'),
                'family': c.get('family_name'),
                'initials': c.get('initials'),
                'non-dropping-particle': c.get('prefix')}
            if c['role'] == 'editor':
                editors.append(contributor)
            else:
                authors.append(contributor)
        type = 'entry'
        if 'chapter' in item['type'].lower():
            type = 'chapter'
        elif 'book' in item['type'].lower():
            type = 'book'
        elif 'article' in item['type'].lower():
            type = 'article-journal'
        elif 'paper' in item['type'].lower() or 'report' in item['type'].lower():
            type = 'report'

        journal = {}
        for rel in item.get('relations', []):
            if rel['relation_type'] == 'isPartOf' and rel['type'] == 'journal':
                journal['container-title'] = rel['title']
                if rel['issue']:
                    journal['issue'] = rel['issue']
                if rel['volume']:
                    journal['volume'] = rel['volume']
                if rel['starting'] and rel['ending']:
                    journal['page'] = '%s-%s' % (rel['starting'],
                                                 rel['ending'])
                break

        result = {'title': item['title'],
                  'id': str(item['id']),
                  'type': type,
                  'issued': {"date-parts": [date_parts]},
                  'author': authors,
                  'editor': editors}
        result.update(journal)
        return result

    if qs.get('format') == 'csl':
        result['hits'] = [csl_convert(h) for h in result['hits']]
    else:
        for hit in result['hits']:
            hit['csl'] = csl_convert(hit)

    result['snippets'] = result.pop('hits')
    result['status'] = 'ok'
    return result

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
def work_search_view(request):
    offset = request.validated['querystring']['offset']
    limit = request.validated['querystring']['limit']
    order_by = [Work.title.asc()]
    query = request.validated['querystring'].get('query')
    type = request.validated['querystring'].get('type')
    filters = []
    if query:
        filters.append(Work.search_terms.match(query))
    if type:
        filters.append(Work.type == type)
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
                         'info': hit.type,
                         'name': hit.title})
    return {'total': listing['total'],
            'snippets': snippets,
            'limit': limit,
            'offset': offset,
            'status': 'ok'}

