import sys
import os

from pyramid.paster import get_appsettings
from scributor import main
import transaction
 
def initialize_db():
    if not len(sys.argv) == 2:
        cmd = os.path.basename(sys.argv[0])
        print('usage: %s <config_uri>\n'
              'example: "%s development.ini"' % (cmd, cmd))
        sys.exit(1)
    settings = get_appsettings(sys.argv[1])
    app = main({}, **settings)
    storage = app.registry['storage']
    storage.create_all()
    with transaction.manager:
        storage.initialize('admin', 'admin')
    
def drop_db():
    if not len(sys.argv) == 2:
        cmd = os.path.basename(sys.argv[0])
        print('usage: %s <config_uri>\n'
              'example: "%s development.ini"' % (cmd, cmd))
        sys.exit(1)
    settings = get_appsettings(sys.argv[1])
    app = main({}, **settings)
    storage = app.registry['storage']
    storage.drop_all()
    
    
