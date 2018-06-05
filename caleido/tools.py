import sys
import os
import json

from pyramid.paster import get_appsettings
from caleido import main
from caleido.models import Person, Group, Work
import transaction
import sqlalchemy as sql
import sqlalchemy.dialects.postgresql  as postgresql
from sqlalchemy.inspection import inspect

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

def bigquery_schema():
    if len(sys.argv) == 1:
        cmd = os.path.basename(sys.argv[0])
        print('usage: %s content_type \n'
              'example: "%s works|persons|groups"' % (cmd, cmd))
        sys.exit(1)
    kind = sys.argv[1]
    if kind == 'person':
        model = Person
    elif kind == 'group':
        model = Group
    elif kind == 'work':
        model = Work
    else:
        print('Error: unknown kind: %s' % kind)
        sys.exit(1)
    def model2schema(model):
        schema = []
        mapper = inspect(model)
        for column in mapper.columns:
            field = {'name': column.name,
                     'type': 'string'}
            if column.name == 'during':
                schema.append({'name': 'start_date', 'type': 'date'})
                schema.append({'name': 'end_date', 'type': 'date'})
                continue
            elif isinstance(column.type, sql.BigInteger):
                field['type'] = 'integer'
            elif isinstance(column.type, sql.Integer):
                field['type'] = 'integer'
            elif isinstance(column.type, sql.Boolean):
                field['type'] = 'boolean'
            elif isinstance(column.type, sql.Float):
                field['type'] = 'float'
            elif isinstance(column.type, sql.Date):
                field['type'] = 'date'
            elif isinstance(column.type, sql.DateTime):
                field['type'] = 'dateTime'
            elif isinstance(column.type, postgresql.TSVECTOR):
                continue
            schema.append(field)
        for relation in mapper.relationships:
            if relation.info.get('inline_schema') is True:
                field = {'name': relation.key,
                         'type': 'record',
                         'mode': 'repeated',
                         'fields': model2schema(relation.argument())}
                schema.append(field)
        return schema

    schema = model2schema(model)
    schema.append({'name': 'modified', 'type': 'datetime'})

    print(json.dumps(schema))


