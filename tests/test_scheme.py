from core import BaseTest
        
class SchemeTypeTest(BaseTest):
    def test_retrieving_and_updating_actor_types(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/schemes/types/actor', headers=headers)
        # make sure there is a config entry for individuals
        value_keys = [v['key'] for v in out.json['values']]
        assert 'individual' in value_keys
        # let's add an actor type, and change some labels
        types = out.json.copy()
        types['values'].append(dict(key='publisher', label='Publisher'))
        [v for v in types['values']
         if v['key'] == 'individual'][0]['label'] = 'An Individual'
        self.api.put_json('/api/v1/schemes/types/actor',
                          types,
                          headers=headers)
        out = self.api.get('/api/v1/schemes/types/actor', headers=headers)
        values = dict((v['key'], v['label']) for v in out.json['values'])
        assert values['individual'] == 'An Individual'
        assert 'individual' in values
        
        
    def test_retrieving_all_types(self):
        headers = dict(Authorization='Bearer %s' % self.admin_token())
        out = self.api.get('/api/v1/schemes/types', headers=headers)
        type_ids = [t['id'] for t in out.json['types']]
        assert 'actor' in type_ids
        
