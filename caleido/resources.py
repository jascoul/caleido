import math

from pyramid.httpexceptions import HTTPForbidden
from pyramid.security import Allow, ALL_PERMISSIONS
from pyramid.interfaces import IAuthorizationPolicy
from sqlalchemy_utils.functions import get_primary_keys
from sqlalchemy.orm import load_only
import sqlalchemy.exc
import transaction
from caleido.models import User, Actor, ActorType
from caleido.exceptions import StorageError

class ResourceFactory(object):
    def __init__(self, resource_class):
        self._class = resource_class

    def __call__(self, request):
        key = request.matchdict.get('id')
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
               keys_only=False):
        query = self.session.query(self.orm_class)
        order_by = order_by or []
        if not isinstance(order_by, list):
            order_by = [order_by]

        for filter in self.acl_filters(principals) + (filters or []):
            query = query.filter(filter)
        total = query.count()
        query = query.order_by(*order_by).offset(offset).limit(limit)
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


class ActorResource(BaseResource):
    orm_class = Actor
    key_col_name = 'id'


    def __acl__(self):
        yield (Allow, 'group:admin', ALL_PERMISSIONS)
        yield (Allow, 'group:manager', ['view', 'add', 'edit', 'delete'])
        yield (Allow, 'group:editor', ['view', 'add', 'edit', 'delete'])
        if self.model:
            # owners can view and edit actors
            yield (Allow, 'actor:%s' % self.model.id, ['view', 'edit'])
        elif self.model is None:
            # no model loaded yet, allow container view
            yield (Allow, 'system.Authenticated', 'view')

    def pre_put_hook(self, model):
        if model.type == 'individual':
            name = model.family_name
            if model.family_name_prefix:
                name = '%s %s' % (model.family_name_prefix, name)
            if model.family_name_suffix:
                name = '%s %s' % (name, model.family_name_suffix)
            if model.initials:
                name = '%s, %s' % (name, model.initials)
            if model.given_name:
                name = '%s (%s)' % (name, model.given_name)
            model.name = name
        else:
            model.name = model.corporate_international_name
        return model

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


class TypeResource(object):
    schemes = {'actor': ActorType}
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
