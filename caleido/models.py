import datetime
from intervals import DateInterval

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

from caleido.utils import parse_duration

class WorkType(Base):
    __tablename__ = 'work_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))



class UserGroup(Base):
    __tablename__ = 'user_groups'
    id = Column(Integer(), primary_key=True)
    label = Column(Unicode(128))



class ContributorRole(Base):
    __tablename__ = 'contributor_role_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class RelationType(Base):
    __tablename__ = 'relation_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class Relation(Base):
    """
    isPartOf
    isFormatOf
    isReplacedBy
    isVersionOf
    """


    __tablename__ = 'relations'
    id = Column(Integer, Sequence('relations_id_seq'), primary_key=True)
    work_id = Column(Integer,
                     ForeignKey('works.id'),
                     index=True)
    work = relationship('Work',
                        foreign_keys=[work_id],
                        back_populates='relations')
    target_id = Column(Integer,
                       ForeignKey('works.id'),
                       index=True,
                       nullable=False)
    target = relationship('Work',
                          foreign_keys=[target_id])
    type = Column(Unicode(32),
                  ForeignKey('relation_type_schemes.key'),
                  index=True,
                  nullable=False)

    location = Column(Unicode(1024), nullable=True)
    starting = Column(Unicode(128), nullable=True)
    ending = Column(Unicode(128), nullable=True)
    total = Column(Unicode(128), nullable=True)
    volume = Column(Unicode(128), nullable=True)
    issue = Column(Unicode(128), nullable=True)
    number = Column(Unicode(128), nullable=True)
    during = Column(DateRangeType, nullable=True)
    position = Column(Integer, nullable=False)

    def to_dict(self):
        start_date = end_date = None
        if self.during:
            start_date, end_date = parse_duration(self.during)

        result = {'id': self.id,
                  'type': self.type,
                  'work_id': self.work_id,
                  '_work_name': self.work.title,
                  'target_id': self.target_id,
                  '_target_name': self.target.title,
                  '_target_type': self.target.type,
                  'location': self.location,
                  'starting': self.starting,
                  'ending': self.ending,
                  'total': self.total,
                  'volume': self.volume,
                  'issue': self.issue,
                  'number': self.number,
                  'start_date': start_date,
                  'end_date': end_date,
                  'position': self.position}
        return result

    def update_dict(self, data):
        start_date = data.pop('start_date', None)
        end_date = data.pop('end_date', None)
        set_attribute(self, 'during', DateInterval([start_date, end_date]))

        for key, value in data.items():
            if key.startswith('_'):
                continue
            set_attribute(self, key, value)

    @classmethod
    def from_dict(cls, data):
        relation = Relation()
        relation.update_dict(data)
        return relation


class DescriptionType(Base):
    __tablename__ = 'description_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class DescriptionFormat(Base):
    __tablename__ = 'description_format_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class Description(Base):
    __tablename__ = 'descriptions'

    id = Column(Integer, Sequence('descriptions_id_seq'), primary_key=True)
    work_id = Column(Integer,
                     ForeignKey('works.id'),
                     index=True,
                     nullable=False)
    work = relationship('Work',
                        foreign_keys=[work_id],
                        back_populates='descriptions')
    target_id = Column(Integer,
                       ForeignKey('works.id'),
                       nullable=True)
    type = Column(Unicode(32),
                  ForeignKey('description_type_schemes.key'),
                  nullable=False)
    format = Column(Unicode(32),
                  ForeignKey('description_format_schemes.key'),
                  nullable=False)
    value = Column(UnicodeText, nullable=False)
    position = Column(Integer)

    def to_dict(self):
        if self.target_id is None:
            target_name = None
        else:
            target_name = self.target.title

        result = {'id': self.id,
                  'type': self.type,
                  'format': self.format,
                  'value': self.value,
                  'work_id': self.work_id,
                  '_work_name': self.work.title,
                  'target_id': self.target_id,
                  '_target_name': target_name,
                  'position': self.position}

        return result

    def update_dict(self, data):
        for key, value in data.items():
            if key.startswith('_'):
                continue
            set_attribute(self, key, value)

    @classmethod
    def from_dict(cls, data):
        description = Description()
        description.update_dict(data)
        return description


