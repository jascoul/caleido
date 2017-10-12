from operator import attrgetter

import cornice
import colander
from cornice import Service
from cornice.service import get_services
from pyramid.view import view_config
from cornice_swagger import CorniceSwagger
from cornice_swagger.converters import TypeConversionDispatcher
from caleido.utils import colander_bound_repository_body_validator

# Create a service to serve our OpenAPI spec
swagger = Service(name='OpenAPI',
                  path='/__api__',
                  description="OpenAPI documentation")

def body_schema_transformer(schema, args):
    validators = args.get('validators', [])
    if colander_bound_repository_body_validator in validators:
        body_schema = schema
        schema = colander.MappingSchema()
        schema['body'] = body_schema
    return schema

class TypeConverterWithDeferredSupport(TypeConversionDispatcher):
    """
    This class subclasses TypeConversionDispatcher to add support
    for deferred validators. The deferreds are executed so the return
    values can be used in the OpenAPI schema.

    The deferreds get access to the repository config object in the
    validator similar to the arguments used when being bound by
    `caleido.utils.colander_bound_repository_body_validator`
    """

    deferred_args = {}
    def __call__(self, schema_node):
        if isinstance(schema_node.validator, colander.deferred):
            schema_node.validator = schema_node.validator(schema_node,
                                                          self.deferred_args)
        return super(
            TypeConverterWithDeferredSupport, self).__call__(schema_node)


@swagger.get()
def openAPI_v1_spec(request):
    services = get_services()
    services.sort(key=attrgetter('path'))
    CorniceSwagger.schema_transformers.append(body_schema_transformer)
    CorniceSwagger.type_converter = TypeConverterWithDeferredSupport
    CorniceSwagger.type_converter.deferred_args = {
        'repository': request.repository}
    doc = CorniceSwagger(services)
    extra_fields = {
        'securityDefinitions': {
        'jwt': {'type': 'apiKey',
                'description': (
                     'Enter a valid token as returned by the '
                     '/auth/login endpoint.\n\n'
                     'Note: The token should be prefixed with "Bearer "'),
                'in': 'header',
                'name': 'Authorization'}}
        }
    my_spec = doc.generate('Caleido API',
                           '1.0.0',
                           swagger=extra_fields)
    return my_spec


@view_config(route_name='swagger_ui',
             renderer='caleido:templates/swagger.pt')
def swagger_ui_view(request):
    return {'swagger_api_url': request.route_url('OpenAPI')}
