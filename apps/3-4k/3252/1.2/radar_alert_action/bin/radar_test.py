import copy
import splunk
import splunk.admin as admin
import requests
import json
import os
import sys
import unittest
from cStringIO import StringIO
from xml.dom import minidom
from radar_client import *
from radar_settings_manager import *
from radar_addon_config_handler import *

'''
    See TEST_README.md for test invocation instructions.
'''
class TestRADARClass(unittest.TestCase):
    SPLUNK_URL = os.environ.get('SPLUNK_URL')
    SPLUNK_USERNAME = os.environ.get('SPLUNK_USERNAME')
    SPLUNK_PASSWORD = os.environ.get('SPLUNK_PASSWORD')

    original_settings = None

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None
        if cls.SPLUNK_URL is None or cls.SPLUNK_USERNAME is None or cls.SPLUNK_PASSWORD is None:
            print >> sys.stderr, "Splunk creds for testing need to be set."
            sys.exit(1)

            #print >> sys.stdout, "Splunk settings found..."

        try:
            # load test JSON
            with open('radar_test.json') as data_file:
                #print >> sys.stdout, "Loading json data file..."
                cls.payload = json.load(data_file)
                #print >> sys.stdout, "Loading configuration from data file..."
                cls.config = cls.payload.get('configuration')
                cls.config[RADAR_PARAM_URL] = cls.SPLUNK_URL
        except BaseException, e:
            print >> sys.stderr, "ERROR Unable to load JSON file.  Error: %s" % e
            sys.exit(1)

        try:
            # obtain splunk session key
            url = cls.SPLUNK_URL + "/services/auth/login"
            # print >> sys.stdout, "Getting session (hitting " + url + ")..."
            result = requests.post(
                url=url,
                data={'username':cls.SPLUNK_USERNAME, 'password':cls.SPLUNK_PASSWORD},
                headers={},
                verify=False)

            cls.session_key = minidom.parseString(result.text).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue
            #print >> sys.stdout, "Session key: %s" % cls.session_key
        except BaseException, e:
            print >> sys.stderr, "ERROR Unable to obtain Splunk session.  Error: %s" % e
            sys.exit(1)
        cls.settings_manager = RadarSettingsManager(cls.SPLUNK_URL, cls.session_key)
        cls.original_settings = copy.deepcopy(cls.settings_manager.get_radar_settings())

    @classmethod
    def setUp(cls):
        settings = cls.settings_manager.get_radar_settings()
        settings[RADAR_PARAM_API_TOKEN] = None
        cls.settings_manager.update_radar_settings(settings)

    @classmethod
    def tearDown(cls):
        cls.settings_manager = RadarSettingsManager(cls.SPLUNK_URL, cls.session_key)
        cls.settings_manager.update_radar_settings(cls.original_settings)


