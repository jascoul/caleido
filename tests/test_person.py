import transaction

from core import BaseTest
from caleido.models import User

class PersonWebTest(BaseTest):

    def test_crud_as_admin(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/person/records',
                                 {'family_name': 'Doe',
                                  'given_name': 'John', 'type': 'individual'},
                                 headers=headers,
                                 status=201)
        john_id = out.json['id']
        # Change Johns name to Johnny
        self.api.put_json('/api/v1/person/records/%s' % john_id,
                          {'id': john_id,
                           'family_name': 'Doe',
                           'given_name': 'Johnny'},
                          headers=headers,
                          status=200)
        out = self.api.get('/api/v1/person/records/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['given_name'] == 'Johnny'
        self.api.delete('/api/v1/person/records/%s' % john_id,
                        headers=headers,
                        status=200)
        self.api.get('/api/v1/person/records/%s' % john_id,
                          headers=headers,
                          status=404)

    def test_person_name_generator(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/person/records',
                                 {'family_name': 'Doe'},
                                 headers=headers,
                                 status=400)
        assert out.json['errors'][0]['name'] == 'given_name'
        assert out.json['errors'][0]['description'] == (
            "Required: supply either 'initials' or 'given_name'")
        out = self.api.post_json('/api/v1/person/records',
                                 {'family_name': 'Doe', 'given_name': 'Joe'},
                                 headers=headers,
                                 status=201)
        john_id = out.json['id']
        out = self.api.get('/api/v1/person/records/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['name'] == 'Doe (Joe)'
        self.api.put_json('/api/v1/person/records/%s' % john_id,
                          {'id': john_id,
                           'family_name': 'Doe',
                           'family_name_prefix': 'van der',
                           'given_name': 'John',
                           'initials': 'J.',
                           'type': 'individual'},
                          headers=headers,
                          status=200)
        out = self.api.get('/api/v1/person/records/%s' % john_id,
                          headers=headers,
                          status=200)
        assert out.json['name'] == 'van der Doe, J. (John)'

    def test_adding_person_accounts(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json(
            '/api/v1/person/records',
            {'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '1234'}]},
             headers=headers,
             status=201)
        john_id = out.json['id']
        assert out.json['accounts'] == [{'type': 'local', 'value': '1234'}]
        out = self.api.get('/api/v1/person/records/%s' % john_id,
                           headers=headers)
        assert out.json['accounts'] == [{'type': 'local', 'value': '1234'}]
        out = self.api.put_json(
            '/api/v1/person/records/%s' % john_id,
            {'id': john_id,
             'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': 'XXXX'}]},
             headers=headers,
             status=200)
        out = self.api.get('/api/v1/person/records/%s' % john_id,
                           headers=headers)
        assert out.json['accounts'] == [{'type': 'local', 'value': 'XXXX'}]


    def test_insert_empty_account_or_no_account(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json(
            '/api/v1/person/records',
            {'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '1234'}]},
             headers=headers,
             status=201)
        last_id = out.json['id']
        # let's change a field without specifying the accounts
        out = self.api.put_json(
            '/api/v1/person/records/%s' % last_id,
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
            '/api/v1/person/records/%s' % last_id,
            {'id': last_id,
             'family_name': 'Doe',
             'initials': 'J.',
             'type': 'individual',
             'accounts': []},
             headers=headers,
             status=200)
        assert out.json['accounts'] == []

class PersonAuthorzationWebTest(BaseTest):
    def test_crud_persons_by_user_groups(self):
        super(PersonAuthorzationWebTest, self).setUp()
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
                '/api/v1/person/records', {'family_name': user,
                                           'given_name': user},
                headers=headers,
                status=201)
            last_id = out.json['id']
            out = self.api.get('/api/v1/person/records/%s' % last_id, headers=headers)
            assert out.json['family_name'] == user
            out = self.api.put_json(
                '/api/v1/person/records/%s' % last_id,
                {'id': last_id, 'family_name': user, 'given_name': 'John'},
                headers=headers,
                status=200)
            assert out.json['given_name'] == 'John'
            out = self.api.delete('/api/v1/person/records/%s' % last_id,
                                  headers=headers)
            self.api.get('/api/v1/person/records/%s' % last_id,
                         headers=headers,
                         status=404)

    def test_owners_can_view_and_edit(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json(
            '/api/v1/person/records',
            {'family_name': 'Doe',
             'given_name': 'John',
             'type': 'individual',
             'accounts': [{'type': 'local', 'value': '1234'}]},
             headers=headers,
             status=201)
        person_id = out.json['id']
        out = self.api.post_json(
            '/api/v1/user/records',
            {'userid': 'john',
             'credentials': 'john',
             'user_group': 40,
             'owns': [{'person_id': person_id}]},
            headers=headers, status=201)
        assert out.json['owns'][0]['person_id'] == person_id

        token = self.api.post_json(
            '/api/v1/auth/login',
            {'user': 'john', 'password': 'john'}).json['token']
        john_headers = dict(Authorization='Bearer %s' % token)
        # we can view the metadata
        out = self.api.get('/api/v1/person/records/%s' % person_id,
                           headers=john_headers)
        # and are allowed to edit it
        self.api.put_json(
            '/api/v1/person/records/%s' % person_id,
            {'id': person_id,
             'family_name': 'Doe',
             'initials': 'J.',
             'type': 'individual',
             'accounts': []},
             headers=john_headers,
             status=200)
        # but not allowed to delete
        self.api.delete(
            '/api/v1/person/records/%s' % person_id,
             headers=john_headers, status=403)



    def test_person_bulk_import(self):
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
        out = self.api.post_json('/api/v1/person/bulk',
                                 records,
                                 headers=headers,
                                 status=201)
        assert out.json['status'] == 'ok'
        out = self.api.get('/api/v1/person/records/2', headers=headers)
        assert out.json['given_name'] == 'Jane'
        records['records'][1]['initials'] = 'J.'
        # bulk update records
        out = self.api.post_json('/api/v1/person/bulk',
                                 records,
                                 headers=headers,
                                 status=201)
        assert out.json['status'] == 'ok'
        out = self.api.get('/api/v1/person/records/2', headers=headers)
        assert out.json['initials'] == 'J.'

class PersonMembersTest(PersonWebTest):
    def setUp(self):
        super(PersonMembersTest, self).setUp()
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/person/records',
                                 {'family_name': 'Doe',
                                  'given_name': 'John'},
                                 headers=headers,
                                 status=201)
        self.john_id = out.json['id']
        out = self.api.post_json('/api/v1/group/records',
                                 {'international_name': 'Corp.',
                                  'type': 'organisation'},
                                 headers=headers,
                                 status=201)
        self.corp_id = out.json['id']

    def test_adding_inline_membership(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.put_json('/api/v1/person/records/%s' % self.john_id,
                                 {'family_name': 'Doe',
                                  'given_name': 'John',
                                  'id': self.john_id,
                                  'memberships': [{'group_id': self.corp_id}]},
                                 headers=headers,
                                 status=200)
        assert len(out.json['memberships']) == 1

    def test_adding_inline_membership_as_owner(self):
        # XXX this should not be allowed, but it is to hard to implement
        # maybe we should deny inlined membership changes.
        # It is too much hastle.
        headers = dict(Authorization='Bearer %s' % self.generate_test_token(
            'owner', owners=[{'person_id': self.john_id}]))
        out = self.api.put_json('/api/v1/person/records/%s' % self.john_id,
                                 {'family_name': 'Doe',
                                  'given_name': 'John',
                                  'id': self.john_id,
                                  'memberships': [{'group_id': self.corp_id}]},
                                 headers=headers,
                                 status=200)
        assert len(out.json['memberships']) == 1

    def test_adding_inline_position(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.put_json('/api/v1/person/records/%s' % self.john_id,
                                 {'family_name': 'Doe',
                                  'given_name': 'John',
                                  'id': self.john_id,
                                  'positions': [{'group_id': self.corp_id,
                                                 'type': 'academic',
                                                 'description': 'Full Professor'}]},
                                 headers=headers,
                                 status=200)
        assert len(out.json['positions']) == 1

class PersonRetrievalWebTest(PersonWebTest):
    def setUp(self):
        super(PersonRetrievalWebTest, self).setUp()
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/person/records',
                                 {'family_name': 'Doe',
                                  'given_name': 'John'},
                                 headers=headers,
                                 status=201)
        self.john_id = out.json['id']
        out = self.api.post_json('/api/v1/person/records',
                                 {'family_name': 'Blow',
                                  'given_name': 'Joe'},
                                 headers=headers,
                                 status=201)
        self.joe_id = out.json['id']
        out = self.api.post_json('/api/v1/group/records',
                                 {'international_name': 'Corp.',
                                  'type': 'organisation'},
                                 headers=headers,
                                 status=201)
        self.corp_id = out.json['id']
        self.api.post_json('/api/v1/membership/records',
                           {'person_id': self.john_id,
                            'group_id': self.corp_id,
                            'start_date': '2017-01-01',
                            'end_date': '2017-12-31'},
                           headers=headers,
                           status=201)

    def test_person_filtering(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get(
            '/api/v1/person/records',
            headers=headers, status=200)
        assert out.json['total'] == 2
        out = self.api.get(
            '/api/v1/person/records?query=Doe',
            headers=headers, status=200)
        assert out.json['total'] == 1

    def test_person_snippet(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get(
            '/api/v1/person/records?query=Doe&format=snippet',
            headers=headers, status=200)
        assert out.json['total'] == 1
        assert len(out.json.get('snippets', [])) == 1
        assert out.json['snippets'][0]['memberships'] == 1


    def test_owner_person_search(self):
        headers = dict(Authorization='Bearer %s' % self.generate_test_token('owner'))
        # all users have search permission on all persons
        out = self.api.get(
            '/api/v1/person/search?query=Doe&format=snippet',
            headers=headers, status=200)
        assert out.json['total'] == 1
        assert len(out.json.get('snippets', [])) == 1

