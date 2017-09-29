from pyramid.security import Allow
from sqlalchemy_utils.functions import get_primary_keys
import transaction
from scributor.models import User

class Resource(object):
    orm = None
    
    def __init__(self, storage, resource):
        self.storage = storage
        self.model = resource


    def to_dict(self):
        raise NotImplemented()

    
    def from_dict(self, data):
        self.model = self.orm(**data)


    def insert(self):
        self.storage.session.add(self.model)
        self.storage.session.flush()


    def delete(self):
        self.storage.session.delete(self.model)
        self.storage.session.flush()
        
    def reload(self):
        primary_keys = get_primary_keys(self.orm)
        if len(primary_keys) != 1:
            raise ValueError(
                'default implementation can not reload composite primary keys')
        pkey_name, pkey_column = list(primary_keys.items())[0]
        pkey_value = getattr(self.model, pkey_name)
        transaction.commit()
        self.model = self.storage.session.query(
            self.orm).filter(pkey_column==pkey_value).first()
            
        
class UserResource(Resource):
    orm = User

        
    def __acl__(self):
        yield (Allow, 'group:admin', 'view')
        yield (Allow, 'group:admin', 'add')
        yield (Allow, 'group:admin', 'edit')
        yield (Allow, 'group:admin', 'delete')

  
    def to_dict(self):
        return {'id': self.model.id,
                'user_group': self.model.user_group,
                'userid': self.model.userid,
                'credentials': self.model.credentials.hash.decode('utf8')}
