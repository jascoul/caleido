import colander
from cornice import Service

from caleido.security import authenticator_factory
from caleido.utils import OKStatus

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
    result = {'status': 'ok',
              'types': [{'id': 'person',
                         'label': 'Person', 'label_plural': 'Persons'},
                        {'id': 'group',
                         'label': 'Group', 'label_plural': 'Groups'},
                        {'id': 'user',
                         'label': 'User', 'label_plural': 'Users'}]}
    dev_user_id = request.registry.settings.get('caleido.debug_dev_user')
    if dev_user_id:
        auth_context = authenticator_factory(request)
        principals = auth_context.principals(dev_user_id)
        token = request.create_jwt_token(dev_user_id, principals=principals)
        result['dev_user'] = {'user': dev_user_id, 'token': token}
    return result
