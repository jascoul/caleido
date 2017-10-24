
from core import BaseTest

class ActorWebTest(BaseTest):

    def test_crud_as_admin(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/actors',
                                 {'family_name': 'John', 'type': 'individual'},
                                 headers=headers,
                                 status=201)
        john_id = out.json['id']
        # Change Johns name to Johnny
        self.api.put_json('/api/v1/actors/%s' % john_id,
                          {'family_name': 'Johnny', 'type': 'individual'},
                          headers=headers,
                          status=200)
        out = self.api.get('/api/v1/actors/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['family_name'] == 'Johnny'
        self.api.delete('/api/v1/actors/%s' % john_id,
                        headers=headers,
                        status=200)
        self.api.get('/api/v1/actors/%s' % john_id,
                          headers=headers,
                          status=404)

    def test_invalid_actor_type(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/actors',
                                 {'family_name': 'John', 'type': 'foobar'},
                                 headers=headers,
                                 status=400)
        assert out.json['errors'][0]['name'] == 'type'
        assert out.json['errors'][0]['location'] == 'body'
        assert out.json['errors'][0]['description'].startswith(
            '"foobar" is not one of')

    def test_label_generator(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/actors',
                                 {'family_name': 'Doe', 'type': 'individual'},
                                 headers=headers,
                                 status=201)
        john_id = out.json['id']
        out = self.api.get('/api/v1/actors/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['label'] == 'Doe'
        self.api.put_json('/api/v1/actors/%s' % john_id,
                          {'family_name': 'Doe',
                           'family_name_prefix': 'van der',
                           'given_name': 'John',
                           'initials': 'J.',
                           'type': 'individual'},
                          headers=headers,
                          status=200)
        out = self.api.get('/api/v1/actors/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['label'] == 'Doe'

