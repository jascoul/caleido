import os

import transaction

from core import BaseTest
from caleido.models import User

class ContributorWebTest(BaseTest):
    def setUp(self):
        super(ContributorWebTest, self).setUp()
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
        out = self.api.post_json('/api/v1/group/records',
                                 {'international_name': 'Department A',
                                  'type': 'organisation'},
                                 headers=headers,
                                 status=201)
        self.dept_id = out.json['id']
        out = self.api.post_json('/api/v1/work/records',
                                 {'title': 'Test Publication',
                                  'type': 'article',
                                  'issued': '2018-02-27'},
                                 headers=headers,
                                 status=201)
        self.pub_id = out.json['id']


    def test_contributor_crud_as_admin(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.post_json('/api/v1/contributor/records',
                                 {'person_id': self.john_id,
                                  'work_id': self.pub_id,
                                  'role': 'author',
                                  'position': 0},
                                 headers=headers,
                                 status=201)
        last_id = out.json['id']
        assert out.json['person_id'] == self.john_id
        self.api.put_json('/api/v1/contributor/records/%s' % last_id,
                          {'id': last_id,
                           'person_id': self.jane_id,
                           'work_id': self.pub_id,
                           'role': 'author',
                           'position': 0},
                          headers=headers,
                          status=200)
        out = self.api.get('/api/v1/contributor/records/%s' % last_id,
                          headers=headers,
                          status=200)
        assert out.json['person_id'] == self.jane_id
        self.api.delete('/api/v1/contributor/records/%s' % last_id,
                        headers=headers,
                        status=200)
        self.api.get('/api/v1/contributor/records/%s' % last_id,
                          headers=headers,
                          status=404)


    def test_contributor_bulk_import(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        records = {'records': [
            {'id': 1,
             'person_id': 1,
             'work_id': 1,
             'position': 0,
             'role': 'author'},
            {'id': 2,
             'person_id': 2,
             'work_id': 1,
             'position': 1,
             'role': 'author'},
             ]}
        # bulk add records
        out = self.api.post_json('/api/v1/contributor/bulk',
                                 records,
                                 headers=headers,
                                 status=201)
        assert out.json['status'] == 'ok'
        out = self.api.get('/api/v1/contributor/records/2', headers=headers)
        assert out.json['person_id'] == 2
        records['records'][1]['group_id'] = 1
        records['records'][1]['person_id'] = None

        # bulk update records
        out = self.api.post_json('/api/v1/contributor/bulk',
                                 records,
                                 headers=headers,
                                 status=201)
        assert out.json['status'] == 'ok'
        out = self.api.get('/api/v1/contributor/records/2', headers=headers)
        assert out.json['group_id'] == 1
        assert out.json.get('person_id') is None
