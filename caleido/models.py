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
    international_name = Column(Unicode(128))
    native_name = Column(Unicode(128))
    abbreviated_name = Column(Unicode(64))
    family_name = Column(Unicode(64))
    given_name = Column(Unicode(64))
    initials = Column(Unicode(32))
    family_name_prefix = Column(Unicode(64))
    family_name_suffix = Column(Unicode(64))

    memberships = relationship('Membership', back_populates='actor')
    accounts = relationship('Account', back_populates='actor')


class Account(Base):
    __tablename__ = 'accounts'

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


    def to_dict(self):
        return {'id': self.id,
                'user_group': self.user_group,
                'userid': self.userid,
                'credentials': self.credentials.hash.decode('utf8')}

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class Owner(Base):
    __tablename__ = 'owners'
    id = Column(Integer, Sequence('owners_id_seq'), primary_key=True)
    actor_id = Column(Integer,
                      ForeignKey('actors.id'),
                      index=True,
                      nullable=False)
    userid = Column(Unicode(128), index=True, nullable=False)


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
