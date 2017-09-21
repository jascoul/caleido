"""Main entry point
"""
from pyramid.config import Configurator

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include("cornice")
    config.include("cornice_swagger")
    config.include("scributor.storage")
    config.scan("scributor.views")
    return config.make_wsgi_app()

