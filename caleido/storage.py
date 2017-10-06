from pyramid.decorator import reify
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
import zope.sqlalchemy
import transaction

from caleido.models import Base, User, UserGroup, ActorType

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
    def __init__(self, registry):
        self.registry = registry
        
    def create_all(self):
        Base.metadata.create_all(self.registry['engine'])

    def drop_all(self):
        Base.metadata.drop_all(self.registry['engine'])

    def make_session(self, transaction_manager=None):
        return get_tm_session(
            self.registry['dbsession_factory'],
            transaction_manager or transaction.manager)
    
    def initialize(self, admin_userid, admin_credentials):
        with transaction.manager:
            session = self.make_session()
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
        return get_tm_session(session_factory, request.tm)
    config.add_request_method(new_dbsession, 'new_dbsession')
    # make request.dbsession available for use in Pyramid
    config.add_request_method(
        # r.tm is the transaction manager used by pyramid_tm
        lambda r: new_dbsession(r),
        'dbsession',
        reify=True
        )

    config.registry['storage'] = Storage(config.registry)
