import httplib
import json
import os
import requests
import sys

import splunklib.client as client
from urlparse import urlparse

RADAR_ADD_ON_PATH = 'servicesNS/nobody/radar_alert_action'

RADAR_PARAM_URL = 'radar_url'
RADAR_PARAM_API_TOKEN = 'radar_api_token'
RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS = 'skip_verify_ssl_cert_for_splunk_rest_calls'
RADAR_PARAM_INCIDENT_NAME = 'radar_incident_name'
RADAR_PARAM_INCIDENT_DESCRIPTION = 'radar_incident_description'

ERROR_SPLUNK_SSL_VERIFICATION = "Unable to access token: SSL certificate verification failure"

SPLUNK_PASSWORD_CHUNK_SIZE = 255 # Constraint from Splunk password storage impl
NUM_PASSWORD_CHUNKS = 3          # Takes 3 chunks to fit a RADAR API token (~538 chars)

class RadarSettingsManager:

    def __init__(self, server_uri, session_key, app=None, owner=None):
        self.server_uri = server_uri
        self.session_key = session_key
        self.requests = requests
        parts = urlparse(server_uri)
        try:
            self.service = client.connect(host = parts.hostname,
                                          port = parts.port,
                                          scheme = parts.scheme,
                                          token = session_key,
                                          app = app)
        except BaseException, e:
            print >> sys.stderr, "Splunk client could not connect due to %s: %s" % (
                e.__class__.__name__, e)


    def splunkd_auth_header(self):
        return {'Authorization': 'Splunk ' + self.session_key}

    
    def get_radar_settings(self):
        """
        Fetch all settings from Splunk's storage.
        """
        radar_settings = dict()
        content = self._get_service_conf().content()
        for k,v in content.items():
            if k.startswith('param.'):
                k = k[len('param.'):]
                v = v.strip()
                if k == RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS:
                    v = bool(int(v))
                radar_settings[k] = v
        radar_settings.setdefault(RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS, True)

        token = self._get_radar_api_token(radar_settings)
        if token:
            radar_settings[RADAR_PARAM_API_TOKEN] = token

        return radar_settings
    
    
    def update_radar_settings(self, new_settings):
        """
        Persist new_settings in Splunk's config store.  This includes storing the RADAR API token
        to Splunk's password store, broken into chunks to circumvent the length limit.
        """
        old_settings = self.get_radar_settings()

        # encrypted storage for RADAR API token -- do this first in case it fails due to SSL cert verification failure
        self.save_radar_api_token(new_settings, old_settings)

        # cleartext configuration concerns
        cleartext_entries = {
            RADAR_PARAM_URL: lambda x: x,
            RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS: lambda x: int(x),
            RADAR_PARAM_INCIDENT_NAME: lambda x: x,
            RADAR_PARAM_INCIDENT_DESCRIPTION: lambda x: x
        }
        data = { 'param.{0}'.format(param): f(new_settings[param])
                 for param, f in cleartext_entries.items() if new_settings.has_key(param) }
        self._get_service_conf().post(**data)
    

    def _get_service_conf(self):
        return self.service.confs['alert_actions']['radar']


    def save_radar_api_token(self, new_settings, old_settings):
        """
        Encrypt token before storing in plaintext config file.  Splunk's password store truncates
        values to 255 characters; since RADAR API tokens are 538 characters (give or take), we need
        to break them into three chunks to store everything.
        """
        old_token = old_settings.get(RADAR_PARAM_API_TOKEN, None)
        new_token = new_settings.get(RADAR_PARAM_API_TOKEN, None)
        if new_token == old_token or new_token == ERROR_SPLUNK_SSL_VERIFICATION:
            return
        for i in range(NUM_PASSWORD_CHUNKS):
            offset = i * SPLUNK_PASSWORD_CHUNK_SIZE
            url = self._get_radar_api_token_uri(i)
            headers = self.splunkd_auth_header()
            verify = self._should_verify_ssl(new_settings)
            if new_token:
                chunk = new_token[offset:offset + SPLUNK_PASSWORD_CHUNK_SIZE]
                result = self.requests.post(url=url, data={ 'password': chunk }, headers=headers, verify=verify)
            else:
                self.requests.delete(url=url, headers=headers, verify=verify)

    
    def _get_radar_api_token(self, radar_settings):
        """
        Retrieve (and reconstitute) stored RADAR API token from Splunk's encrypted store.
        """
        try:
            api_token = ''
            for i in range(NUM_PASSWORD_CHUNKS):
                result = self.requests.get(url=self._get_radar_api_token_uri(i),
                                           headers=self.splunkd_auth_header(),
                                           verify=self._should_verify_ssl(radar_settings))
                if result.status_code != httplib.OK:
                    print >> sys.stderr, \
                        "Unexpected HTTP response retrieving RADAR API Token: %d %s" % \
                        (result.status_code, result.reason)
                    return None
                chunk = json.loads(result.text)['entry'][0]['content']['clear_password']
                api_token += chunk
            return api_token or None
        except requests.exceptions.SSLError, e:
            return ERROR_SPLUNK_SSL_VERIFICATION
        except BaseException, e:
            print >> sys.stderr, "Exception occurred when getting RADAR API token: %s" % e
            return "Unable to access token: see splunkd.log"
    

    def _should_verify_ssl(self, radar_settings):
        return not radar_settings.get(RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS, True)
        

    def _get_radar_api_token_uri(self, chunk_number):
        return "%s/%s/storage/passwords/%s_chunk_%d?output_mode=json" % (
            self.server_uri, RADAR_ADD_ON_PATH, RADAR_PARAM_API_TOKEN, chunk_number)
