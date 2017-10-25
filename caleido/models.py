from sqlalchemy import (
    Column,
    Integer,
    Unicode,
    UnicodeText,
    Date,
    Sequence,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint
    )
from sqlalchemy.orm import relationship, configure_mappers
from sqlalchemy.orm.attributes import instance_dict
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import DateRangeType, LtreeType, PasswordType
from sqlalchemy.orm.attributes import set_attribute
Base = declarative_base()

class Kind(Base):
    __tablename__ = 'kind_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))


class WorkType(Base):
    __tablename__ = 'work_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    kind = Column(Unicode(32),
                  ForeignKey('kind_schemes.key'),
                  nullable=False,
                  primary_key=True)
    label = Column(Unicode(128))


class ActorType(Base):
    __tablename__ = 'actor_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))


class UserGroup(Base):
    __tablename__ = 'user_groups'
    id = Column(Integer(), primary_key=True)
    label = Column(Unicode(128))


class AccountType(Base):
    __tablename__ = 'account_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))


class ContributorRole(Base):
    __tablename__ = 'contributor_role_schemes'
    key = Column(Unicode(32), primary_key=True)
    kind = Column(Unicode(32),
                  ForeignKey('kind_schemes.key'),
                  nullable=False,
                  primary_key=True)
    label = Column(Unicode(128))


class Work(Base):
    __tablename__ = 'works'
    __table_args__ = (
        ForeignKeyConstraint(['type', 'kind'],
                             ['work_type_schemes.key',
                              'work_type_schemes.kind']),
        )
    id = Column(Integer, Sequence('works_id_seq'), primary_key=True)
    kind = Column(Unicode(32),
                  ForeignKey('kind_schemes.key'),
                  nullable=False)
    type = Column(Unicode(32),
                  nullable=False)
    title = Column(UnicodeText, nullable=False)
    date = Column(Date, nullable=False)
    during = Column(DateRangeType, nullable=False)
    contributors = relationship('Contributor',
                                back_populates='work',
                                order_by='Contributor.position',
                                collection_class=ordering_list('position'))



class Actor(Base):
    __tablename__ = 'actors'

    id = Column(Integer, Sequence('works_id_seq'), primary_key=True)
    type = Column(Unicode(32),
                  ForeignKey('actor_type_schemes.key'),
                  nullable=False)
    name = Column(Unicode(128), nullable=False)
    corporate_international_name = Column(Unicode(256))
    corporate_native_name = Column(Unicode(256))
    corporate_abbreviated_name = Column(Unicode(128))
    family_name = Column(Unicode(128))
    given_name = Column(Unicode(128))
    initials = Column(Unicode(32))
    family_name_prefix = Column(Unicode(64))
    family_name_suffix = Column(Unicode(64))

    memberships = relationship('Membership', back_populates='actor')
    accounts = relationship('Account',
                            back_populates='actor',
                            cascade='all, delete-orphan')

    def to_dict(self):
        result = {}
        for prop in instance_dict(self):
            if prop.startswith('_'):
                continue
            result[prop] = getattr(self, prop)

        result['accounts'] = [{'type': a.type, 'value': a.value}
                              for a in self.accounts]

        return result

    def update_dict(self, data):
        if data.get('accounts') is not None:
            new_accounts = set([(a['type'], a['value'])
                                for a in data.pop('accounts', [])])
            for account in self.accounts:
                key = (account.type, account.value)
                if key in new_accounts:
                    new_accounts.remove(key)
                else:
                    self.accounts.remove(account)
            for new_account in new_accounts:
                type, value = new_account
                self.accounts.append(Account(type=type,
                                             value=value,
                                             actor_id=data.get('id')))

        for key, value in data.items():
            set_attribute(self, key, value)

    @classmethod
    def from_dict(cls, data):
        actor = Actor()
        actor.update_dict(data)
        return actor

