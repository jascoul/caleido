import math

import sqlalchemy as sql
from pyramid.httpexceptions import HTTPForbidden
from pyramid.security import Allow, ALL_PERMISSIONS
from pyramid.interfaces import IAuthorizationPolicy
from sqlalchemy_utils.functions import get_primary_keys
from sqlalchemy.orm import load_only, Load
from sqlalchemy import func
import sqlalchemy.exc
import transaction

from caleido.models import (
    User, Person, Group, GroupType, GroupAccountType, PersonAccountType,
    Membership)
from caleido.exceptions import StorageError

class ResourceFactory(object):
    def __init__(self, resource_class):
        self._class = resource_class

    def __call__(self, request, key=None):
        key = key or request.matchdict.get('id')
        resource = self._class(request.registry,
                               request.dbsession,
                               key)
        if key and resource.model is None:
            request.errors.status = 404
            request.errors.add('path', 'id', 'The resource id does not exist')
            raise HTTPForbidden()
        return resource

class BaseResource(object):
    orm_class = None
    key_col_name = None


    def __init__(self, registry, session, key=None, model=None):
        self.session = session
        self.registry = registry
        if model:
            self.model = model
        elif key:
            self.model = self.get(key)
        else:
            self.model = None

    def __acl__(self):
        return []


    def get(self, key=None, principals=None):
        if key is None:
            if principals and self.model and not self.is_permitted(self.model,
                                                                   principals,
                                                                   'view'):
                return None
            return self.model
        return self.get_many([key], principals=principals)[0]

    def get_many(self, keys, principals=None):
        """
        Retrieve multiple models for a list of keys.

        Note that this method always returns the same number of
        models as the number of keys in the same order.
        Models can be None if not found, or if principals are specified
        and the model view is not permitted.
        """

        pkey_col = getattr(self.orm_class, self.key_col_name)
        keys = [int(k) for k in keys]
        models_by_id = {getattr(r, self.key_col_name): r for r in
                        self.session.query(self.orm_class).filter(
            pkey_col.in_(keys)).all()}
        models = []
        for key in keys:
            model = models_by_id.get(key)
            if model is None:
                models.append(None)
            elif principals and not self.is_permitted(model,
                                                      principals,
                                                      'view'):
                raise HTTPForbidden(
                    'Failed ACL check: permission "view" on %s %s' % (
                    self.orm_class.__name__, key))
            else:
                models.append(model)
        return models


    def pre_put_hook(self, model):
        return model


    def put(self, model=None, principals=None):
        if model is None:
            if self.model is None:
                raise ValueError('No model to put')
            model = self.model
        return self.put_many([model], principals=principals)[0]


    def put_many(self, models, principals=None):
        if not models:
            return
        for model in models:
            key = getattr(model, self.key_col_name)
            if key is None:
                permission = 'add'
            else:
                permission = 'edit'
            model = self.pre_put_hook(model)
            self.session.add(model)
            if principals and not self.is_permitted(
                model, principals, permission):
                raise HTTPForbidden('Failed ACL check: permission "%s" on %s %s' % (
                    permission, self.orm_class.__name__, key))
        try:
            self.session.flush()
        except sqlalchemy.exc.IntegrityError as err:
            raise StorageError.from_err(err)
        return models

    def delete(self, model=None, principals=None):
        if model is None:
            if self.model is None:
                raise ValueError('No model to delete')
            model = self.model
        self.session.delete(model)
        if principals and not self.is_permitted(
            model, principals, 'delete'):
            raise HTTPForbidden('Failed ACL check for permission "delete"')
        self.session.flush()

    def search(self,
               filters=None,
               principals=None,
               limit=100,
               offset=0,
               order_by=None,
               format=None,
               from_query=None,
               post_query_callback=None,
               apply_limits_post_query=False,
               keys_only=False):
        query = from_query or self.session.query(self.orm_class)

        order_by = order_by or []
        if not isinstance(order_by, list):
            order_by = [order_by]

        if filters:
            query = query.filter(sql.and_(*filters))
        acl_filters = []
        acl_joined_tables = []
        for filter in self.acl_filters(principals):
            if (filter.left.table.name != self.orm_class.__table__.name and
                filter.left.table.name not in acl_joined_tables):
                # acl requires filter on other table
                query = query.join(filter.left.table)
                acl_joined_tables.append(filter.left.table.name)
            acl_filters.append(filter)
        if acl_filters:
            query = query.filter(sql.or_(*acl_filters))


        if not apply_limits_post_query:
            total = query.count()
            query = query.order_by(*order_by)
            query = query.offset(offset)
            query = query.limit(limit)
        if post_query_callback:
            # useful for cte aggregations, etc
            query = post_query_callback(query)
            if apply_limits_post_query:
                total = query.count()
                query = query.order_by(*order_by)
                query = query.offset(offset)
                query = query.limit(limit)

        if keys_only:
            query = query.options(load_only(self.key_col_name))
        return {'total': total,
                'hits': [h for h in query.all()]}


    def is_permitted(self, model, principals, permission):
        policy = self.registry.queryUtility(IAuthorizationPolicy)
        context = self.__class__(self.registry, self.session, model=model)
        permitted = policy.permits(context, principals, permission)
        if permitted == False:
            return False
        return True

    def acl_filters(self, principals):
        return []

