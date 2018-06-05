import colander
import sqlalchemy as sql
from sqlalchemy import func
from sqlalchemy.orm import Load

from cornice.resource import resource, view
from cornice.validators import colander_validator
from cornice import Service

from caleido.models import Group, Membership, Affiliation
from caleido.resources import ResourceFactory, GroupResource

from caleido.exceptions import StorageError
from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema,
                           OKStatusResponseSchema,
                           OKStatus,
                           JsonMappingSchemaSerializerMixin,
                           colander_bound_repository_body_validator)

@colander.deferred
def deferred_group_type_validator(node, kw):
    types = kw['repository'].type_config('group_type')
    return colander.OneOf([t['key'] for t in types])

@colander.deferred
def deferred_account_type_validator(node, kw):
    types = kw['repository'].type_config('group_account_type')
    return colander.OneOf([t['key'] for t in types])

class GroupSchema(colander.MappingSchema, JsonMappingSchemaSerializerMixin):
    id = colander.SchemaNode(colander.Int())
    type = colander.SchemaNode(colander.String(),
                               validator=deferred_group_type_validator)
    name = colander.SchemaNode(colander.String(),
                                missing=colander.drop)
    international_name = colander.SchemaNode(colander.String())
    native_name = colander.SchemaNode(colander.String(),
                                      missing=colander.drop)
    abbreviated_name = colander.SchemaNode(colander.String(),
                                           missing=colander.drop)
    location = colander.SchemaNode(colander.String(),
                                   missing=colander.drop)
    start_date = colander.SchemaNode(colander.Date(),
                                     missing=colander.drop)
    end_date = colander.SchemaNode(colander.Date(),
                                   missing=colander.drop)
    parent_id = colander.SchemaNode(colander.Int(), missing=colander.drop)
    _parent_name = colander.SchemaNode(colander.String(),
                                       missing=colander.drop)

    @colander.instantiate(missing=colander.drop)
    class accounts(colander.SequenceSchema):
        @colander.instantiate()
        class account(colander.MappingSchema):
            type = colander.SchemaNode(colander.String(),
                                       validator=deferred_account_type_validator)
            value = colander.SchemaNode(colander.String())

class GroupPostSchema(GroupSchema):
    # similar to group schema, but id is optional
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)

class GroupResponseSchema(colander.MappingSchema):
    body = GroupSchema()

class GroupListingResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        status = OKStatus
        total = colander.SchemaNode(colander.Int())
        offset = colander.SchemaNode(colander.Int())
        limit = colander.SchemaNode(colander.Int())

        @colander.instantiate()
        class records(colander.SequenceSchema):
            group = GroupSchema()

        @colander.instantiate()
        class snippets(colander.SequenceSchema):
            @colander.instantiate()
            class snippet(colander.MappingSchema):
                id = colander.SchemaNode(colander.Int())
                name = colander.SchemaNode(colander.String())
                type = colander.SchemaNode(colander.String())
                members = colander.SchemaNode(colander.Int())
                works = colander.SchemaNode(colander.Int())

class GroupListingRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class querystring(colander.MappingSchema):
        query = colander.SchemaNode(colander.String(),
                                    missing=colander.drop)
        filter_type = colander.SchemaNode(colander.String(),
                                          missing=colander.drop)
        filter_parent = colander.SchemaNode(colander.Int(),
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

class GroupSearchRequestSchema(colander.MappingSchema):
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

class GroupBulkRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class records(colander.SequenceSchema):
        group = GroupSchema()

@resource(name='Group',
          collection_path='/api/v1/group/records',
          path='/api/v1/group/records/{id}',
          tags=['group'],
          cors_origins=('*', ),
          api_security=[{'jwt':[]}],
          factory=ResourceFactory(GroupResource))
class GroupRecordAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          response_schemas={
        '200': GroupResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a Group"
        return GroupSchema().to_json(self.context.model.to_dict())

    @view(permission='edit',
          schema=GroupSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '200': GroupResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Modify an Group"
        body = self.request.validated
        body['id'] = int(self.request.matchdict['id'])
        self.context.model.update_dict(body)
        try:
            self.context.put()
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return
        return GroupSchema().to_json(self.context.model.to_dict())


    @view(permission='delete',
          response_schemas={
        '200': StatusResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def delete(self):
        "Delete an Group"
        self.context.delete()
        return {'status': 'ok'}

    @view(permission='add',
          schema=GroupPostSchema(),
          validators=(colander_bound_repository_body_validator,),
          response_schemas={
        '201': GroupResponseSchema(description='Created'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new Group"
        group = Group.from_dict(self.request.validated)
        try:
            self.context.put(group)
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return
        self.request.response.status = 201
        return GroupSchema().to_json(group.to_dict())


    @view(permission='view',
          schema=GroupListingRequestSchema(),
          validators=(colander_validator),
          cors_origins=('*', ),
          response_schemas={
        '200': GroupListingResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        offset = self.request.validated['querystring']['offset']
        limit = self.request.validated['querystring']['limit']
        order_by = [Group.name.asc()]
        format = self.request.validated['querystring'].get('format')
        if format == 'record':
            format = None
        query = self.request.validated['querystring'].get('query')
        filters = []
        if query:
            filters.append(Group.name.ilike('%%%s%%' % query))
        filter_type = self.request.validated['querystring'].get('filter_type')
        if filter_type:
            filter_types = filter_type.split(',')
            filters.append(sql.or_(*[Group.type == f for f in filter_types]))
        filter_parent = self.request.validated['querystring'].get('filter_parent')
        if filter_parent:
            filters.append(Group.parent_id == filter_parent)

        from_query=None
        query_callback = None
        if format == 'snippet':
            from_query = self.context.session.query(Group)
            from_query = from_query.options(
                Load(Group).load_only('id',
                                      'type',
                                      'name')).group_by(Group.id,
                                                        Group.type,
                                                        Group.name)



            def query_callback(from_query):
                filtered_groups = from_query.cte('filtered_groups')
                with_memberships = self.context.session.query(
                    filtered_groups,
                    func.count(Membership.id.distinct()).label('membership_count')
                    ).outerjoin(Membership).group_by(filtered_groups.c.id,
                                                     filtered_groups.c.type,
                                                     filtered_groups.c.name)
                filtered_memberships = with_memberships.order_by(
                    filtered_groups.c.name).cte('memberships')
                with_work_counts = self.context.session.query(
                    filtered_memberships,
                    func.count(Affiliation.work_id.distinct()).label('work_count'),
                    ).outerjoin(Affiliation).group_by(filtered_memberships)
                return with_work_counts



        listing = self.context.search(
            filters=filters,
            offset=offset,
            limit=limit,
            order_by=order_by,
            format=format,
            from_query=from_query,
            post_query_callback=query_callback,
            principals=self.request.effective_principals)
        schema = GroupSchema()
        result = {'total': listing['total'],
                  'records': [],
                  'snippets': [],
                  'limit': limit,
                  'offset': offset,
                  'status': 'ok'}

        if format == 'snippet':
            snippets = []
            for hit in listing['hits']:
                snippets.append({'id': hit.id,
                                 'name': hit.name,
                                 'type': hit.type,
                                 'works': hit.work_count,
                                 'members': hit.membership_count})
            result['snippets'] = snippets
        else:
            result['records'] = [schema.to_json(group.to_dict())
                                 for group in listing['hits']]

        return result

group_bulk = Service(name='GroupBulk',
                     path='/api/v1/group/bulk',
                     factory=ResourceFactory(GroupResource),
                     api_security=[{'jwt':[]}],
                     tags=['group'],
                     cors_origins=('*', ),
                     schema=GroupBulkRequestSchema(),
                     validators=(colander_bound_repository_body_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@group_bulk.post(permission='import')
def group_bulk_import_view(request):
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

group_search = Service(name='GroupSearch',
                     path='/api/v1/group/search',
                     factory=ResourceFactory(GroupResource),
                     api_security=[{'jwt':[]}],
                     tags=['group'],
                     cors_origins=('*', ),
                     schema=GroupSearchRequestSchema(),
                     validators=(colander_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@group_search.get(permission='search')
def group_search_view(request):
    offset = request.validated['querystring']['offset']
    limit = request.validated['querystring']['limit']
    order_by = [Group.name.asc()]
    query = request.validated['querystring'].get('query')
    filters = []
    if query:
        filters.append(Group.name.ilike('%%%s%%' % query))
    from_query = request.context.session.query(Group)
    from_query = from_query.options(
        Load(Group).load_only('id', 'name'))

    def query_callback(from_query):
        filtered_groups = from_query.cte('filtered_groups')
        with_memberships = request.context.session.query(
            filtered_groups,
            func.count(Membership.id).label('membership_count')
            ).outerjoin(Membership).group_by(filtered_groups.c.id,
                                             filtered_groups.c.name)
        return with_memberships

    # allow search listing with editor principals
    listing = request.context.search(
        filters=filters,
        offset=offset,
        limit=limit,
        order_by=order_by,
        format=format,
        from_query=from_query,
        post_query_callback=query_callback,
        principals=['group:editor'])
    snippets = []
    for hit in listing['hits']:
        snippets.append({'id': hit.id,
                         'name': hit.name,
                         'members': hit.membership_count})
    return {'total': listing['total'],
            'snippets': snippets,
            'limit': limit,
            'offset': offset,
            'status': 'ok'}

