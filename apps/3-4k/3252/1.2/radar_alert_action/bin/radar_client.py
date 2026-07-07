import httplib
import json
import requests
import sys

from datetime import datetime
from radar_settings_manager import *

class RadarClient:

    def __init__(self, radar_settings):
        self.radar_settings = radar_settings


    def validate_radar_settings(self):
        """
        Confirm RADAR endpoint and API token are valid and can be used to create incidents.
        """
        return 'incidents-write' in self.get_scopes()
    

    def get_scopes(self):
        """
        Fetch authorization data for given API token; return its allowed scopes.
        """
        uri = self.radar_uri('authorization')
        r = requests.get(
            url=uri,
            headers=self._build_headers(),
            verify=not self.skip_ssl_cert_verification_for_radar_rest_calls(),
            timeout=10)
        if r.status_code != 200:
            print >> sys.stderr, "ERROR Got response (%s %s) from server for URI %s" % (
                r.status_code, r.reason, uri)
            return [] # Will result in validation failure for lack of 'incident-writes' scope.
        try:
            return r.json().get('scopes')
        except ValueError, e:
            print >> sys.stderr, "ERROR Could not decode JSON from '%s': %s" % (r.text, e)
            raise
    
    
    def radar_uri(self, endpoint):
        return self.radar_settings[RADAR_PARAM_URL] + endpoint


    def create_incident(self, config, results_uri, search_name):
        has_incident_name = len(config.get(RADAR_PARAM_INCIDENT_NAME, ''))
        if not search_name:
            search_name = "manual trigger"
            if not has_incident_name:
                config[RADAR_PARAM_INCIDENT_NAME] = "Splunk Alert (manually triggered)"
        elif not has_incident_name:
            print >> sys.stderr, "WARN Cannot create RADAR incident without a name.  Providing a basic default."
            config[RADAR_PARAM_INCIDENT_NAME] = "Splunk Alert from '%s'" % search_name
        try:
            body = {
                "name": config[RADAR_PARAM_INCIDENT_NAME].strip(),
                "description": config.get(RADAR_PARAM_INCIDENT_DESCRIPTION, ""),
                "discovery_date": datetime.now().strftime('%Y-%m-%d'),
                "channel": {
                    "source": "splunk",
                    "uri": results_uri
                }
            }
            result = requests.post(url=self.radar_uri("incidents"),
                                   data=json.dumps(body),
                                   headers=self._build_headers(),
                                   verify=not self.skip_ssl_cert_verification_for_radar_rest_calls())
            if result.status_code == httplib.CREATED:
                print >> sys.stderr, "INFO RADAR created incident %s for alert '%s'" % (json.loads(result.text)["id"],
                                                                                        search_name)
            else:
                print >> sys.stderr, "ERROR Unexpected HTTP response code (%d) creating incident: %s" % \
                    (result.status_code, result.reason)
        except BaseException, e:
            print >> sys.stderr, "ERROR Error posting incident: (%s) %s" % (e.__class__.__name__, e)


    def _build_headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/vnd.radarfirst.v1+json",
            "Authorization": "Bearer " + self.radar_settings[RADAR_PARAM_API_TOKEN]
        }
        

    @classmethod
    def skip_ssl_cert_verification_for_radar_rest_calls(cls):
        return 'RADAR_API_SKIP_SSL_VERIFY' in os.environ
