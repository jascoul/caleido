from pyramid.decorator import reify
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema
import zope.sqlalchemy
import transaction

from caleido.interfaces import IBlobStoreBackend
from caleido.blob import BlobStore
from caleido.models import (Base,
                            Repository,
                            User, UserGroup,
                            GroupType,
                            WorkType,
                            ContributorRole,
                            PersonAccountType,
                            IdentifierType,
                            MeasureType,
                            RelationType,
                            DescriptionType,
                            PositionType,
                            DescriptionFormat,
                            GroupAccountType)

DEFAULTS = {
    'user_groups': {100: 'Admin',
                    80: 'Manager',
                    60: 'Editor',
                    40: 'Owner',
                    10: 'Viewer'},
    'group_types': {'organisation': 'Organisation'},
    'contributor_roles': {'author': 'Author'},
    'work_types': {'article': 'Article'},
    'person_account_types': {'email': 'email',
                             'local': 'Local',
                             'wikipedia': 'Wikipedia'},
    'relation_types': {'isPartOf': 'is part of',
                       'references': 'references',
                       'isFormatOf': 'is format of',
                       'isVersionOf': 'is version of',
                       'isReplacedBy': 'is replaced by'},
    'identifier_types': {'isbn': 'ISBN',
                         'issn': 'ISSN',
                         'essn': 'ESSN (ISSN Electronic)',
                         'doi': 'DOI',
                         'url': 'URL',
                         'handle': 'Handle URL',
                         'scopus': 'Scopus',
                         'wos': 'Web of Science'},
    'description_types': {'abstract': 'Abstract',
                          'keywords': 'Keywords',
                          'toc': 'Table of Contents'},
    'description_formats': {'text': 'Plain Text',
                            'markdown': 'Markdown Text',
                            'html': 'HTML'},
    'measure_types': {'cites': 'Citations',
                      'openAccess': 'Open Access',
                      'impactFactor': 'Impact Factor'},
    'position_types': {'academic': 'Academic Side Position',
                       'commercial': 'Commercial Side Position',
                       'government': 'Governmental Side Position',
                       'charitative': 'Charitative Side Position',
                       'honorary': 'Honorary Side Position'},
    'group_account_types': {'email': 'email',
                            'local': 'Local',
                            'wikipedia': 'Wikipedia'},
    'repository_settings': {'title': 'Caleido'}}

class Storage(object):
    schema_version = '0.1'
    def __init__(self, registry):
        self.registry = registry

    def repository_info(self, session):
        revisions = {}
        for repository in session.query(Repository).all():
            revisions[repository.namespace] = repository.to_dict()
        return revisions

    def create_repository(self, session, namespace, vhost_name, settings=None):
        self.registry['engine'].execute(CreateSchema(namespace))
        session.add(Repository(namespace=namespace,
                               schema_version=self.schema_version,
                               vhost_name=vhost_name,
                               settings=settings or DEFAULTS['repository_settings']))
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
        group_types = DEFAULTS['group_types']
        for key, label in group_types.items():
            session.add(GroupType(key=key, label=label))
        person_account_types = DEFAULTS['person_account_types']
        for key, label in person_account_types.items():
            session.add(PersonAccountType(key=key, label=label))
        group_account_types = DEFAULTS['group_account_types']
        for key, label in group_account_types.items():
            session.add(GroupAccountType(key=key, label=label))
        work_types = DEFAULTS['work_types']
        for key, label in work_types.items():
            session.add(WorkType(key=key, label=label))
        contributor_roles = DEFAULTS['contributor_roles']
        for key, label in contributor_roles.items():
            session.add(ContributorRole(key=key, label=label))
        identifier_types = DEFAULTS['identifier_types']
        for key, label in identifier_types.items():
            session.add(IdentifierType(key=key, label=label))
        relation_types = DEFAULTS['relation_types']
        for key, label in relation_types.items():
            session.add(RelationType(key=key, label=label))
        description_types = DEFAULTS['description_types']
        for key, label in description_types.items():
            session.add(DescriptionType(key=key, label=label))
        description_formats = DEFAULTS['description_formats']
        for key, label in description_formats.items():
            session.add(DescriptionFormat(key=key, label=label))
        measure_types = DEFAULTS['measure_types']
        for key, label in measure_types.items():
            session.add(MeasureType(key=key, label=label))
        position_types = DEFAULTS['position_types']
        for key, label in position_types.items():
            session.add(PositionType(key=key, label=label))

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