class UserResource(BaseResource):
    orm_class = User
    key_col_name = 'id'


    def __acl__(self):
        yield (Allow, 'group:admin', ALL_PERMISSIONS)
        if self.model:
            # users can view their own info
            yield (Allow, 'user:%s' % self.model.userid, 'view')
        elif self.model is None:
            # no model loaded yet, allow container view
            yield (Allow, 'system.Authenticated', 'view')


    def acl_filters(self, principals):
        filters = []
        if 'group:admin' in principals:
            return filters
        # only return the user object of logged in user
        user_ids = [
            p.split(':', 1)[1] for p in principals if p.startswith('user:')]
        for user_id in user_ids:
            filters.append(User.userid == user_id)
        return filters


class PersonResource(BaseResource):
    orm_class = Person
    key_col_name = 'id'


    def __acl__(self):
        yield (Allow, 'group:admin', ALL_PERMISSIONS)
        yield (Allow, 'system.Authenticated', 'search')
        yield (Allow, 'group:manager', ['view', 'add', 'edit', 'delete'])
        yield (Allow, 'group:editor', ['view', 'add', 'edit', 'delete'])
        if self.model:
            # person owners can view and edit persons
            yield (Allow, 'owner:person:%s' % self.model.id, ['view', 'edit'])
            for membership in self.model.memberships:
                # group owners can view and edit persons
                yield (Allow, 'owner:group:%s' % membership.group_id, ['view', 'edit'])

        elif self.model is None:
            # no model loaded yet, allow container view
            yield (Allow, 'system.Authenticated', 'view')

    def pre_put_hook(self, model):
        name = model.family_name
        if model.family_name_prefix:
            name = '%s %s' % (model.family_name_prefix, name)
        if model.initials:
            name = '%s, %s' % (name, model.initials)
        if model.given_name:
            name = '%s (%s)' % (name, model.given_name)
        model.name = name
        return model

    def acl_filters(self, principals):
        filters = []
        for principal in principals:
            if principal in {'group:admin',
                             'group:manager',
                             'group:editor'}:
                return []
            if principal.startswith('owner:person:'):
                filters.append(Person.id == principal.split(':')[-1])
            if principal.startswith('owner:group:'):
                filters.append(Membership.group_id == principal.split(':')[-1])

        if not filters:
            # match nothing
            filters.append(Person.id == -1)
        return filters

