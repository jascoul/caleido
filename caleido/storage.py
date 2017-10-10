from pyramid.decorator import reify
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema
import zope.sqlalchemy
import transaction

from caleido.models import Base, Repository, User, UserGroup, ActorType

DEFAULTS = {
    'user_groups': {100: 'Admin',
                    80: 'Manager',
                    60: 'Editor',
                    40: 'Owner',
                    10: 'Viewer'},
    'actor_types': {'individual': 'Individual',
                    'organisation': 'Organisation'}
    }

class Storage(object):
    schema_version = '0.1'
    def __init__(self, registry):
        self.registry = registry

    def repository_info(self, session):
        revisions = {}
        for repository in session.query(Repository).all():
            revisions[repository.namespace] = repository.to_dict()
        return revisions

    def create_repository(self, session, namespace, vhost_name):
        self.registry['engine'].execute(CreateSchema(namespace))
        session.add(Repository(namespace=namespace,
                               schema_version=self.schema_version,
                               vhost_name=vhost_name))
        session.flush()
        session.execute('SET search_path TO %s, public' % namespace);
        Base.metadata.create_all(bind=session.connection())
        session.flush()

    def drop_repository(self, session, namespace):
        self.registry['engine'].execute(DropSchema(namespace, cascade=True))
        repo = session.query(Repository).filter(
            Repository.namespace == namespace).first()
        if repo:
            session.delete(repo)
        session.flush()

    def create_all(self, session):
        session.execute('SET search_path TO public');
        Repository.__table__.create(bind=session.connection())
        session.flush()

    def drop_all(self, session):
        for repository in session.query(Repository).all():
            self.drop_repository(session, repository.namespace)
        Repository.__table__.drop(bind=session.connection())

    def make_session(self, namespace=None, transaction_manager=None):
        session = get_tm_session(
            self.registry['dbsession_factory'],
            transaction_manager or transaction.manager)
        if namespace:
            session.execute('SET search_path TO %s, public' % namespace);
        return session

    def initialize_repository(self, session, namespace, admin_userid, admin_credentials):
        session.execute('SET search_path TO %s, public' % namespace);
        user_groups = DEFAULTS['user_groups']
        for id, label in user_groups.items():
            session.add(UserGroup(id=id, label=label))
        session.flush()
        session.add(User(userid=admin_userid,
                         credentials=admin_credentials,
                         user_group=100))
        session.flush()
        actor_types = DEFAULTS['actor_types']
        for key, label in actor_types.items():
            session.add(ActorType(key=key, label=label))
        session.flush()
        session.execute('SET search_path TO public');
        session.flush()


def get_tm_session(session_factory, transaction_manager):
    """
    Get a ``sqlalchemy.orm.Session`` instance backed by a transaction.

    This function will hook the session to the transaction manager which
    will take care of committing any changes.

    - When using pyramid_tm it will automatically be committed or aborted
      depending on whether an exception is raised.

    - When using scripts you should wrap the session in a manager yourself.
      For example::

          import transaction

          engine = get_engine(settings)
          session_factory = get_session_factory(engine)
          with transaction.manager:
              dbsession = get_tm_session(session_factory, transaction.manager)

    """
    dbsession = session_factory()

    zope.sqlalchemy.register(
        dbsession, transaction_manager=transaction_manager)
    return dbsession


def includeme(config):
    """
    Initialize the model for a Pyramid app.

    Activate this setup using ``config.include('caleido.models')``.

    """
    settings = config.get_settings()

    settings['tm.manager_hook'] = 'pyramid_tm.explicit_manager'

    # use pyramid_tm to hook the transaction lifecycle to the request
    config.include('pyramid_tm')

    # use pyramid_retry to retry a request when transient exceptions occur
    config.include('pyramid_retry')

    engine = engine_from_config(settings, prefix='sqlalchemy.')

    session_factory = sessionmaker()
    session_factory.configure(bind=engine)

    config.registry['engine'] = engine
    config.registry['dbsession_factory'] = session_factory

    def new_dbsession(request):
        session = get_tm_session(session_factory, request.tm)
        host = request.headers['Host'].split(':')[0]
        repository = session.query(Repository).filter(Repository.vhost_name == host).first()
        if repository:
            session.execute(
                'SET search_path TO %s, public' % repository.namespace);
        return session

    config.add_request_method(new_dbsession, 'new_dbsession')
    # make request.dbsession available for use in Pyramid
    config.add_request_method(
        new_dbsession,
        'dbsession',
        reify=True
        )

    config.registry['storage'] = Storage(config.registry)
