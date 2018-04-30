import colander

from sqlalchemy import func
from sqlalchemy.orm import Load

from cornice.resource import resource, view
from cornice.validators import colander_validator
from cornice import Service

from caleido.models import Person, Membership, Group, Contributor
from caleido.resources import ResourceFactory, PersonResource

from caleido.exceptions import StorageError
from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema,
                           OKStatusResponseSchema,
                           OKStatus,
                           JsonMappingSchemaSerializerMixin,
                           colander_bound_repository_body_validator)

@colander.deferred
def deferred_account_type_validator(node, kw):
    types = kw['repository'].type_config('person_account_type')
    return colander.OneOf([t['key'] for t in types])

@colander.deferred
def deferred_position_type_validator(node, kw):
    types = kw['repository'].type_config('position_type')
    return colander.OneOf([t['key'] for t in types])


def person_validator(node, kw):
    if not kw.get('given_name') and not kw.get('initials'):
        node.name = '%s.given_name' % node.name
        raise colander.Invalid(
            node, "Required: supply either 'initials' or 'given_name'")

class PersonSchema(colander.MappingSchema, JsonMappingSchemaSerializerMixin):
    def __init__(self, *args, **kwargs):
        kwargs['validator'] = person_validator
        super(PersonSchema, self).__init__(*args, **kwargs)

    id = colander.SchemaNode(colander.Int())
    name = colander.SchemaNode(colander.String(),
                                missing=colander.drop)
    family_name = colander.SchemaNode(colander.String())
    family_name_prefix = colander.SchemaNode(colander.String(),
                                             missing=None)
    given_name = colander.SchemaNode(colander.String(), missing=None)
    initials = colander.SchemaNode(colander.String(), missing=None)
    alternative_name = colander.SchemaNode(colander.String(), missing=None)
    honorary = colander.SchemaNode(colander.String(), missing=None)


    @colander.instantiate(missing=colander.drop)
    class accounts(colander.SequenceSchema):
        @colander.instantiate()
        class account(colander.MappingSchema):
            type = colander.SchemaNode(colander.String(),
                                       validator=deferred_account_type_validator)
            value = colander.SchemaNode(colander.String())

    @colander.instantiate(missing=colander.drop)
    class memberships(colander.SequenceSchema):
        @colander.instantiate()
        class membership(colander.MappingSchema):
            group_id = colander.SchemaNode(colander.Integer())
            _group_name = colander.SchemaNode(colander.String(),
                                              missing=colander.drop)
            start_date = colander.SchemaNode(colander.Date(),
                                             missing=colander.drop)
            end_date = colander.SchemaNode(colander.Date(),
                                           missing=colander.drop)


    @colander.instantiate(missing=colander.drop)
    class positions(colander.SequenceSchema):
        @colander.instantiate()
        class position(colander.MappingSchema):
            group_id = colander.SchemaNode(colander.Integer())
            _group_name = colander.SchemaNode(colander.String(),
                                              missing=colander.drop)
            type = colander.SchemaNode(colander.String(),
                                       validator=deferred_position_type_validator)
            description = colander.SchemaNode(colander.String(),
                                              missing=colander.drop)

            start_date = colander.SchemaNode(colander.Date(),
                                             missing=colander.drop)
            end_date = colander.SchemaNode(colander.Date(),
                                           missing=colander.drop)

class PersonPostSchema(PersonSchema):
    # similar to person schema, but id is optional
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)

class PersonResponseSchema(colander.MappingSchema):
    body = PersonSchema()

class PersonListingResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        status = OKStatus
        total = colander.SchemaNode(colander.Int())
        offset = colander.SchemaNode(colander.Int())
        limit = colander.SchemaNode(colander.Int())

        @colander.instantiate()
        class records(colander.SequenceSchema):
            person = PersonSchema()

        @colander.instantiate()
        class snippets(colander.SequenceSchema):
            @colander.instantiate()
            class snippet(colander.MappingSchema):
                id = colander.SchemaNode(colander.Int())
                name = colander.SchemaNode(colander.String())
                memberships = colander.SchemaNode(colander.Int())
                works = colander.SchemaNode(colander.Int())

                @colander.instantiate()
                class groups(colander.SequenceSchema):
                    @colander.instantiate()
                    class group(colander.MappingSchema):
                        id = colander.SchemaNode(colander.Int())
                        name = colander.SchemaNode(colander.String())


class PersonListingRequestSchema(colander.MappingSchema):
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
        format = colander.SchemaNode(
            colander.String(),
            validator=colander.OneOf(['record', 'snippet']),
            missing=colander.drop)

class PersonSearchRequestSchema(colander.MappingSchema):
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

class PersonBulkRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class records(colander.SequenceSchema):
        person = PersonSchema()

@resource(name='Person',
          collection_path='/api/v1/person/records',
          path='/api/v1/person/records/{id}',
          tags=['person'],
          cors_origins=('*', ),
          api_security=[{'jwt':[]}],
          factory=ResourceFactory(PersonResource))
class PersonRecordAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          response_schemas={
        '200': PersonResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a Person"
        return PersonSchema().to_json(self.context.model.to_dict())

