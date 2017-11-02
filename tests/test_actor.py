import transaction

from core import BaseTest
from caleido.models import User

class ActorWebTest(BaseTest):

    def test_crud_as_admin(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/actor/records',
                                 {'family_name': 'John', 'type': 'individual'},
                                 headers=headers,
                                 status=201)
        john_id = out.json['id']
        # Change Johns name to Johnny
        self.api.put_json('/api/v1/actor/records/%s' % john_id,
                          {'id': john_id, 'family_name': 'Johnny', 'type': 'individual'},
                          headers=headers,
                          status=200)
        out = self.api.get('/api/v1/actor/records/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['family_name'] == 'Johnny'
        self.api.delete('/api/v1/actor/records/%s' % john_id,
                        headers=headers,
                        status=200)
        self.api.get('/api/v1/actor/records/%s' % john_id,
                          headers=headers,
                          status=404)

    def test_invalid_actor_type(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/actor/records',
                                 {'family_name': 'John', 'type': 'foobar'},
                                 headers=headers,
                                 status=400)
        assert out.json['errors'][0]['name'] == 'type'
        assert out.json['errors'][0]['location'] == 'body'
        assert out.json['errors'][0]['description'].startswith(
            '"foobar" is not one of')

    def test_individual_actor_name_generator(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/actor/records',
                                 {'family_name': 'Doe', 'type': 'individual'},
                                 headers=headers,
                                 status=201)
        john_id = out.json['id']
        out = self.api.get('/api/v1/actor/records/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['name'] == 'Doe'
        self.api.put_json('/api/v1/actor/records/%s' % john_id,
                          {'id': john_id,
                           'family_name': 'Doe',
                           'family_name_prefix': 'van der',
                           'given_name': 'John',
                           'initials': 'J.',
                           'type': 'individual'},
                          headers=headers,
                          status=200)
        out = self.api.get('/api/v1/actor/records/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['name'] == 'van der Doe, J. (John)'

    def test_corporate_actor_name_generator(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json(
            '/api/v1/actor/records',
            {'name': 'Erasmus University', 'type': 'organisation'},
            headers=headers,
            status=400)
        assert out.json['errors'][0]['name'] == 'corporate_international_name'
        assert out.json['errors'][0]['description']  == 'Required'
        out = self.api.post_json(
            '/api/v1/actor/records',
            {'corporate_international_name': 'Erasmus University',
             'type': 'organisation'},
            headers=headers,
            status=201)
        assert out.json['name'] == out.json['corporate_international_name']

    def test_adding_actor_accounts(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json(
            '/api/v1/actor/records',
            {'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '1234'}]},
             headers=headers,
             status=201)
        john_id = out.json['id']
        assert out.json['accounts'] == [{'type': 'local', 'value': '1234'}]
        out = self.api.get('/api/v1/actor/records/%s' % john_id,
                           headers=headers)
        assert out.json['accounts'] == [{'type': 'local', 'value': '1234'}]
        out = self.api.put_json(
            '/api/v1/actor/records/%s' % john_id,
            {'id': john_id,
             'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': 'XXXX'}]},
             headers=headers,
             status=200)
        out = self.api.get('/api/v1/actor/records/%s' % john_id,
                           headers=headers)
        assert out.json['accounts'] == [{'type': 'local', 'value': 'XXXX'}]

    def test_insert_non_unique_account(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        self.api.post_json(
            '/api/v1/actor/records',
            {'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '1234'}]},
             headers=headers,
             status=201)
        # adding a resource with a used account, fails
        out = self.api.post_json(
            '/api/v1/actor/records',
            {'family_name': 'Doe',
             'initials': 'J.',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '1234'}]},
             headers=headers,
             status=400)
        assert 'IntegrityError' in out.json['errors'][0]['description']
        # add a user with a different account, then change the account
        # to an existing one
        out = self.api.post_json(
            '/api/v1/actor/records',
            {'family_name': 'Doe',
             'initials': 'J.',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': 'XXX'}]},
             headers=headers,
             status=201)
        last_id = out.json['id']
        out = self.api.put_json(
            '/api/v1/actor/records/%s' % last_id,
            {'id': last_id,
             'family_name': 'Doe',
             'initials': 'J.',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '1234'}]},
             headers=headers,
             status=400)
        assert 'IntegrityError' in out.json['errors'][0]['description']

    def test_insert_empty_account_or_no_account(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json(
            '/api/v1/actor/records',
            {'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '1234'}]},
             headers=headers,
             status=201)
        last_id = out.json['id']
        # let's change a field without specifying the accounts
        out = self.api.put_json(
            '/api/v1/actor/records/%s' % last_id,
            {'id': last_id,
             'family_name': 'Doe',
             'initials': 'J.',
             'type': 'individual'},
             headers=headers,
             status=200)
        # the accounts should be intact
        assert out.json['accounts'] == [{'type': 'local', 'value': '1234'}]
        # we can clear the accounts by supllying an empty list/array
        out = self.api.put_json(
            '/api/v1/actor/records/%s' % last_id,
            {'id': last_id,
             'family_name': 'Doe',
             'initials': 'J.',
             'type': 'individual',
             'accounts': []},
             headers=headers,
             status=200)
        assert out.json['accounts'] == []

class ActorAuthorzationWebTest(BaseTest):
    def test_crud_actors_by_user_groups(self):
        super(ActorAuthorzationWebTest, self).setUp()
        # add some users
        test_users = [('test_admin', 100),
                      ('test_manager', 80),
                      ('test_editor',  60)]
        session = self.storage.make_session(namespace='unittest')
        for user, user_group in test_users:
            session.add(
                User(userid=user, credentials=user, user_group=user_group))
        session.flush()
        transaction.commit()
        for user, user_group in test_users:
            token = self.api.post_json(
            '/api/v1/auth/login',
            {'user': user, 'password': user}).json['token']
            headers = dict(Authorization='Bearer %s' % token)
            out = self.api.post_json(
                '/api/v1/actor/records', {'family_name': user, 'type': 'individual'},
                headers=headers,
                status=201)
            last_id = out.json['id']
            out = self.api.get('/api/v1/actor/records/%s' % last_id, headers=headers)
            assert out.json['family_name'] == user
            out = self.api.put_json(
                '/api/v1/actor/records/%s' % last_id,
                {'id': last_id, 'family_name': user, 'given_name': 'John',
                 'type': 'individual'},
                headers=headers,
                status=200)
            assert out.json['given_name'] == 'John'
            out = self.api.delete('/api/v1/actor/records/%s' % last_id,
                                  headers=headers)
            self.api.get('/api/v1/actor/records/%s' % last_id,
                         headers=headers,
                         status=404)

    def test_owners_can_view_and_edit(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json(
            '/api/v1/actor/records',
            {'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '1234'}]},
             headers=headers,
             status=201)
        actor_id = out.json['id']
        out = self.api.post_json(
            '/api/v1/user/records',
            {'userid': 'john',
             'credentials': 'john',
             'user_group': 40,
             'owns': [{'actor_id': actor_id}]},
            headers=headers, status=201)
        assert out.json['owns'] == [{'actor_id': actor_id}]
        token = self.api.post_json(
            '/api/v1/auth/login',
            {'user': 'john', 'password': 'john'}).json['token']
        john_headers = dict(Authorization='Bearer %s' % token)
        # we can view the metadata
        out = self.api.get('/api/v1/actor/records/%s' % actor_id,
                           headers=john_headers)
        # and are allowed to edit it
        self.api.put_json(
            '/api/v1/actor/records/%s' % actor_id,
            {'id': actor_id,
             'family_name': 'Doe',
             'initials': 'J.',
             'type': 'individual',
             'accounts': []},
             headers=john_headers,
             status=200)
        # but not allowed to delete
        self.api.delete(
            '/api/v1/actor/records/%s' % actor_id,
             headers=john_headers, status=403)

    def test_actor_bulk_import(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        records = {'records': [
            {'id': 1,
             'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '123'}]},
            {'id': 2,
             'family_name': 'Doe',
             'given_name': 'Jane',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '345'}]}
             ]}
        # bulk add records
        out = self.api.post_json('/api/v1/actor/bulk',
                                 records,
                                 headers=headers,
                                 status=201)
        assert out.json['status'] == 'ok'
        out = self.api.get('/api/v1/actor/records/2', headers=headers)
        assert out.json['given_name'] == 'Jane'
        records['records'][1]['initials'] = 'J.'
        # bulk update records
        out = self.api.post_json('/api/v1/actor/bulk',
                                 records,
                                 headers=headers,
                                 status=201)
        assert out.json['status'] == 'ok'
        out = self.api.get('/api/v1/actor/records/2', headers=headers)
        assert out.json['initials'] == 'J.'