class Work(Base):
    __tablename__ = 'works'
    id = Column(Integer, Sequence('works_id_seq'), primary_key=True)
    type = Column(Unicode(32),
                  ForeignKey('work_type_schemes.key'),
                  index=True,
                  nullable=False)
    title = Column(UnicodeText, nullable=False)
    issued = Column(Date, nullable=False)
    during = Column(DateRangeType, nullable=False)

    descriptions = relationship('Description',
                                back_populates='work',
                                foreign_keys=[Description.work_id],
                                order_by='Description.position',
                                collection_class=ordering_list('position'),
                                cascade='all, delete-orphan')
    identifiers = relationship('Identifier',
                               back_populates='work',
                               cascade='all, delete-orphan')
    measures = relationship('Measure',
                            back_populates='work',
                            cascade='all, delete-orphan')
    expressions = relationship('Expression',
                            back_populates='work',
                            cascade='all, delete-orphan')

    contributors = relationship('Contributor',
                                back_populates='work',
                                order_by='Contributor.position',
                                collection_class=ordering_list('position'),
                                cascade='all, delete-orphan')

    affiliations = relationship('Affiliation', back_populates='work')

    relations = relationship('Relation',
                             back_populates='work',
                             foreign_keys=[Relation.work_id],
                             order_by='Relation.position',
                             collection_class=ordering_list('position'),
                             cascade='all, delete-orphan')

    def to_dict(self):
        start_date = end_date = None
        if self.during:
            start_date, end_date = parse_duration(self.during)

        result = {'id': self.id,
                  'type': self.type,
                  'title': self.title,
                  'issued': self.issued,
                  'start_date': start_date,
                  'end_date': end_date}

        result['identifiers'] = [{'type': a.type, 'value': a.value}
                                 for a in self.identifiers]
        result['measures'] = [{'type': a.type, 'value': a.value}
                              for a in self.measures]

        result['contributors'] = []
        for contributor in self.contributors:
            contributor = contributor.to_dict()
            result['contributors'].append(
                {'person_id': contributor['person_id'],
                 'id': contributor['id'],
                 '_person_name': contributor['_person_name'],
                 'role': contributor['role'],
                 'location': contributor['location'],
                 'start_date': contributor['start_date'],
                 'end_date': contributor['end_date'],
                 'position': contributor['position'],
                 'affiliations': [{'group_id': a['group_id'],
                                   '_group_name': a['_group_name'],
                                   'id': a['id'],
                                   'position': a['position']}for a in
                                  contributor['affiliations']]})

        result['descriptions'] = []
        for description in self.descriptions:
            description = description.to_dict()
            result['descriptions'].append(
                {'id': description['id'],
                 'target_id': description['target_id'],
                 '_target_name': description['_target_name'],
                 'type': description['type'],
                 'value': description['value'],
                 'format': description['format'],
                 'position': description['position']})

        result['relations'] = []
        for relation in self.relations:
            relation = relation.to_dict()
            result['relations'].append(
                {'id': relation['id'],
                 'target_id': relation['target_id'],
                 '_target_name': relation['_target_name'],
                 '_target_type': relation['_target_type'],
                 'type': relation['type'],
                 'location': relation['location'],
                 'start_date': relation['start_date'],
                 'end_date': relation['end_date'],
                 'starting': relation['starting'],
                 'ending': relation['ending'],
                 'total': relation['total'],
                 'volume': relation['volume'],
                 'issue': relation['issue'],
                 'number': relation['number'],
                 'position': relation['position']})

        return result


    def update_dict(self, data):
        start_date = data.pop('start_date', None)
        end_date = data.pop('end_date', None)
        issued = data['issued']
        set_attribute(self, 'during', DateInterval([start_date, end_date]))
        if start_date is None and end_date is None:
            set_attribute(self, 'during', DateInterval([issued, issued]))

        if 'identifiers' in data:
            new_values = set([(a['type'], a['value'])
                              for a in data.pop('identifiers', [])])
            for value in self.identifiers:
                key = (value.type, value.value)
                if key in new_values:
                    new_values.remove(key)
                else:
                    self.identifiers.remove(value)
            for new_value in new_values:
                type, value = new_value
                self.identifiers.append(Identifier(type=type,
                                                   value=value,
                                                   work_id=data.get('id')))
        if 'measures' in data:
            new_values = set([(a['type'], a['value'])
                              for a in data.pop('measures', [])])
            for value in self.measures:
                key = (value.type, value.value)
                if key in new_values:
                    new_values.remove(key)
                else:
                    self.measures.remove(value)
            for new_value in new_values:
                type, value = new_value
                self.measures.append(Measure(type=type,
                                             value=value,
                                             work_id=data.get('id')))

        if 'contributors' in data:
            existing_contributors = dict([(c.id, c) for c in self.contributors])
            new_contributors = []
            for contributor_data in data.pop('contributors', []):
                contributor_data['work_id'] = self.id
                affiliations_data = contributor_data.pop('affiliations', [])
                if contributor_data.get('id') in existing_contributors:
                    contributor = existing_contributors.pop(contributor_data['id'])
                    contributor.update_dict(contributor_data)

                else:
                    contributor = Contributor.from_dict(contributor_data)

                existing_affiliations = dict([(c.id, c) for c in contributor.affiliations])
                new_affiliations = []
                for affiliation_data in affiliations_data:
                    affiliation_data['work_id'] = self.id
                    if affiliation_data.get('id') in existing_affiliations:
                        affiliation = existing_affiliations.pop(
                            affiliation_data['id'])
                        affiliation.update_dict(affiliation_data)
                    else:
                        affiliation = Affiliation.from_dict(affiliation_data)
                    new_affiliations.append(affiliation)
                contributor.affiliations[:] = new_affiliations

                new_contributors.append(contributor)
            self.contributors[:] = new_contributors

        if 'descriptions' in data:
            existing_descriptions = dict([(c.id, c) for c in self.descriptions])
            new_descriptions = []
            for description_data in data.pop('descriptions', []):
                description_data['work_id'] = self.id
                if description_data.get('id') in existing_descriptions:
                    description = existing_descriptions.pop(description_data['id'])
                    description.update_dict(description_data)
                else:
                    description = Description.from_dict(description_data)
                new_descriptions.append(description)
            self.descriptions[:] = new_descriptions

        if 'relations' in data:
            existing_relations = dict([(c.id, c) for c in self.relations])
            new_relations = []
            for relation_data in data.pop('relations', []):
                relation_data['work_id'] = self.id
                if relation_data.get('id') in existing_relations:
                    relation = existing_relations.pop(relation_data['id'])
                    relation.update_dict(relation_data)
                else:
                    relation = Relation.from_dict(relation_data)
                new_relations.append(relation)
            self.relations[:] = new_relations


        for key, value in data.items():
            if key.startswith('_'):
                continue
            set_attribute(self, key, value)


    @classmethod
    def from_dict(cls, data):
        work = Work()
        work.update_dict(data)
        return work


