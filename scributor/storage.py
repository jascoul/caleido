from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
import zope.sqlalchemy
import transaction

from scributor.models import Base, User, UserGroup

class Storage(object):
    def __init__(self, settings):
        self.settings = settings
        self.engine = get_engine(settings)
        self.session_factory = get_session_factory(self.engine)

    def session(self):
        return get_tm_session(self.session_factory, transaction.manager)

    def create_all(self):
        Base.metadata.create_all(self.engine)

    def drop_all(self):
        Base.metadata.drop_all(self.engine)
        
    def initialize(self, admin_principal, admin_credential):
        session = self.session()
        user_groups = {100: 'Admin',
                       80: 'Manager',
                       60: 'Editor',
                       40: 'Owner',
                       10: 'Viewer'}
        for id, label in user_groups.items():
            session.add(UserGroup(id=id, label=label))
        transaction.commit()
        session.add(User(principal=admin_principal,
                         credential=admin_credential,
                         user_group=100))
        transaction.commit()

def get_engine(settings, prefix='sqlalchemy.'):
    return engine_from_config(settings, prefix)


def get_session_factory(engine):
    factory = sessionmaker()
    factory.configure(bind=engine)
    return factory


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

    Activate this setup using ``config.include('scributor.models')``.

    """
    settings = config.get_settings()
    settings['tm.manager_hook'] = 'pyramid_tm.explicit_manager'

    # use pyramid_tm to hook the transaction lifecycle to the request
    config.include('pyramid_tm')

    # use pyramid_retry to retry a request when transient exceptions occur
    config.include('pyramid_retry')

    storage = Storage(settings)

    config.registry['storage'] = storage
    
    # make request.storage available for use in Pyramid
    config.add_request_method(lambda r: storage, 'storage', reify=True)
