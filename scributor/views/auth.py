import json

import colander
from pyramid.view import forbidden_view_config
from pyramid.httpexceptions import HTTPUnauthorized
from cornice import Service
from cornice.validators import colander_body_validator

from scributor.security import authenticator_factory
from scributor.utils import ErrorBodySchema

class AuthLoginSchema(colander.MappingSchema):
    user = colander.SchemaNode(colander.String())
    password = colander.SchemaNode(colander.String())

class AuthLoggedInSchema(colander.MappingSchema):
    status = colander.SchemaNode(colander.String())
    token = colander.SchemaNode(colander.String())

class AuthLoggedInBodySchema(colander.MappingSchema):
    body = AuthLoggedInSchema()

login = Service(name='login',
                path='/api/v1/auth/login',
                schema=AuthLoginSchema(),
                validators=(colander_body_validator,),
                factory=authenticator_factory,
                response_schemas={
        '20O': AuthLoggedInBodySchema(description='Ok'),
        '400': ErrorBodySchema(description='Bad Request'),
        '401': ErrorBodySchema(description='Unauthorized')})
@login.post()
def login_view(request):
    body = json.loads(request.body.decode('utf8'))
    user_id = body['user']
    credentials = body['password']
    principals = request.context.principals(user_id, credentials)
    if principals is None:
        raise HTTPUnauthorized('Unauthorized')
    result = {'status': 'ok',
              'token': request.create_jwt_token(user_id, principals=principals)}
    
    return result


@forbidden_view_config()
def forbidden_view(request):
    response = request.response
    if request.authenticated_userid:
        response.status = 403
        response.content_type = 'application/json'
        response.write(
            json.dumps({'status': 'error',
                        'errors': [{'name': 'forbidden',
                                    'description': 'Forbidden',
                                    'location': 'request'}]}).encode('utf8'))
    else:
        response.status = 401
        response.content_type = 'application/json'
        response.headers['Location'] = request.route_url('login')
        response.write(
            json.dumps({'status': 'error',
                        'errors': [{'name': 'unauthorized',
                                    'description': 'Unauthorized',
                                    'location': 'request'}]}).encode('utf8'))
    return response
