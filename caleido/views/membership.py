import datetime

from intervals import DateInterval
import colander
import sqlalchemy as sql
from sqlalchemy import func
from cornice.resource import resource, view
from cornice.validators import colander_validator
from cornice import Service

from caleido.models import Membership, Person, Group, Contributor
from caleido.resources import ResourceFactory, MembershipResource, GroupResource

from caleido.exceptions import StorageError
from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema,
                           OKStatusResponseSchema,
                           OKStatus,
                           JsonMappingSchemaSerializerMixin,
                           colander_bound_repository_body_validator,
                           )

class MembershipSchema(colander.MappingSchema, JsonMappingSchemaSerializerMixin):
    id = colander.SchemaNode(colander.Int())
    person_id = colander.SchemaNode(colander.Int())
    _person_name = colander.SchemaNode(colander.String(),
                                       missing=colander.drop)
    group_id = colander.SchemaNode(colander.Int())
    _group_name = colander.SchemaNode(colander.String(),
                                      missing=colander.drop)
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
        status = OKStatus
        total = colander.SchemaNode(colander.Int())
        offset = colander.SchemaNode(colander.Int())
        limit = colander.SchemaNode(colander.Int())

        @colander.instantiate()
        class records(colander.SequenceSchema):
            membership = MembershipSchema()

        @colander.instantiate()
        class snippets(colander.SequenceSchema):
            @colander.instantiate()
            class snippet(colander.MappingSchema):
                person_id = colander.SchemaNode(colander.Int())
                person_name = colander.SchemaNode(colander.String())
                works = colander.SchemaNode(colander.Int())

                @colander.instantiate()
                class groups(colander.SequenceSchema):
                    @colander.instantiate()
                    class group(colander.MappingSchema):
                        group_id = colander.SchemaNode(colander.Int())
                        group_name = colander.SchemaNode(colander.String())

                earliest = colander.SchemaNode(colander.Date(),
                                                 missing=colander.drop)
                latest = colander.SchemaNode(colander.Date(),
                                             missing=colander.drop)

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
        query = colander.SchemaNode(colander.String(),
                                    missing=colander.drop)
        person_id = colander.SchemaNode(colander.Int(),
                                        missing=colander.drop)
        group_id = colander.SchemaNode(colander.Int(),
                                       missing=colander.drop)
        transitive = colander.SchemaNode(colander.Boolean(),
                                       missing=False)
        start_date = colander.SchemaNode(colander.Date(),
                                         missing=colander.drop)
        end_date = colander.SchemaNode(colander.Date(),
                                       missing=colander.drop)
        format = colander.SchemaNode(
            colander.String(),
            validator=colander.OneOf(['record', 'snippet']),
            missing=colander.drop)

class MembershipBulkRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class records(colander.SequenceSchema):
        membership = MembershipSchema()

