"""Main entry point
"""
from pyramid.config import Configurator

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include("cornice")
    config.include("pyramid_tm")
    config.include("scributor.models")
    config.scan("scributor.views")
    return config.make_wsgi_app()