class GroupResource(BaseResource):
    orm_class = Group
    key_col_name = 'id'


    def __acl__(self):
        yield (Allow, 'group:admin', ALL_PERMISSIONS)
        yield (Allow, 'system.Authenticated', 'search')
        yield (Allow, 'group:manager', ['view', 'add', 'edit', 'delete'])
        yield (Allow, 'group:editor', ['view', 'add', 'edit', 'delete'])
        if self.model:
            # owners can view and edit groups
            yield (Allow, 'owner:group:%s' % self.model.id, ['view', 'edit'])
        elif self.model is None:
            # no model loaded yet, allow container view
            yield (Allow, 'system.Authenticated', 'view')


    def pre_put_hook(self, model):
        model.name = model.international_name
        if model.abbreviated_name:
            model.name = '%s (%s)' % (model.name, model.abbreviated_name)
        return model

    def acl_filters(self, principals):
        filters = []
        for principal in principals:
            if principal in {'group:admin',
                             'group:manager',
                             'group:editor'}:
                return []
            if principal.startswith('owner:group:'):
                filters.append(Group.id == int(principal.split(':')[-1]))
        if not filters:
            # match nothing
            filters.append(Group.id == -1)
        return filters

    def child_groups(self):
        query = sql.text('''
        WITH RECURSIVE rel_tree AS (
          SELECT id,
                 parent_id,
                 1 AS level,
                 ARRAY[id] AS path_info,
                 false AS cyclic
          FROM groups
          WHERE parent_id = :group_id
          UNION ALL
          SELECT c.id,
                 c.parent_id,
                 p.level + 1,
                 p.path_info||c.id,
                 c.id = ANY(p.path_info) as cyclic
          FROM groups c
          JOIN rel_tree p ON c.parent_id = p.id AND NOT cyclic)
        SELECT array_agg(DISTINCT path)
        FROM rel_tree, unnest(rel_tree.path_info) path
        ''')
        return self.session.execute(
            query, dict(group_id=self.model.id)).scalar() or []

class MembershipResource(BaseResource):
    orm_class = Membership
    key_col_name = 'id'


    def __acl__(self):
        yield (Allow, 'group:admin', ALL_PERMISSIONS)
        yield (Allow, 'group:manager', ['view', 'add', 'edit', 'delete'])
        yield (Allow, 'group:editor', ['view', 'add', 'edit', 'delete'])
        if self.model:
            # group owners can view and edit members
            yield (Allow, 'owner:group:%s' % self.model.group_id, ['view', 'edit', 'delete'])
            # person owners can view and edit memberships
            yield (Allow, 'owner:person:%s' % self.model.person_id, ['view', 'edit', 'delete'])
        elif self.model is None:
            # no model loaded yet, allow container view
            yield (Allow, 'system.Authenticated', 'view')

    def acl_filters(self, principals):
        filters = []
        for principal in principals:
            if principal in {'group:admin',
                             'group:manager',
                             'group:editor'}:
                return []
            if principal.startswith('owner:group:'):
                filters.append(Membership.group_id == principal.split(':')[-1])
            elif principal.startswith('owner:person:'):
                filters.append(
                    Membership.person_id == principal.split(':')[-1])
        return filters


class TypeResource(object):
    schemes = {'group': GroupType,
               'groupAccount': GroupAccountType,
               'personAccount': PersonAccountType}
    orm = None

    def __acl__(self):
        yield (Allow, 'system.Authenticated', 'view')
        yield (Allow, 'group:admin', 'edit')


    def __init__(self, session, scheme_id):
        self.session = session
        self.scheme_id = scheme_id
        if scheme_id is not None:
            self.orm = self.schemes[scheme_id]
        self.model = None

    def from_dict(self, data):
        values = dict((v['key'], v['label']) for v in data['values'])
        for item in self.session.query(self.orm).all():
            if item.key not in values:
                self.session.delete(item)
            else:
                if values[item.key] != item.label:
                    item.label = values[item.key]
                    self.session.add(item)
                del values[item.key]
        for key, label in values.items():
            self.session.add(self.orm(key=key, label=label))
        self.session.flush()

    def to_dict(self):
        values = []
        for setting in self.session.query(self.orm).all():
            values.append({'key': setting.key, 'label': setting.label})
        return {'id': self.scheme_id, 'values': values}

    def list(self):
        listing = []
        for scheme_id in self.schemes.keys():
            res = TypeResource(self.session, scheme_id)
            listing.append(res.to_dict())
        return {'types': listing}