    @view(permission='edit',
          schema=PersonSchema(),
          validators=(colander_bound_repository_body_validator,),
          cors_origins=('*', ),
          response_schemas={
        '200': PersonResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def put(self):
        "Modify a Person"
        body = self.request.validated
        body['id'] = int(self.request.matchdict['id'])
        self.context.model.update_dict(body)
        try:
            self.context.put()
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return
        return PersonSchema().to_json(self.context.model.to_dict())


    @view(permission='delete',
          response_schemas={
        '200': StatusResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def delete(self):
        "Delete an Person"
        self.context.delete()
        return {'status': 'ok'}

    @view(permission='add',
          schema=PersonPostSchema(),
          validators=(colander_bound_repository_body_validator,),
          cors_origins=('*', ),
          response_schemas={
        '201': PersonResponseSchema(description='Created'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new Person"
        person = Person.from_dict(self.request.validated)
        try:
            self.context.put(person)
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return

        self.request.response.status = 201
        return PersonSchema().to_json(person.to_dict())


    @view(permission='view',
          schema=PersonListingRequestSchema(),
          validators=(colander_validator),
          cors_origins=('*', ),
          response_schemas={
        '200': PersonListingResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        offset = self.request.validated['querystring']['offset']
        limit = self.request.validated['querystring']['limit']
        order_by = [Person.family_name.asc(), Person.name.asc()]
        format = self.request.validated['querystring'].get('format')
        if format == 'record':
            format = None
        query = self.request.validated['querystring'].get('query')
        filters = []
        if query:
            filters.append(Person.search_terms.match(query))
        from_query=None
        query_callback = None
        if format == 'snippet':
            from_query = self.context.session.query(Person)
            from_query = from_query.options(
                Load(Person).load_only('id', 'name')).group_by(Person.id,
                                                               Person.name)

            def query_callback(from_query):
                filtered_persons = from_query.cte('filtered_persons')
                with_memberships = self.context.session.query(
                    filtered_persons,
                    func.count(Membership.id.distinct()).label('membership_count'),
                    func.array_agg(Group.id.distinct()).label('group_ids'),
                    func.array_agg(Group.name.distinct()).label('group_names'),
                    func.count(Contributor.work_id.distinct()).label('work_count')
                    ).outerjoin(Contributor).outerjoin(Membership).outerjoin(
                    Group).group_by(filtered_persons.c.id,
                                    filtered_persons.c.name)
                return with_memberships.order_by(filtered_persons.c.name)

        listing = self.context.search(
            filters=filters,
            offset=offset,
            limit=limit,
            order_by=order_by,
            format=format,
            from_query=from_query,
            post_query_callback=query_callback,
            principals=self.request.effective_principals)
        schema = PersonSchema()
        result = {'total': listing['total'],
                  'records': [],
                  'snippets': [],
                  'limit': limit,
                  'offset': offset,
                  'status': 'ok'}

        if format == 'snippet':
            snippets = []
            for hit in listing['hits']:
                groups = [{'id': i[0], 'name': i[1]} for i in
                           zip(hit.group_ids, hit.group_names)]
                snippets.append(
                    {'id': hit.id,
                     'name': hit.name,
                     'groups': groups,
                     'works': hit.work_count,
                     'memberships': hit.membership_count})
            result['snippets'] = snippets
        else:
            result['records'] = [schema.to_json(person.to_dict())
                                 for person in listing['hits']]

        return result



person_bulk = Service(name='PersonBulk',
                     path='/api/v1/person/bulk',
                     factory=ResourceFactory(PersonResource),
                     api_security=[{'jwt':[]}],
                     tags=['person'],
                     cors_origins=('*', ),
                     schema=PersonBulkRequestSchema(),
                     validators=(colander_bound_repository_body_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@person_bulk.post(permission='import')
def person_bulk_import_view(request):
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

person_search = Service(name='PersonSearch',
                     path='/api/v1/person/search',
                     factory=ResourceFactory(PersonResource),
                     api_security=[{'jwt':[]}],
                     tags=['person'],
                     cors_origins=('*', ),
                     schema=PersonSearchRequestSchema(),
                     validators=(colander_validator,),
                     response_schemas={
    '200': OKStatusResponseSchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})

@person_search.get(permission='search')
def person_search_view(request):
    offset = request.validated['querystring']['offset']
    limit = request.validated['querystring']['limit']
    order_by = [Person.name.asc()]
    query = request.validated['querystring'].get('query')
    filters = []
    if query:
        filters.append(Person.search_terms.match(query))
    from_query = request.context.session.query(Person)
    from_query = from_query.options(
        Load(Person).load_only('id', 'name'))

    def query_callback(from_query):
        filtered_persons = from_query.cte('filtered_persons')
        with_memberships = request.context.session.query(
            filtered_persons,
            func.count(Membership.id).label('membership_count')
            ).outerjoin(Membership).group_by(filtered_persons.c.id,
                                             filtered_persons.c.name)
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
        if hit.membership_count == 0:
            info = ''
        elif hit.membership_count == 1:
            info = '1 membership'
        else:
            info = '%s memberships' % hit.membership_count

        snippets.append({'id': hit.id,
                         'name': hit.name,
                         'info': info,
                         'members': hit.membership_count})
    return {'total': listing['total'],
            'snippets': snippets,
            'limit': limit,
            'offset': offset,
            'status': 'ok'}

