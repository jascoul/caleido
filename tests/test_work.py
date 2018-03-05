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
        self.api.post_json('/api/v1/contributor/records',
                           {'person_id': self.john_id,
                            'work_id': self.pub_id,
                            'role': 'author',
                            'position': 0},
                           headers=headers,
                           status=201)
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



