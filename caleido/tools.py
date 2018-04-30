import sys
import os

from pyramid.paster import get_appsettings
from caleido import main
import transaction

def initialize_db():
    if len(sys.argv) == 1:
        cmd = os.path.basename(sys.argv[0])
        print('usage: %s <config_uri> [schema]\n'
              'example: "%s development.ini test"' % (cmd, cmd))
        sys.exit(1)
    settings = get_appsettings(sys.argv[1])
    app = main({}, **settings)
    storage = app.registry['storage']
    session = storage.make_session()
    if len(sys.argv) == 3:
        repo = sys.argv[2]
        print('Creating "%s" repository on "%s.localhost"' % (repo, repo))
        storage.create_repository(session, repo, '%s.localhost' % repo)
        storage.initialize_repository(session, repo, 'admin', 'admin')
    else:
        storage.create_all(session)
        print('Creating "unittest" repository on "unittest.localhost"')
        storage.create_repository(session, 'unittest', 'unittest.localhost')
        print('Creating "test" repository on "localhost"')
        storage.create_repository(session, 'test', 'localhost')
        print('- Adding user "admin" with password "admin"')
        storage.initialize_repository(session, 'test', 'admin', 'admin')
    transaction.commit()

def drop_db():
    if len(sys.argv) == 1:
        cmd = os.path.basename(sys.argv[0])
        print('usage: %s <config_uri> [schema]\n'
              'example: "%s development.ini test"' % (cmd, cmd))
        sys.exit(1)
    settings = get_appsettings(sys.argv[1])
    app = main({}, **settings)
    storage = app.registry['storage']
    session = storage.make_session()
    if len(sys.argv) == 3:
        repo = sys.argv[2]
        print('Dropping "%s" repository on "%s.localhost"' % (repo, repo))
        storage.drop_repository(session, repo)
    else:
        print('Dropping all repositories"')
        storage.drop_all(session)
    transaction.commit()

