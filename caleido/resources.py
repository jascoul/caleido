import math

from pyramid.security import Allow
from sqlalchemy_utils.functions import get_primary_keys
import transaction
from caleido.models import User, ActorType

class Resource(object):
    orm = None
    
    def __init__(self, session, resource):
        self.session = session
        self.model = resource


    def to_dict(self):
        raise NotImplemented()

    
    def from_dict(self, data):
        self.model = self.orm(**data)


    def insert(self):
        self.session.add(self.model)
        self.session.flush()


    def delete(self):
        self.session.delete(self.model)
        self.session.flush()
        
    def reload(self):
        self.session.refresh(self.model)
        primary_keys = get_primary_keys(self.orm)
        if len(primary_keys) != 1:
            raise ValueError(
                'default implementation can not reload composite primary keys')
        pkey_name, pkey_column = list(primary_keys.items())[0]
        pkey_value = getattr(self.model, pkey_name)
        transaction.commit()
        self.model = self.session.query(
            self.orm).filter(pkey_column==pkey_value).first()
            
    def listing_query(self):
        query = self.session.query(self.orm)
        return query

    def acl_filter(self, query, userid, principals):
        raise NotImplemented

    def list(self, query, page=1, page_size=100):
        total = query.count()
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        total_pages = math.ceil(total / page_size)
        if page == 1:
            prev = None
        else:
            prev = page - 1
        if page == total_pages:
            next = None
        else:
            next = page + 1
        return {'total': total,
                'page': {'total': total_pages,
                         'size': page_size,
                         'current': page,
                         'previous': prev,
                         'next': next},
                'result': (self.__class__(self.session, row)
                           for row in query.all())}

        
class UserResource(Resource):
    orm = User
        
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


    def acl_filter(self, query, userid, principals):
        if not 'group:admin' in principals:
            # only show current user
            query = query.filter(User.userid == userid)
        return query

        
    def to_dict(self):
        return {'id': self.model.id,
                'user_group': self.model.user_group,
                'userid': self.model.userid,
                'credentials': self.model.credentials.hash.decode('utf8')}

    
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
