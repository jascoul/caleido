from core import BaseTest

class WorkWebTest(BaseTest):

    def test_crud_as_admin(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/work/records',
                                 {'title': 'A test article.',
                                  'issued': '2018-02-26',
                                  'type': 'article'},
                                 headers=headers)
        assert out.status_code == 201
        last_id = out.json['id']
        self.api.put_json('/api/v1/work/records/%s' % last_id,
                          {'id': last_id,
                           'title': 'A modified article.',
                           'issued': '2018-02-26',
                           'type': 'article'},
                          headers=headers,
                          status=200)
        out = self.api.get('/api/v1/work/records/%s' % last_id,
                          headers=headers,
                          status=200)
        assert out.json['title'] == 'A modified article.'
        self.api.delete('/api/v1/work/records/%s' % last_id,
                        headers=headers,
                        status=200)
        self.api.get('/api/v1/group/work/%s' % last_id,
                          headers=headers,
                          status=404)

    def test_invalid_group_type(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/work/records',
                                 {'title': 'A test article.',
                                  'issued': '2018-02-26',
                                  'type': 'foobar'},
                                 headers=headers,
                                 status=400)
        assert out.json['errors'][0]['name'] == 'type'
        assert out.json['errors'][0]['location'] == 'body'
        assert out.json['errors'][0]['description'].startswith(
            '"foobar" is not one of')

    def test_work_bulk_import(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        records = {'records': [
            {'id': 1,
             'title': 'Pub 1',
             'type': 'article',
             'issued': '2018-01-01'},
            {'id': 2,
             'title': 'Pub 2',
             'type': 'article',
             'issued': '2018-01-01'
             }]}
        # bulk add records
        out = self.api.post_json('/api/v1/work/bulk',
                                 records,
                                 headers=headers,
                                 status=201)
        assert out.json['status'] == 'ok'
        out = self.api.get('/api/v1/work/records/2', headers=headers)
        assert out.json['title'] == 'Pub 2'
        records['records'][1]['title'] = 'Pub 2 with modified title'
        # bulk update records
        out = self.api.post_json('/api/v1/work/bulk',
                                 records,
                                 headers=headers,
                                 status=201)
        assert out.json['status'] == 'ok'
        out = self.api.get('/api/v1/work/records/2', headers=headers)
        assert out.json['title'] == 'Pub 2 with modified title'

class WorkPermissionWebTest(BaseTest):
    def setUp(self):
        super(WorkPermissionWebTest, self).setUp()
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/person/records',
                                 {'family_name': 'Doe',
                                  'given_name': 'John'},
                                 headers=headers,
                                 status=201)
        self.john_id = out.json['id']
        out = self.api.post_json('/api/v1/person/records',
                                 {'family_name': 'Doe',
                                  'given_name': 'Jane'},
                                 headers=headers,
                                 status=201)
        self.jane_id = out.json['id']
        out = self.api.post_json('/api/v1/group/records',
                                 {'international_name': 'Corp.',
                                  'type': 'organisation'},
                                 headers=headers,
                                 status=201)
        self.corp_id = out.json['id']
        out = self.api.post_json('/api/v1/work/records',
                                 {'title': 'Test Publication',
                                  'type': 'article',
                                  'issued': '2018-02-27'},
                                 headers=headers,
                                 status=201)
        self.pub_id = out.json['id']
        out = self.api.post_json('/api/v1/work/records',
                                 {'title': 'Another Test Publication',
                                  'type': 'article',
                                  'issued': '2018-02-27'},
                                 headers=headers,
                                 status=201)
        self.another_pub_id = out.json['id']
        out = self.api.post_json('/api/v1/contributor/records',
                                 {'person_id': self.john_id,
                                  'work_id': self.pub_id,
                                  'role': 'author',
                                  'position': 0},
                                 headers=headers,
                                 status=201)
        self.contributor_id = out.json['id']
        self.api.post_json('/api/v1/contributor/records',
                           {'person_id': self.jane_id,
                            'work_id': self.another_pub_id,
                            'role': 'author',
                            'position': 0},
                           headers=headers,
                           status=201)
        self.api.post_json('/api/v1/membership/records',
                           {'person_id': self.john_id,
                            'group_id': self.corp_id,
                            'start_date': '2018-01-01',
                            'end_date': '2018-12-31'},
                           headers=headers,
                           status=201)
        self.api.post_json('/api/v1/membership/records',
                           {'person_id': self.jane_id,
                            'group_id': self.corp_id,
                            'start_date': '2017-01-01',
                            'end_date': '2017-12-31'},
                           headers=headers,
                           status=201)



    def test_listing_personal_owner_works(self):
        headers = dict(Authorization='Bearer %s' % self.generate_test_token(
            'owner', owners=[{'person_id': self.john_id}]))
        out = self.api.get('/api/v1/work/records',
                           headers=headers)
        assert len(out.json['records']) == 1


    def test_retrieve_contributor_affiliations_inline(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        self.api.post_json('/api/v1/affiliation/records',
                           {'contributor_id': self.contributor_id,
                            'work_id': self.pub_id,
                            'group_id':  self.corp_id,
                            'position': 0},
                           headers=headers,
                           status=201)
        out = self.api.get('/api/v1/work/records/%s' % self.pub_id,
                           headers=headers)
        assert len(out.json['contributors']) == 1
        contributor = out.json['contributors'][0]
        assert len(contributor['affiliations']) == 1

    def test_add_contributor_inline(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/work/records/%s' % self.pub_id,
                           headers=headers)
        pub = out.json
        assert len(pub['contributors']) == 1
        pub['contributors'].append({'position': 1,
                                    'role': 'author',
                                    'person_id': self.jane_id})
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        pub = out.json
        assert len(pub['contributors']) == 2
        pub['contributors'] = list(reversed(pub['contributors']))
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        pub = out.json
        assert pub['contributors'][0]['person_id'] == 2
        assert pub['contributors'][1]['person_id'] == 1

        del pub['contributors'][0]
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        pub = out.json
        assert len(pub['contributors']) == 1


    def test_add_contributor_affiliations_inline(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/work/records/%s' % self.pub_id,
                           headers=headers)
        pub = out.json
        assert len(pub['contributors']) == 1
        assert len(pub['contributors'][0]['affiliations']) == 0

        pub['contributors'][0]['affiliations'] = [{'group_id': self.corp_id,
                                                   'position': 0}]
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        assert len(pub['contributors'][0]['affiliations']) == 1

    def test_work_with_identifiers_inline(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/work/records/%s' % self.pub_id,
                           headers=headers)
        pub = out.json
        assert len(pub['identifiers']) == 0
        pub['identifiers'].append({'type': 'doi', 'value': '10.12345/54321'})
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        assert len(pub['identifiers']) == 1
        pub['identifiers'][0]['value'] = 'changed'
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        assert len(pub['identifiers']) == 1
        assert pub['identifiers'][0]['value'] == 'changed'

    def test_work_with_measures_inline(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/work/records/%s' % self.pub_id,
                           headers=headers)
        pub = out.json
        assert len(pub['measures']) == 0
        pub['measures'].append({'type': 'cites', 'value': '10'})
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        assert len(pub['measures']) == 1
        pub['measures'][0]['value'] = 'changed'
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        assert len(pub['measures']) == 1
        assert pub['measures'][0]['value'] == 'changed'


    def test_add_descriptions_inline(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/work/records/%s' % self.pub_id,
                           headers=headers)
        pub = out.json
        assert len(pub['descriptions']) == 0
        pub['descriptions'].append({'type': 'abstract',
                                    'format': 'text',
                                    'value': 'An abstract'})
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        pub = out.json
        assert len(pub['descriptions']) == 1
        assert pub['descriptions'][0]['value'] == 'An abstract'
        pub['descriptions'].append({'type': 'abstract',
                                    'format': 'text',
                                    'value': 'Another abstract'})
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        pub = out.json
        assert len(pub['descriptions']) == 2
        assert pub['descriptions'][1]['value'] == 'Another abstract'
        pub['descriptions'] = list(reversed(pub['descriptions']))
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        pub = out.json
        assert len(pub['descriptions']) == 2
        assert pub['descriptions'][1]['value'] == 'An abstract'
        assert pub['descriptions'][0]['value'] == 'Another abstract'
        del pub['descriptions'][0]
        pub['descriptions'] = list(reversed(pub['descriptions']))
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        pub = out.json
        assert len(pub['descriptions']) == 1
        assert pub['descriptions'][0]['value'] == 'An abstract'

    def test_add_relations_inline(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/work/records/%s' % self.pub_id,
                           headers=headers)
        pub = out.json

        assert len(pub['relations']) == 0
        pub['relations'].append({'type': 'isPartOf',
                                 'target_id': self.another_pub_id,
                                 'starting': '1',
                                 'ending': '2',
                                 'volume': '3',
                                 'issue': '4',
                                 'location': 'here'})
        out = self.api.put_json('/api/v1/work/records/%s' % self.pub_id,
                                pub,
                                headers=headers)
        pub = out.json
        assert len(pub['relations']) == 1
        assert pub['relations'][0]['_target_name'] == 'Another Test Publication'


