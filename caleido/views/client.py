import colander
from cornice import Service

from caleido.security import authenticator_factory
from caleido.utils import OKStatus
from caleido.resources import TypeResource

class ClientSchema(colander.MappingSchema):
    status = OKStatus
    @colander.instantiate(missing=colander.drop)
    class dev_user(colander.MappingSchema):
        user = colander.SchemaNode(colander.String())
        token = colander.SchemaNode(colander.String())

    @colander.instantiate()
    class types(colander.SequenceSchema):
        @colander.instantiate()
        class type(colander.MappingSchema):
            id = colander.SchemaNode(colander.String())
            label = colander.SchemaNode(colander.String())
            @colander.instantiate()
            class fields(colander.SequenceSchema):
                @colander.instantiate()
                class field(colander.MappingSchema):
                    id = colander.SchemaNode(colander.String())
                    label = colander.SchemaNode(colander.String())
                    type = colander.SchemaNode(colander.String())
            @colander.instantiate()
            class filters(colander.SequenceSchema):
                @colander.instantiate()
                class filter(colander.MappingSchema):
                    label = colander.SchemaNode(colander.String())
                    id = colander.SchemaNode(colander.String())
                    @colander.instantiate()
                    class values(colander.SequenceSchema):
                        @colander.instantiate()
                        class value(colander.MappingSchema):
                            id = colander.SchemaNode(colander.String())
                            label = colander.SchemaNode(colander.String())

            @colander.instantiate()
            class types(colander.SequenceSchema):
                @colander.instantiate()
                class type(colander.MappingSchema):
                    id = colander.SchemaNode(colander.String())
                    label = colander.SchemaNode(colander.String())

class ClientResponseSchema(colander.MappingSchema):
    body = ClientSchema()



client = Service(name='Client',
                 path='/api/v1/client',
                 tags=['config'],
                 cors_origins=('*', ),
                 response_schemas={
    '200': ClientResponseSchema(description='Ok')})

@client.get()
def client_config(request):
    group_types = [{'id': v['key'], 'label': v['label']}
                   for v in TypeResource(request.dbsession, 'group').to_dict()['values']]
    result = {
        'status': 'ok',
        'types': [{'id': 'person',
                   'fields': [{'id': 'name',
                               'label': 'Person Name',
                               'type': 'text'},
                              {'id': 'memberships',
                               'label': 'Memberships',
                               'type': 'number'}],
                   'types': [],
                   'filters': [],
                   'label': 'Person', 'label_plural': 'Persons'},
                  {'id': 'group',
                   'label': 'Group',
                   'types': group_types,
                   'filters': [{'label': 'Group Type',
                                'id': 'type',
                                'values': group_types}],
                   'label_plural': 'Groups',
                   'fields': [{'id': 'name',
                               'label': 'Group Name',
                               'type': 'text'},
                              {'id': 'members',
                               'label': 'Members',
                               'type': 'number'}],
                   }]
        }
    dev_user_id = request.registry.settings.get('caleido.debug_dev_user')
    if dev_user_id:
        auth_context = authenticator_factory(request)
        principals = auth_context.principals(dev_user_id)
        token = request.create_jwt_token(dev_user_id, principals=principals)
        result['dev_user'] = {'user': dev_user_id, 'token': token}
    return result
