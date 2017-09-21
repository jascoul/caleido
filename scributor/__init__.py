"""Main entry point
"""
from pyramid.config import Configurator

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include("cornice")
    config.include("cornice_swagger")
    config.include('pyramid_chameleon')
    config.include("scributor.storage")
    
    config.add_route('swagger_ui', '/api/swagger.html')
    config.scan("scributor.views")
    config.add_static_view('api', path='scributor:static/dist/swagger')

    return config.make_wsgi_app()

