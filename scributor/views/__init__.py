import colander
from cornice import Service
from cornice.service import get_services
from cornice.validators import colander_body_validator
from pyramid.view import view_config

from cornice_swagger import CorniceSwagger
                
_VALUES = {}


# Create a simple service that will store and retrieve values
values = Service(name='foo',
                 path='/values/{key}',
                 description="Cornice Demo")


# Create a body schema for our requests
class BodySchema(colander.MappingSchema):
        value = colander.SchemaNode(colander.String(),
                                    description='My precious value')


# Create a response schema for our 200 responses
class OkResponseSchema(colander.MappingSchema):
    body = BodySchema()
    

# Aggregate the response schemas for get requests
response_schemas = {
    '200': OkResponseSchema(description='Return value')
    }


# Create our cornice service views
class MyValueApi(object):
    """My precious API."""
    
    @values.get(tags=['values'], response_schemas=response_schemas)
    def get_value(request):
        """Returns the value."""
        key = request.matchdict['key']
        return _VALUES.get(key)
    
    @values.put(tags=['values'], validators=(colander_body_validator, ),
                schema=BodySchema(), response_schemas=response_schemas)
    def set_value(request):
        """Set the value and returns *True* or *False*."""
        
        key = request.matchdict['key']
        _VALUES[key] = request.json_body
        return _VALUES.get(key)
    
    
# Create a service to serve our OpenAPI spec
swagger = Service(name='OpenAPI',
                  path='__api__',
                  description="OpenAPI documentation")


@swagger.get()
def openAPI_v1_spec(request):
    doc = CorniceSwagger(get_services())
    my_spec = doc.generate('Scributor API', '1.0.0')
    return my_spec

@view_config(route_name='swagger_ui',
             renderer='scributor:templates/swagger.pt')
def swagger_ui_view(request):
    return {'swagger_api_url': request.route_url('OpenAPI')}

hello = Service(name='hello', path='/', description="Simplest app")

@hello.get()
def get_info(request):
    """Returns Hello in JSON."""
    return {'Hello': 'World'}