class Person(Base):
    __tablename__ = 'persons'

    id = Column(Integer, Sequence('person_id_seq'), primary_key=True)
    name = Column(Unicode(128), nullable=False)
    family_name = Column(Unicode(128))
    given_name = Column(Unicode(128))
    initials = Column(Unicode(32))
    family_name_prefix = Column(Unicode(64))
    honorary = Column(Unicode(64))
    alternative_name = Column(UnicodeText)

    owners = relationship('Owner', back_populates='person')
    memberships = relationship('Membership',
                               back_populates='person',
                               cascade='all, delete-orphan')
    accounts = relationship('PersonAccount',
                            back_populates='person',
                            cascade='all, delete-orphan')
    contributors = relationship('Contributor',
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
        result['memberships'] = []
        for membership in self.memberships:
            membership = membership.to_dict()
            result['memberships'].append(
                {'group_id': membership['group_id'],
                 '_group_name': membership['_group_name'],
                 'start_date': membership['start_date'],
                 'end_date': membership['end_date']})

        return result

    def update_dict(self, data):
        if 'accounts' in data:
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
        if 'memberships' in data:
            # only update memberships if key is present
            new_memberships = set([(m['group_id'],
                                    m.get('start_date'),
                                    m.get('end_date'))
                                   for m in data.pop('memberships', [])])
            for membership in self.memberships:
                membership_dict = membership.to_dict()
                key = (membership_dict['group_id'],
                       membership_dict.get('start_date'),
                       membership_dict.get('end_date'))
                if key in new_memberships:
                    new_memberships.remove(key)
                else:
                    self.memberships.remove(membership)
            for new_membership in new_memberships:
                group_id, start_date, end_date = new_membership
                self.memberships.append(
                    Membership.from_dict(dict(group_id=group_id,
                                              person_id=data.get('id'),
                                              start_date=start_date,
                                              end_date=end_date)))
        for key, value in data.items():
            set_attribute(self, key, value)

    @classmethod
    def from_dict(cls, data):
        person = Person()
        person.update_dict(data)
        return person


class IdentifierType(Base):
    __tablename__ = 'identifier_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class Identifier(Base):
    __tablename__ = 'identifiers'
    #__table_args__ = (
    #    UniqueConstraint('type', 'value'),)


    id = Column(Integer, Sequence('identifiers_id_seq'), primary_key=True)
    work_id = Column(Integer,
                      ForeignKey('works.id'),
                      index=True,
                      nullable=False)
    work = relationship('Work', back_populates='identifiers')
    type = Column(Unicode(32),
                  ForeignKey('identifier_type_schemes.key'),
                  nullable=False)
    value = Column(Unicode(1024), nullable=False)

class ConceptType(Base):
    __tablename__ = 'concept_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class Concept(Base):
    __tablename__ = 'concepts'

    id = Column(Integer, Sequence('concepts_id_seq'), primary_key=True)

    parent_id = Column(Integer,
                      ForeignKey('concepts.id'),
                      index=True,
                      nullable=True)

    parent = relationship('Concept', remote_side=[id], lazy='joined')

    type = Column(Unicode(32),
                    ForeignKey('concept_type_schemes.key'),
                    nullable=False)
    label = Column(Unicode(1024), nullable=False)
    notation = Column(Unicode(128), nullable=False)



class MeasureType(Base):
    __tablename__ = 'measure_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class MeasureUnit(Base):
    __tablename__ = 'measure_unit_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class Measure(Base):
    __tablename__ = 'measures'

    id = Column(Integer, Sequence('measures_id_seq'), primary_key=True)
    work_id = Column(Integer,
                      ForeignKey('works.id'),
                      index=True,
                      nullable=False)
    work = relationship('Work', back_populates='measures')
    type = Column(Unicode(32),
                  ForeignKey('measure_type_schemes.key'),
                  nullable=False)
    unit = Column(Unicode(32),
                  ForeignKey('measure_unit_schemes.key'),
                  nullable=True)
    during = Column(DateRangeType)
    value = Column(Unicode(128), nullable=False)


class ExpressionType(Base):
    __tablename__ = 'expression_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class ExpressionFormat(Base):
    __tablename__ = 'expression_format_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class ExpressionAccessRight(Base):
    __tablename__ = 'expression_access_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))


class ExpressionMeasureType(Base):
    __tablename__ = 'expression_measure_type_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class ExpressionMeasureUnit(Base):
    __tablename__ = 'expression_measure_unit_schemes'
    key = Column(Unicode(32), primary_key=True)
    label = Column(Unicode(128))

class ExpressionMeasure(Base):
    __tablename__ = 'expression_measures'

    id = Column(Integer, Sequence('expression_measures_id_seq'), primary_key=True)
    expression_id = Column(Integer,
                      ForeignKey('expressions.id'),
                      index=True,
                      nullable=False)
    expression = relationship('Expression', back_populates='measures')
    type = Column(Unicode(32),
                  ForeignKey('expression_measure_type_schemes.key'),
                  nullable=False)
    unit = Column(Unicode(32),
                  ForeignKey('expression_measure_unit_schemes.key'),
                  nullable=False)
    value = Column(Unicode(128), nullable=False)

class Expression(Base):
    __tablename__ = 'expressions'

    id = Column(Integer, Sequence('expressions_id_seq'), primary_key=True)
    work_id = Column(Integer,
                      ForeignKey('works.id'),
                      index=True,
                      nullable=False)
    work = relationship('Work', back_populates='expressions')
    type = Column(Unicode(32),
                  ForeignKey('expression_type_schemes.key'),
                  nullable=False)
    format = Column(Unicode(32),
                  ForeignKey('expression_format_schemes.key'),
                  nullable=False)
    access = Column(Unicode(32),
                  ForeignKey('expression_access_schemes.key'),
                  nullable=False)
    measures = relationship('ExpressionMeasure',
                            back_populates='expression',
                            cascade='all, delete-orphan')
    during = Column(DateRangeType)
    name = Column(Unicode(128), nullable=False)
    blob_key = Column(Unicode(1024), nullable=False)
    uri = Column(Unicode(1024), nullable=False)



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

    parent_id = Column(Integer,
                      ForeignKey('groups.id'),
                      index=True,
                      nullable=True)

    parent = relationship('Group', remote_side=[id], lazy='joined')

    members = relationship('Membership', back_populates='group')
    owners = relationship('Owner', back_populates='group')
    affiliations = relationship('Affiliation', back_populates='group')
    accounts = relationship('GroupAccount',
                            back_populates='group',
                            cascade='all, delete-orphan')


    def to_dict(self):
        result = {}
        for prop in instance_dict(self):
            if prop.startswith('_'):
                continue
            result[prop] = getattr(self, prop)
        if self.parent_id:
            result['_parent_name'] = self.parent.name

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
            if key.startswith('_'):
                continue
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
            owner_data = owner.to_dict()
            if owner.person_id:
                result.setdefault('owns', []).append(
                    {'person_id': owner.person_id,
                     '_person_name': owner_data['_person_name']})
            elif owner.group_id:
                result.setdefault('owns', []).append(
                    {'group_id': owner.group_id,
                     '_group_name': owner_data['_group_name']})
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
    person = relationship('Person', back_populates='owners')
    group_id = Column(Integer,
                      ForeignKey('groups.id'),
                      index=True)
    group = relationship('Group', back_populates='owners')

    def to_dict(self):
        result = {'id': self.id,
                  'user_id': self.user_id}
        if self.person_id:
            result['person_id'] = self.person_id
            result['_person_name'] = self.person.name
        elif self.group_id:
            result['group_id'] = self.group_id
            result['_group_name'] = self.group.name
        return result

class Membership(Base):
    __tablename__ = 'memberships'
    id = Column(Integer, Sequence('memberships_id_seq'), primary_key=True)
    person_id = Column(Integer,
                       ForeignKey('persons.id'),
                       index=True,
                       nullable=False)
    person = relationship('Person', back_populates='memberships', lazy='joined')

    group_id = Column(Integer,
                      ForeignKey('groups.id'),
                      index=True,
                      nullable=False)
    group = relationship('Group', back_populates='members', lazy='joined')

    during = Column(DateRangeType)
    provenance = Column(Unicode(1024))


    def to_dict(self):
        start_date = end_date = None
        if self.during:
            start_date, end_date = parse_duration(self.during)

        result = {'id': self.id,
                  'person_id': self.person_id,
                  '_person_name': self.person.name,
                  'group_id': self.group_id,
                  '_group_name': self.group.name,
                  'start_date': start_date,
                  'end_date': end_date,
                  'provenance': self.provenance}
        return result

    def update_dict(self, data):

        start_date = data.pop('start_date', None)
        end_date = data.pop('end_date', None)
        set_attribute(self, 'during', DateInterval([start_date, end_date]))
        for key, value in data.items():
            set_attribute(self, key, value)

    @classmethod
    def from_dict(cls, data):
        membership = Membership()
        membership.update_dict(data)
        return membership


class Contributor(Base):
    "An Actor that made a specific contribution to a work"
    __tablename__ = 'contributors'
    __table_args__ = (
        CheckConstraint('NOT(person_id IS NULL AND group_id IS NULL)'),
        )
    id = Column(Integer, Sequence('contributors_id_seq'), primary_key=True)
    role = Column(Unicode(32),
                  ForeignKey('contributor_role_schemes.key'),
                  index=True,
                  nullable=False)
    work_id = Column(Integer, ForeignKey('works.id'), index=True, nullable=False)
    work = relationship('Work', back_populates='contributors', lazy='joined')

    person_id = Column(Integer, ForeignKey('persons.id'), index=True, nullable=True)
    person = relationship('Person', lazy='joined')

    group_id = Column(Integer, ForeignKey('groups.id'), index=True, nullable=True)
    group = relationship('Group', lazy='joined')

    during = Column(DateRangeType, nullable=True)
    location = Column(Unicode(1024), nullable=True)

    position = Column(Integer)

    affiliations = relationship('Affiliation',
                                back_populates='contributor',
                                lazy='joined')


    def to_dict(self):
        start_date = end_date = None
        if self.during:
            start_date, end_date = parse_duration(self.during)

        if self.person is None:
            person_name = None
        else:
            person_name = self.person.name
        if self.group is None:
            group_name = None
        else:
            group_name = self.group.name

        result = {'id': self.id,
                  'role': self.role,
                  'work_id': self.work_id,
                  '_work_name': self.work.title,
                  'person_id': self.person_id,
                  '_person_name': person_name,
                  'group_id': self.group_id,
                  '_group_name': group_name,
                  'start_date': start_date,
                  'end_date': end_date,
                  'location': self.location,
                  'position': self.position}

        result['affiliations'] = []
        for affiliation in self.affiliations:
            result['affiliations'].append(affiliation.to_dict())

        return result

    def update_dict(self, data):

        start_date = data.pop('start_date', None)
        end_date = data.pop('end_date', None)
        set_attribute(self, 'during', DateInterval([start_date, end_date]))

        for key, value in data.items():
            if key.startswith('_'):
                continue
            set_attribute(self, key, value)

    @classmethod
    def from_dict(cls, data):
        contributor = Contributor()
        contributor.update_dict(data)
        return contributor

class Affiliation(Base):
    __tablename__ = 'affiliations'

    id = Column(Integer, Sequence('affiliations_id_seq'), primary_key=True)

    work_id = Column(Integer, ForeignKey('works.id'), index=True, nullable=False)
    work = relationship('Work', back_populates='affiliations', lazy='joined')

    contributor_id = Column(Integer,
                            ForeignKey('contributors.id'),
                            index=True, nullable=True)
    contributor = relationship('Contributor',
                               back_populates='affiliations')

    group_id = Column(Integer, ForeignKey('groups.id'), index=True, nullable=True)
    group = relationship('Group', back_populates='affiliations', lazy='joined')

    position = Column(Integer)

    def to_dict(self):
        result = {'id': self.id,
                  'work_id': self.work_id,
                  'contributor_id': self.contributor_id,
                  'group_id': self.group_id,
                  '_group_name': self.group.name,
                  'position': self.position}
        return result

    def update_dict(self, data):

        for key, value in data.items():
            if key.startswith('_'):
               continue
            set_attribute(self, key, value)

    @classmethod
    def from_dict(cls, data):
        affiliation = Affiliation()
        affiliation.update_dict(data)
        return affiliation



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
