import math

from pyramid.httpexceptions import HTTPForbidden
from pyramid.security import Allow
from pyramid.interfaces import IAuthorizationPolicy
from sqlalchemy_utils.functions import get_primary_keys
from sqlalchemy.orm import load_only
import transaction
from caleido.models import User, ActorType


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
        if key:
            model = self.session.query(self.orm_class).filter(
                getattr(self.orm_class,
                        self.key_col_name) == key).first()
        else:
            model = self.model
        if model and principals:
            if not self.is_permitted(model, principals, 'view'):
                return None
        return model


    def get_many(self, keys, principals=None):
        raise NotImplemented()


    def put(self, model=None, principals=None):
        if model is None:
            if self.model is None:
                raise ValueError('No model to put')
            model = self.model
        key = getattr(model, self.key_col_name)
        if key is None:
            permission = 'add'
        else:
            permission = 'edit'
        self.session.add(model)
        if principals and not self.is_permitted(
            model, principals, permission):
            raise HTTPForbidden('Failed ACL check for permission "%s"' % permission)
        self.session.flush()
        return model


    def put_many(self, models, principals=None):
        raise NotImplemented()


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
               keys_only=False):
        query = self.session.query(self.orm_class)
        for filter in self.acl_filters(principals) + (filters or []):
            query = query.filter(filter)
        total = query.count()
        query = query.offset(offset).limit(limit)
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
        yield (Allow, 'group:admin', 'view')
        yield (Allow, 'group:admin', 'add')
        yield (Allow, 'group:admin', 'edit')
        yield (Allow, 'group:admin', 'delete')
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
