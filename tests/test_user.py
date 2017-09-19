from webtest import TestApp
import unittest

from scributor import main

class ScributorTest(unittest.TestCase):

    def test_case(self):
        app = TestApp(main({}))
        app.get('/status', status=404)
        