class Account(Base):
    __tablename__ = 'accounts'
    __table_args__ = (
        UniqueConstraint('type', 'value'),)


    id = Column(Integer, Sequence('accounts_id_seq'), primary_key=True)
    actor_id = Column(Integer,
                      ForeignKey('actors.id'),
                      index=True,
                      nullable=False)
    actor = relationship('Actor', back_populates='accounts')
    type = Column(Unicode(32),
                  ForeignKey('account_type_schemes.key'),
                  nullable=False)
    value = Column(Unicode(128), nullable=False)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('users_id_seq'), primary_key=True)
    user_group = Column(Integer(),
                        ForeignKey('user_groups.id'),
                        nullable=False)
    userid = Column(Unicode(128), index=True, nullable=False)
    credentials = Column(PasswordType(schemes=['pbkdf2_sha512']),
                         nullable=False)

    owns = relationship('Owner',
                        back_populates='user',
                        cascade='all, delete-orphan',
                        lazy='joined')

    def to_dict(self):
        result = {'id': self.id,
                  'user_group': self.user_group,
                  'userid': self.userid,
                  'credentials': self.credentials.hash.decode('utf8')}
        result['owns'] = [{'actor_id': o.actor_id} for o in self.owns]
        return result


    def update_dict(self, data):
        if data.get('owns') is not None:
            new_owns = set([a['actor_id'] for a in data.pop('owns', [])])
            for owner in self.owns:
                key = owner.actor_id
                if key in new_owns:
                    new_owns.remove(key)
                else:
                    self.owns.remove(owner)
            for actor_id in new_owns:
                self.owns.append(Owner(actor_id=actor_id,
                                       user_id=data.get('id')))
        for key, value in data.items():
            set_attribute(self, key, value)

    @classmethod
    def from_dict(cls, data):
        user = User()
        user.update_dict(data)
        return user


class Owner(Base):
    __tablename__ = 'owners'
    id = Column(Integer, Sequence('owners_id_seq'), primary_key=True)
    user_id = Column(Integer,
                     ForeignKey('users.id'),
                     index=True,
                     nullable=False)
    user = relationship('User', back_populates='owns')
    actor_id = Column(Integer,
                      ForeignKey('actors.id'),
                      index=True,
                      nullable=False)


class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, ForeignKey('actors.id'), primary_key=True)
    path = Column(LtreeType, nullable=False)


class Membership(Base):
    __tablename__ = 'memberships'
    id = Column(Integer, Sequence('memberships_id_seq'), primary_key=True)
    actor_id = Column(Integer, ForeignKey('actors.id'), index=True, nullable=False)
    actor = relationship('Actor', back_populates='memberships')

    group_id = Column(Integer, ForeignKey('groups.id'), index=True, nullable=False)
    during = Column(DateRangeType)


class Contributor(Base):
    "An Actor that made a specific contribution to a work"
    __tablename__ = 'contributors'
    __table_args__ = (
        ForeignKeyConstraint(['role', 'kind'],
                             ['contributor_role_schemes.key',
                              'contributor_role_schemes.kind']),
        )
    id = Column(Integer, Sequence('contributors_id_seq'), primary_key=True)
    kind = Column(Unicode(32),
                  ForeignKey('kind_schemes.key'),
                  nullable=False)
    role = Column(Unicode(32),
                  nullable=False)
    during = Column(DateRangeType, nullable=True)
    work_id = Column(Integer, ForeignKey('works.id'), index=True, nullable=False)
    work = relationship('Work', back_populates='contributors')

    actor_id = Column(Integer, ForeignKey('actors.id'), index=True, nullable=False)
    position = Column(Integer)

class Repository(Base):
    __tablename__ = 'repositories'
    namespace = Column(Unicode(32), primary_key=True)
    vhost_name = Column(Unicode(128), nullable=False, unique=True)
    config_revision = Column(Integer, nullable=False)
    schema_version = Column(Unicode(32), nullable=False)

    __mapper_args__ = {
        'version_id_col': config_revision
        }

    def to_dict(self):
        return instance_dict(self)

configure_mappers()
