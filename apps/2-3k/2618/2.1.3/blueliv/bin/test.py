import unittest
from StringUtils import StringUtils
from hackMapScript import afapiHackMap
from hackScript import afapiHack
from navigator import Navigator
import json
import os


class TestStringUtils(unittest.TestCase):

    def setUp(self):
        self.stringUtils = StringUtils()

    def test_replace_special_keys(self):
        self.assertEqual(self.stringUtils.clean_str('C_AND_C'),"C & C")

    def test_camel_case(self):
        self.assertEqual(self.stringUtils.clean_str('EXPLOIT KIT'),"Exploit Kit")


class TestHackMap(unittest.TestCase):

    def setUp(self):
        self.test = afapiHackMap()

    def test_hack_map(self):
        self.test.parser()


class TestHashtags(unittest.TestCase):

    def setUp(self):
        self.test = afapiHack()

    def test_hack_map(self):
        self.test.parser()


class TestNavigator(unittest.TestCase):

    def setUp(self):
        self.test = Navigator()

    def test_api_connection(self):
        result = self.test.go('https://api.blueliv.com/v1/statistics/hacktivism/byCountry')
        self.assertNotEqual(result, '')


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStringUtils)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestNavigator)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestHackMap)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestHashtags)
    unittest.TextTestRunner(verbosity=2).run(suite)