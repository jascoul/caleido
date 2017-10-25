
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
                          {'id': john_id, 'family_name': 'Johnny', 'type': 'individual'},
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

    def est_individual_actor_name_generator(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/actors',
                                 {'family_name': 'Doe', 'type': 'individual'},
                                 headers=headers,
                                 status=201)
        john_id = out.json['id']
        out = self.api.get('/api/v1/actors/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['name'] == 'Doe'
        self.api.put_json('/api/v1/actors/%s' % john_id,
                          {'id': john_id,
                           'family_name': 'Doe',
                           'family_name_prefix': 'van der',
                           'given_name': 'John',
                           'initials': 'J.',
                           'type': 'individual'},
                          headers=headers,
                          status=200)
        out = self.api.get('/api/v1/actors/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['name'] == 'van der Doe, J. (John)'

    def test_corporate_actor_name_generator(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json(
            '/api/v1/actors',
            {'name': 'Erasmus University', 'type': 'organisation'},
            headers=headers,
            status=400)
        assert out.json['errors'][0]['name'] == 'corporate_international_name'
        assert out.json['errors'][0]['description']  == 'Required'
        out = self.api.post_json(
            '/api/v1/actors',
            {'corporate_international_name': 'Erasmus University',
             'type': 'organisation'},
            headers=headers,
            status=201)
        assert out.json['name'] == out.json['corporate_international_name']

    def test_adding_actor_accounts(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json(
            '/api/v1/actors',
            {'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '1234'}]},
             headers=headers,
             status=201)
        john_id = out.json['id']
        assert out.json['accounts'] == [{'type': 'local', 'value': '1234'}]
        out = self.api.get('/api/v1/actors/%s' % john_id,
                           headers=headers)
        assert out.json['accounts'] == [{'type': 'local', 'value': '1234'}]
        out = self.api.put_json(
            '/api/v1/actors/%s' % john_id,
            {'id': john_id,
             'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': 'XXXX'}]},
             headers=headers,
             status=200)
        out = self.api.get('/api/v1/actors/%s' % john_id,
                           headers=headers)
        assert out.json['accounts'] == [{'type': 'local', 'value': 'XXXX'}]