REPOSITORY_CONFIG = {}

class RepositoryConfig(object):
    orm_table = {'group_type': GroupType,
                 'work_type': WorkType,
                 'contributor_role': ContributorRole,
                 'person_account_type': PersonAccountType,
                 'group_account_type': GroupAccountType,
                 'identifier_type': IdentifierType,
                 'relation_type': RelationType,
                 'description_type': DescriptionType,
                 'description_format': DescriptionFormat,
                 'position_type': PositionType,
                 'measure_type': MeasureType}

    def __init__(self, registry, session, namespace, api_host_url, config_revision=0, settings=None):
        self.registry = registry
        self.session = session
        self.namespace = namespace
        self.api_host_url = api_host_url
        self._blob_store = None
        self.config_revision = config_revision
        self.settings = settings or {}
        if self.config_revision in REPOSITORY_CONFIG.get(self.namespace, {}):
            self.cached_config = REPOSITORY_CONFIG[
                self.namespace][self.config_revision]
        else:
            self.cached_config = {}
            REPOSITORY_CONFIG[self.namespace] = {
                self.config_revision: self.cached_config}

    @reify
    def blob(self):
        backend = self.registry.queryUtility(
            IBlobStoreBackend,
            self.registry.settings['caleido.blob_storage'])
        return BlobStore(backend(self))

    def update_settings(self, settings):
        self.settings = settings
        repo = self.session.query(Repository).filter(
            Repository.namespace == self.namespace).first()
        repo.settings = self.settings
        self.session.add(repo)
        self.session.flush()

    def type_config(self, type):
        if type in self.cached_config:
            values = self.cached_config[type]
        else:
            orm_table = self.orm_table[type]
            values = []
            for setting in self.session.query(orm_table).all():
                values.append({'key': setting.key, 'label': setting.label})
            self.cached_config[type] = values
        return values

    def put_type_config(self, type, values):
        orm_table = self.orm_table[type]
        values = dict((v['key'], v['label']) for v in values)
        for item in self.session.query(orm_table).all():
            if item.key not in values:
                self.session.delete(item)
            else:
                if values[item.key] != item.label:
                    item.label = values[item.key]
                    self.session.add(item)
                del values[item.key]
        for key, label in values.items():
            self.session.add(self.orm(key=key, label=label))
        # update the repository config revision to force cache invalidation
        repo = self.session(Repository).query(
            Repository.namespace==self.namespace).first()
        repo.config_revision = Repository.config_revision + 1
        self.session.add(repo)
        self.session.flush()


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

    engine = engine_from_config(settings, prefix='sqlalchemy.')#, echo=True)

    session_factory = sessionmaker()
    session_factory.configure(bind=engine, autoflush=False)

    config.registry['engine'] = engine
    config.registry['dbsession_factory'] = session_factory

    config.registry['storage'] = Storage(config.registry)

    def new_dbsession(request):
        session = get_tm_session(session_factory, request.tm)
        host = request.headers['Host'].split(':')[0]
        repository = session.query(Repository).filter(Repository.vhost_name == host).first()
        if repository:
            request.environ[
                'caleido.repository.namespace'] = repository.namespace
            request.environ[
                'caleido.repository.config_revision'] = repository.config_revision
            request.environ[
                'caleido.repository.settings'] = repository.settings
            session.execute(
                'SET search_path TO %s, public' % repository.namespace);
        return session

    def new_repository(request):
        session = request.dbsession
        namespace = request.environ['caleido.repository.namespace']
        rev = request.environ['caleido.repository.config_revision']

        repo_settings = request.environ['caleido.repository.settings']

        api_host_url = '%s://%s' % (request.scheme, request.host)
        if request.server_port != 80:
            api_host_url = '%s:%s' % (api_host_url, request.server_port)

        repository = RepositoryConfig(request.registry,
                                      session,
                                      namespace,
                                      api_host_url,
                                      config_revision=rev,
                                      settings=repo_settings)
        return repository

    config.add_request_method(new_dbsession, 'new_dbsession')
    # make request.dbsession available for use in Pyramid
    config.add_request_method(
        new_dbsession,
        'dbsession',
        reify=True
        )
    config.add_request_method(
        new_repository,
        'repository',
        reify=True
        )
