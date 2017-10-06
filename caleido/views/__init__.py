import colander
from operator import attrgetter

from cornice import Service
from cornice.service import get_services
from pyramid.view import view_config

from cornice_swagger import CorniceSwagger
# Create a service to serve our OpenAPI spec
swagger = Service(name='OpenAPI',
                  path='/__api__',
                  description="OpenAPI documentation")


@swagger.get()
def openAPI_v1_spec(request):
    services = get_services()
    services.sort(key=attrgetter('path'))    
    doc = CorniceSwagger(services)
    extra_fields = {
        'securityDefinitions': {
        'jwt': {'type': 'apiKey',
                'description': ('Enter a valid token as returned by the /auth/login endpoint.\n\n'
                                'Note: The token should be prefixed with "Bearer "'),
                'in': 'header',
                'name': 'Authorization'}}
        }#
        #'security': [{'jwt': []}]}
    my_spec = doc.generate('Caleido API',
                           '1.0.0',
                           swagger=extra_fields)
    return my_spec

@view_config(route_name='swagger_ui',
             renderer='scributor:templates/swagger.pt')
def swagger_ui_view(request):
    return {'swagger_api_url': request.route_url('OpenAPI')}