@resource(name='Membership',
          collection_path='/api/v1/membership/records',
          path='/api/v1/membership/records/{id}',
          tags=['membership'],
          cors_origins=('*', ),
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
        qs = self.request.validated['querystring']
        offset = qs['offset']
        limit = qs['limit']
        person_id = qs.get('person_id')
        group_id = qs.get('group_id')
        format = qs.get('format')
        order_by = []
        query = qs.get('query')
        filters = []
        if person_id:
            filters.append(Membership.person_id == person_id)
        if qs.get('start_date') or qs.get('end_date'):
            duration = DateInterval([qs.get('start_date'),
                                     qs.get('end_date')])
            filters.append(Membership.during.op('&&')(duration))

        if group_id:
            if qs['transitive']:
                # find
                group_ids = [group_id]
                group_ids.extend(ResourceFactory(GroupResource)(
                    self.request, group_id).child_groups())
                filters.append(
                    sql.or_(*[Membership.group_id == g for g in group_ids]))
            else:
                filters.append(Membership.group_id == group_id)


        cte_total = None
        from_query=None
        query_callback = None
        if format == 'record':
            format = None
        elif format == 'snippet':
            from_query = self.context.session.query(Membership)
            def query_callback(from_query):
                filtered_members = from_query.cte('filtered_members')
                with_members = self.context.session.query(
                    func.min(func.coalesce(func.lower(filtered_members.c.during),
                                           datetime.date(1900, 1, 1))).label('earliest'),
                    func.max(func.coalesce(func.upper(filtered_members.c.during),
                                           datetime.date(2100, 1, 1))).label('latest'),
                    func.count(filtered_members.c.id.distinct()).label('memberships'),
                    func.count(Contributor.work_id.distinct()).label('works'),
                    func.array_agg(Group.id.distinct()).label('group_ids'),
                    func.array_agg(Group.name.distinct()).label('group_names'),
                    func.max(filtered_members.c.id).label('id'),
                    Person.id.label('person_id'),
                    Person.name.label('person_name')).join(
                    Person).join(Group).outerjoin(Person.contributors)
                if query and group_id:
                    with_members = with_members.filter(
                        Person.family_name.ilike('%%%s%%' % query))
                with_members = with_members.group_by(Person.id,
                                                     Person.name)
                return with_members.order_by(Person.name)

        listing = self.context.search(
            from_query=from_query,
            filters=filters,
            offset=offset,
            limit=limit,
            order_by=order_by,
            post_query_callback=query_callback,
            apply_limits_post_query={'snippet': True}.get(format, False),
            principals=self.request.effective_principals)
        schema = MembershipSchema()
        result = {'total': listing['total'] or cte_total,
                  'records': [],
                  'snippets': [],
                  'limit': limit,
                  'status': 'ok',
                  'offset': offset}

        if format == 'snippet':
            snippets = []
            for hit in listing['hits']:
                #start_date, end_date = parse_duration(hit.during,
                #                                      format='%Y-%m-%d')
                earliest = hit.earliest
                if earliest:
                    if earliest.year == 1900:
                        earliest = None
                    else:
                        earliest = earliest.strftime('%Y-%m-%d')

                latest = hit.latest
                if latest:
                    if latest.year == 2100:
                        latest = None
                    else:
                        latest = latest.strftime('%Y-%m-%d')

                groups = [{'id': i[0], 'name': i[1]} for i in
                          zip(hit.group_ids, hit.group_names)]

                snippets.append({'id': hit.id,
                                 'person_id': hit.person_id,
                                 'person_name': hit.person_name,
                                 'groups': groups,
                                 'earliest': earliest,
                                 'latest': latest,
                                 'works': hit.works,
                                 'memberships': hit.memberships})
            result['snippets'] = snippets
        else:
            result['records'] = [schema.to_json(person.to_dict())
                                 for person in listing['hits']]

        return result

membership_listing = Service(name='MembershipListing',
                     path='/api/v1/membership/listing',
                     factory=ResourceFactory(MembershipResource),
                     api_security=[{'jwt':[]}],
                     tags=['membership'],
                     cors_origins=('*', ),
                     schema=MembershipListingRequestSchema(),
                     validators=(colander_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@membership_listing.get(permission='view')
def membership_listing_view(request):
    qs = request.validated['querystring']
    params = dict(offset = qs['offset'],
                  limit = qs['limit'],
                  text_query = qs.get('query'),
                  order_by = qs.get('order_by'),
                  start_date = qs.get('start_date'),
                  end_date = qs.get('end_date'),
                  principals=request.effective_principals)

    if qs.get('person_id'):
        params['person_ids'] = [qs['person_id']]
    if qs.get('group_id'):
        params['group_ids'] = [qs['group_id']]
        params['group_ids'].extend(ResourceFactory(GroupResource)(
            request, qs['group_id']).child_groups())

    result = request.context.listing(**params)
    result['snippets'] = result.pop('hits')
    result['status'] = 'ok'
    return result


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