class TestRADARPayload(TestRADARClass):
    @classmethod
    def setUpClass(cls):
        super(TestRADARPayload, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestRADARPayload, cls).tearDownClass()

    ##############################
    # RadarSettingsManager tests #
    ##############################
    def test_get_radar_settings_empty_conf_and_token(self):
        # GIVEN an empty conf and no saved token
        self.settings_manager._get_service_conf = lambda: MockConf({})
        self.settings_manager._get_radar_api_token = lambda settings: None

        # WHEN I get the settings
        settings = self.settings_manager.get_radar_settings()

        # THEN the only setting I get is the defaulted SSL flag
        self.assertDictEqual(settings, {
            RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS: True,
        })

    def test_get_radar_settings_translate_bool(self):
        # GIVEN a conf that specifies '0' for the SSL flag
        self.settings_manager._get_service_conf = lambda: MockConf({
            'param.skip_verify_ssl_cert_for_splunk_rest_calls': '0'
        })
        self.settings_manager._get_radar_api_token = lambda settings: None

        # WHEN I get the settings
        settings = self.settings_manager.get_radar_settings()

        # THEN the SSL flag is translated to False
        self.assertDictEqual(settings, {
            RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS: False,
        })

    def test_get_radar_settings(self):
        # GIVEN a populated conf, and some saved token
        self.settings_manager._get_service_conf = lambda: MockConf({'param.foo': "   bar\n ", 'baz':"ignored"})
        self.settings_manager._get_radar_api_token = lambda settings: "bogus-token"

        # WHEN I get the settings
        settings = self.settings_manager.get_radar_settings()

        # THEN matching params are translated, the SSL flag is defaulted, and the token is included.
        self.assertDictEqual(settings, {
            'foo': "bar", # 'param.' trimmed from key, whitespace from value
            RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS: True,
            RADAR_PARAM_API_TOKEN: "bogus-token",
        })

    def test_disable_self_signed(self):
        # GIVEN existing settings with self-signed certs allowed
        settings = self.settings_manager.get_radar_settings()
        settings[RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS] = True
        self.settings_manager.update_radar_settings(settings)
        
        # WHEN we clear the token and update
        settings[RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS] = False
        self.settings_manager.update_radar_settings(settings)

        # THEN the retrieved settings have no token
        updated_settings = self.settings_manager.get_radar_settings()
        self.assertFalse(updated_settings.get(RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS))
        self.assertEquals(updated_settings.get(RADAR_PARAM_API_TOKEN), ERROR_SPLUNK_SSL_VERIFICATION)

    def test_enable_self_signed(self):
        # GIVEN existing settings with self-signed certs disallowed
        settings = self.settings_manager.get_radar_settings()
        settings[RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS] = False
        self.settings_manager.update_radar_settings(settings)
        
        # WHEN we clear the token and update
        settings[RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS] = True
        self.settings_manager.update_radar_settings(settings)

        # THEN the retrieved settings have no token
        updated_settings = self.settings_manager.get_radar_settings()
        self.assertTrue(updated_settings.get(RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS))
        self.assertIsNone(updated_settings.get(RADAR_PARAM_API_TOKEN))

    def test_update_radar_settings_saves_token(self):
        # GIVEN existing settings
        self.settings_manager._get_service_conf = lambda: MockConf({})

        # WHEN I save settings that include a new token
        token = "T" * 50
        new_settings = {
            RADAR_PARAM_API_TOKEN: token
        }
        saved = {}
        def save(new, old, test=self, saved=saved):
            test.assertDictEqual(new, new_settings)
            saved.setdefault(token, True)
        self.settings_manager.save_radar_api_token = save

        self.settings_manager.update_radar_settings(new_settings)

        # THEN the token gets saved
        self.assertTrue(saved[token])

    def test_update_radar_settings_posts_cleartext_concerns_to_service(self):
        # GIVEN existing settings
        conf = MockConf({})
        self.settings_manager._get_service_conf = lambda conf=conf: conf
        
        # WHEN I save settings for everything other than the token
        new_settings = {
            RADAR_PARAM_URL: "example.com",
            RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS: '1',
            RADAR_PARAM_INCIDENT_NAME: "Loose lips",
            RADAR_PARAM_INCIDENT_DESCRIPTION: "Sink ships",
        }
        self.settings_manager.update_radar_settings(new_settings)

        # THEN all that stuff gets saved
        self.assertDictEqual(conf.posted, {
            'param.'+RADAR_PARAM_URL: "example.com",
            'param.'+RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS: 1,
            'param.'+RADAR_PARAM_INCIDENT_NAME: "Loose lips",
            'param.'+RADAR_PARAM_INCIDENT_DESCRIPTION: "Sink ships",
        })

    def test_save_radar_api_token(self):
        # GIVEN no token saved
        reqs = MockRequests()
        self.settings_manager.requests = reqs
        old_settings = {}
        
        # WHEN I save a token with three chunks' worth of characters
        chunks = map(lambda x: x * SPLUNK_PASSWORD_CHUNK_SIZE, ['A', 'B', 'C'])
        token = ''.join(chunks)
        new_settings = { RADAR_PARAM_API_TOKEN: token }
        self.settings_manager.save_radar_api_token(new_settings, old_settings)

        # THEN three chunks are posted individually
        self.assertEquals(len(reqs.deleted), 0)
        self.assertEquals(len(reqs.posted), 3)
        for i in range(len(reqs.posted)):
            p = reqs.posted[i]
            fmt = "%s/servicesNS/nobody/radar_alert_action/storage/passwords/radar_api_token_chunk_%d?output_mode=json"
            self.assertEquals(p['url'], fmt % (self.SPLUNK_URL, i))
            self.assertTrue(p['headers']['Authorization'].startswith('Splunk '))
            self.assertFalse(p['verify'])
            self.assertEquals(p['data'], {'password':chunks[i]})

    def test_delete_radar_api_token(self):
        # GIVEN an existing saved token
        reqs = MockRequests()
        self.settings_manager.requests = reqs
        chunkA, chunkB, chunkC = map(lambda x: x * 3, ['D', 'E', 'F'])
        token = chunkA + chunkB + chunkC
        old_settings = { RADAR_PARAM_API_TOKEN: token }
        
        # WHEN I save new settings with no token
        new_settings = {}
        self.settings_manager.save_radar_api_token(new_settings, old_settings)

        # THEN three chunks are deletedindividually
        self.assertEquals(len(reqs.posted), 0)
        self.assertEquals(len(reqs.deleted), 3)
        for i in range(len(reqs.deleted)):
            d = reqs.deleted[i]
            fmt = "%s/servicesNS/nobody/radar_alert_action/storage/passwords/radar_api_token_chunk_%d?output_mode=json"
            self.assertEquals(d['url'], fmt % (self.SPLUNK_URL, i))
            self.assertTrue(d['headers']['Authorization'].startswith('Splunk '))
            self.assertFalse(d['verify'])

    def test_get_radar_api_token(self):
        # GIVEN an existing saved token
        chunks = map(lambda x: x * 250, ['A', 'B', 'C'])
        token = ''.join(chunks)
        reqs = MockRequests(map(lambda chunk: '{"entry":[{"content":{"clear_password":"%s"}}]}' % chunk, chunks))
        self.settings_manager.requests = reqs

        # WHEN I get the token
        got = self.settings_manager._get_radar_api_token({})

        # THEN I get the saved token value
        self.assertEquals(got, token)
        self.assertEquals(len(reqs.get_args), 3)

    def test_clear_stored_radar_api_token(self):
        # GIVEN our existing settings
        settings = self.settings_manager.get_radar_settings()

        # WHEN we clear the token and update
        settings[RADAR_PARAM_API_TOKEN] = None
        self.settings_manager.update_radar_settings(settings)

        # THEN the retrieved settings have no token
        updated_settings = self.settings_manager.get_radar_settings()
        self.assertIsNone(updated_settings.get(RADAR_PARAM_API_TOKEN))

    def test_store_radar_api_token_after_being_empty(self):
        # GIVEN existing settings with no token set
        settings = self.settings_manager.get_radar_settings()
        settings[RADAR_PARAM_API_TOKEN] = None
        self.settings_manager.update_radar_settings(settings)

        # WHEN we update them with a provided token
        token = 'X' * 538
        settings = self.settings_manager.get_radar_settings()
        settings[RADAR_PARAM_API_TOKEN] = token
        self.settings_manager.update_radar_settings(settings)

        # THEN the token appears when we fetch the settings
        updated_settings = self.settings_manager.get_radar_settings()
        self.assertEqual(updated_settings.get(RADAR_PARAM_API_TOKEN), token)

    def test_get_radar_api_token_from_storage(self):
        # GIVEN settings configured with an API token
        settings = self.settings_manager.get_radar_settings()
        token = 'Y' * 538
        settings[RADAR_PARAM_API_TOKEN] = token
        self.settings_manager.update_radar_settings(settings)

        # WHEN we call _get_radar_api_token
        actual = self.settings_manager._get_radar_api_token(settings)

        # THEN the token has the expected value
        self.assertEqual(token, actual)


    #####################
    # RadarClient tests #
    #####################

    def test_validate_radar_settings__happy_case(self):
        # GIVEN a RADAR client that reports scopes including 'incidents-write'
        cli = RadarClient(dict())
        cli.get_scopes = lambda: [ 'crush-moon', 'incidents-write', 'redirect-comet' ]

        # THEN validation succeeds
        self.assertTrue(cli.validate_radar_settings());

    def test_validate_radar_settings__missing_incidents_write(self):
        # GIVEN a RADAR client that reports scopes NOT including 'incidents-write'
        cli = RadarClient(dict())
        cli.get_scopes = lambda: [ 'redirect-moon', 'incidents-read', 'crush-comet' ]

        # THEN validation succeeds
        self.assertFalse(cli.validate_radar_settings());


    #################################
    # RadarAddOnConfigHandler tests #
    #################################

    def test_handle_list_populates_values_from_settings(self):
        # GIVEN a handler and some stored settings
        RadarAddOnConfigHandler.getSessionKey = lambda _self: self.session_key
        sys.stdin.close()
        handler = RadarAddOnConfigHandler(RadarAddOnConfigHandler, admin.CONTEXT_APP_ONLY)
        settings = {
            RADAR_PARAM_API_TOKEN: 'ABC123BBD',
            RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS: '1',
        }
        handler.settings_manager.get_radar_settings = lambda: settings

        # WHEN we call handleList() with a confInfo dict
        confInfo = { RADAR_PACKAGE: dict() }
        handler.handleList(confInfo)

        # THEN the settings are copied into the right part of the confInfo dict 
        self.assertDictContainsSubset(settings, confInfo[RADAR_PACKAGE])
    
    def test_handle_edit_stores_values(self):
        # GIVEN a handler
        RadarAddOnConfigHandler.getSessionKey = lambda _self: self.session_key
        sys.stdin.close()
        handler = RadarAddOnConfigHandler(RadarAddOnConfigHandler, admin.CONTEXT_APP_ONLY)
        saved_settings = dict()
        handler.settings_manager.get_radar_settings = lambda: saved_settings
        handler.settings_manager.update_radar_settings = lambda d: saved_settings.update(d)
        handler._validateRADARSettings = lambda _: None

        # WHEN we call handleEdit() with callerArgs including RADAR config data
        handler.callerArgs = admin.ArgsInfo()
        handler.callerArgs.id = RADAR_PACKAGE
        handler.callerArgs.data = { # Values wrapped in lists
            RADAR_PARAM_API_TOKEN: ['ABC123BBD'],
            RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS: '0'
        }
        handler.handleEdit(dict())

        # THEN the config data is passed through to to the settings manager to be saved.
        expected = { # Values _not_ wrapped in lists
            RADAR_PARAM_API_TOKEN: 'ABC123BBD',
            RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS: False
        }
        self.assertDictEqual(expected, saved_settings)

    def test_handle_edit_allows_empty_payload(self):
        # GIVEN a handler
        RadarAddOnConfigHandler.getSessionKey = lambda _self: self.session_key
        sys.stdin.close()
        handler = RadarAddOnConfigHandler(RadarAddOnConfigHandler, admin.CONTEXT_APP_ONLY)
        saved_settings = dict()
        handler.settings_manager.get_radar_settings = lambda: saved_settings
        handler.settings_manager.update_radar_settings = lambda d: saved_settings.update(d)

        # WHEN we call handleEdit() with callerArgs that contain an API token that is None
        handler.handleEdit(dict())

        # THEN the config data is passed through to to the settings manager to be saved.
        self.assertDictEqual(dict(), saved_settings)


    #######################
    # Splunk config tests #
    #######################

    def test_default_session(self):
        self.assertNotEqual(self.config.get('session_key'), "SET_SESSION_KEY")


    ######################
    # RADAR config tests #
    ######################

    def test_radar_url(self):
        self.assertNotEqual(self.config.get(RADAR_PARAM_URL), "SET_RADAR_URL")

    def test_radar_api_token(self):
        self.assertNotEqual(self.config.get(RADAR_PARAM_API_TOKEN), "SET_RADAR_API_TOKEN")


    ######################
    # RADAR params tests #
    ######################

    def test_result(self):
        self.assertIsNone(self.payload.get('result'))


class MockConf:
    def __init__(self, data):
        self.data = data
        self.posted = dict()

    def content(self):
        return self.data

    def post(self, **data):
        self.posted = data


class MockResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


class MockRequests:
    def __init__(self, get_resps=None):
        self.get_args = []
        self.get_resps = get_resps
        self.posted = []
        self.deleted = []
    
    def get(self, **kwargs):
        self.get_args.append(kwargs)
        resp = self.get_resps.pop(0)
        return MockResponse(200, resp)

    def post(self, **kwargs):
        self.posted.append(kwargs)

    def delete(self, **kwargs):
        self.deleted.append(kwargs)


if __name__ == '__main__':
    unittest.main()
