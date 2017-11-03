from sqlalchemy import (
    Column,
    Integer,
    Unicode,
    UnicodeText,
    Date,
    Sequence,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    CheckConstraint
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



class UserGroup(Base):
    __tablename__ = 'user_groups'
    id = Column(Integer(), primary_key=True)
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


class Person(Base):
    __tablename__ = 'persons'

    id = Column(Integer, Sequence('person_id_seq'), primary_key=True)
    name = Column(Unicode(128), nullable=False)
    family_name = Column(Unicode(128))
    given_name = Column(Unicode(128))
    initials = Column(Unicode(32))
    family_name_prefix = Column(Unicode(64))
    honorary = Column(Unicode(64))

    memberships = relationship('Membership', back_populates='person')
    accounts = relationship('PersonAccount',
                            back_populates='person',
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
                self.accounts.append(PersonAccount(type=type,
                                                   value=value,
                                                   person_id=data.get('id')))

        for key, value in data.items():
            set_attribute(self, key, value)

    @classmethod
    def from_dict(cls, data):
        person = Person()
        person.update_dict(data)
        return person

class PersonAccountType(Base):
    __tablename__ = 'person_account_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class PersonAccount(Base):
    __tablename__ = 'person_accounts'
    __table_args__ = (
        UniqueConstraint('type', 'value'),)


    id = Column(Integer, Sequence('person_accounts_id_seq'), primary_key=True)
    person_id = Column(Integer,
                      ForeignKey('persons.id'),
                      index=True,
                      nullable=False)
    person = relationship('Person', back_populates='accounts')
    type = Column(Unicode(32),
                  ForeignKey('person_account_type_schemes.key'),
                  nullable=False)
    value = Column(Unicode(128), nullable=False)


class GroupType(Base):
    __tablename__ = 'group_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class GroupAccountType(Base):
    __tablename__ = 'group_account_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class GroupAccount(Base):
    __tablename__ = 'group_accounts'
    __table_args__ = (
        UniqueConstraint('type', 'value'),)


    id = Column(Integer, Sequence('group_accounts_id_seq'), primary_key=True)
    group_id = Column(Integer,
                      ForeignKey('groups.id'),
                      index=True,
                      nullable=False)
    group = relationship('Group', back_populates='accounts')
    type = Column(Unicode(32),
                  ForeignKey('group_account_type_schemes.key'),
                  nullable=False)
    value = Column(Unicode(128), nullable=False)

class Group(Base):
    __tablename__ = 'groups'

    id = Column(Integer, Sequence('group_id_seq'), primary_key=True)
    type = Column(Unicode(32),
                  ForeignKey('group_type_schemes.key'),
                  nullable=False)
    name = Column(Unicode(256), nullable=False)
    international_name = Column(Unicode(256))
    native_name = Column(Unicode(256))
    abbreviated_name = Column(Unicode(128))

    members = relationship('Membership', back_populates='group')
    accounts = relationship('GroupAccount',
                            back_populates='group',
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
                self.accounts.append(GroupAccount(type=type,
                                                  value=value,
                                                  group_id=data.get('id')))

        for key, value in data.items():
            set_attribute(self, key, value)

    @classmethod
    def from_dict(cls, data):
        group = Group()
        group.update_dict(data)
        return group


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
        for owner in self.owns:
            if owner.person_id:
                result.setdefault('owns', []).append(
                    {'person_id': owner.person_id})
            elif owner.group_id:
                result.setdefault('owns', []).append(
                    {'group_id': owner.group_id})
        return result


    def update_dict(self, data):
        if data.get('owns') is not None:
            owns = data.pop('owns', [])
            owned_person_ids = {
                o['person_id'] for o in owns if o.get('person_id')}
            owned_group_ids = {
                o['group_id'] for o in owns if o.get('group_id')}
            for owner in self.owns:
                if owner.person_id and owner.person_id in owned_person_ids:
                    owned_person_ids.remove(owner.person_id)
                elif owner.group_id and owner.group_id in owned_group_ids:
                    owned_group_ids.remove(owner.group_id)
                else:
                    self.owns.remove(owner)
            for person_id in owned_person_ids:
                self.owns.append(Owner(person_id=person_id,
                                       user_id=data.get('id')))
            for group_id in owned_group_ids:
                self.owns.append(Owner(group_id=group_id,
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
    __table_args__ = (
        CheckConstraint('NOT(person_id IS NULL AND group_id IS NULL)',
                        name='owner_check_person_or_group_id_required'),
                        )
    id = Column(Integer, Sequence('owners_id_seq'), primary_key=True)
    user_id = Column(Integer,
                     ForeignKey('users.id'),
                     index=True,
                     nullable=False)
    user = relationship('User', back_populates='owns')
    person_id = Column(Integer,
                       ForeignKey('persons.id'),
                       index=True)
    group_id = Column(Integer,
                      ForeignKey('groups.id'),
                      index=True)


class Membership(Base):
    __tablename__ = 'memberships'
    id = Column(Integer, Sequence('memberships_id_seq'), primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.id'), index=True, nullable=False)
    person = relationship('Person', back_populates='memberships')

    group_id = Column(Integer, ForeignKey('groups.id'), index=True, nullable=False)
    group = relationship('Group', back_populates='members')

    during = Column(DateRangeType)
    provenance = Column(Unicode(1024))


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

    person_id = Column(Integer, ForeignKey('persons.id'), index=True, nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id'), index=True, nullable=False)
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
