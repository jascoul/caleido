from core import BaseTest

class SchemeTypeTest(BaseTest):
    def test_retrieving_and_updating_group_types(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/schemes/types/group', headers=headers)
        # make sure there is a config entry for organisations
        value_keys = [v['key'] for v in out.json['values']]
        assert 'organisation' in value_keys
        # let's add a group type, and change some labels
        types = out.json.copy()
        types['values'].append(dict(key='publisher', label='Publisher'))
        [v for v in types['values'] if v['key'] == 'organisation'
         ][0]['label'] = 'An Organisation'
        self.api.put_json('/api/v1/schemes/types/group',
                          types,
                          headers=headers)
        out = self.api.get('/api/v1/schemes/types/group', headers=headers)
        values = dict((v['key'], v['label']) for v in out.json['values'])
        assert values['organisation'] == 'An Organisation'
        assert 'publisher' in values


    def test_retrieving_all_types(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/schemes/types', headers=headers)
        type_ids = [t['id'] for t in out.json['types']]
        assert 'group' in type_ids


    def test_repository_settings(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/schemes/settings', headers=headers)
        settings = out.json
        assert 'title' in settings
        settings['title'] = 'Unittest Repository'
        settings['foo'] = 'bar'
        self.api.put_json('/api/v1/schemes/settings',
                                settings,
                                headers=headers)
        out = self.api.get('/api/v1/schemes/settings', headers=headers)
        settings = out.json
        assert settings['title'] == 'Unittest Repository'
        assert settings['foo'] == 'bar'

