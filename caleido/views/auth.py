import json

import jwt
import colander
from pyramid.view import forbidden_view_config, notfound_view_config
from pyramid.httpexceptions import HTTPForbidden
from pyramid.interfaces import IAuthenticationPolicy

from cornice import Service
from cornice.validators import colander_body_validator

from caleido.security import authenticator_factory
from caleido.utils import ErrorResponseSchema, OKStatus

class AuthLoginSchema(colander.MappingSchema):
    user = colander.SchemaNode(colander.String())
    password = colander.SchemaNode(colander.String())

class AuthRenewSchema(colander.MappingSchema):
    token = colander.SchemaNode(colander.String())

class AuthLoggedInSchema(colander.MappingSchema):
    status = OKStatus
    token = colander.SchemaNode(colander.String())

class AuthLoggedInBodySchema(colander.MappingSchema):
    body = AuthLoggedInSchema()

login = Service(name='login',
                path='/api/v1/auth/login',
                validators=(colander_body_validator,),
                factory=authenticator_factory,
                cors_origins=('*', ),
                response_schemas={
        '20O': AuthLoggedInBodySchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
@login.post(tags=['auth'], schema=AuthLoginSchema())
def login_view(request):
    user_id = request.validated['user']
    credentials = request.validated['password']
    if not request.context.valid_user(user_id, credentials):
        raise HTTPForbidden('Unauthorized')
    principals = request.context.principals(user_id)
    result = {'status': 'ok',
              'token': request.create_jwt_token(user_id, principals=principals)}

    return result



renew = Service(name='renew',
                path='/api/v1/auth/renew',
                validators=(colander_body_validator,),
                factory=authenticator_factory,
                cors_origins=('*', ),
                response_schemas={
    '20O': AuthLoggedInBodySchema(description='Ok'),
    '400': ErrorResponseSchema(description='Bad Request'),
    '401': ErrorResponseSchema(description='Unauthorized')})
@renew.post(tags=['auth'], schema=AuthRenewSchema())
def renew_view(request):
    token = request.validated['token']
    policy = request.registry.queryUtility(IAuthenticationPolicy)
    try:
        claims = jwt.decode(token, policy.private_key)
    except jwt.InvalidTokenError as e:
        raise HTTPForbidden('Invalid JWT token: %s' % e)

    user_id = claims['sub']
    if not request.context.existing_user(user_id):
        raise HTTPForbidden('Invalid JWT token: unknown user')

    principals = request.context.principals(user_id)
    result = {'status': 'ok',
              'token': request.create_jwt_token(user_id, principals=principals)}
    return result

@forbidden_view_config()
def forbidden_view(request):
    response = request.response
    description = None
    if request.errors and request.errors.status == 404:
        response.status = 404
        response.content_type = 'application/json'
        response.write(
            json.dumps({'status': 'error',
                        'errors': request.errors}).encode('utf8'))
        return response

    if request.exception and request.exception.detail:
        description = request.exception.detail
    if request.authenticated_userid or request.headers.get('Authorization'):
        response.status = 403
        response.content_type = 'application/json'
        response.write(
            json.dumps({'status': 'error',
                        'errors': [{'name': 'forbidden',
                                    'description': description or 'Forbidden',
                                    'location': 'request'}]}).encode('utf8'))
    else:
        response.status = 401
        response.content_type = 'application/json'
        response.headers['Location'] = request.route_url('login')
        response.write(
            json.dumps({'status': 'error',
                        'errors': [{'name': 'unauthorized',
                                    'description': description or 'Unauthorized',
                                    'location': 'request'}]}).encode('utf8'))
    return response

@notfound_view_config()
def notfound_view(request):
    description = None
    if request.exception and request.exception.detail:
        description = request.exception.detail
    response = request.response
    response.status = 404
    response.content_type = 'application/json'
    response.write(
        json.dumps({'status': 'error',
                    'errors': [{'name': 'not found',
                                'description': description or 'Not Found',
                                'location': 'request'}]}).encode('utf8'))
    return response

