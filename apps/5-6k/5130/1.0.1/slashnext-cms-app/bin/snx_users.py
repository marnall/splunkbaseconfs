import sys
sys.path.append('../lib')

import traceback
import time
import json
import splunk.Intersplunk
import snx_utils
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from SlashNextCMS import SlashNextUsers


@Configuration()
class SnxUsersCommand(GeneratingCommand):
    # Class variables
    # Type of stat to fetch
    stat = Option(require=True)

    # globalFilterValue (Number of days)
    globalFilterValue = Option(require=True, validate=validators.Integer())

    # incidentFilterValue
    incidentFilterValue = Option(require=False)

    # Internal variables
    api_key = None
    base_url = None
    snx_logger = None

    def format_event(self, raw_json):
        event = dict()
        event['_time'] = time.time()
        event['_raw'] = json.dumps(raw_json)

        for (key, val) in raw_json.items():
            event[key] = val

        return event

    def generate(self):
        # Initial Settings for logging and credentials
        try:
            # Accquire the logger
            self.snx_logger = snx_utils.setup_logging()
            self.snx_logger.info('Running "snxusers" Command')

            # Get API information
            api_config = snx_utils.get_config("slashnext.conf", "api-setup")
            self.base_url = api_config['base_url']
            self.api_key = api_config['api_key']

            self.snx_logger.info("Found API Key: {0} and Base URL: {1}".format(self.api_key, self.base_url))

            snx_users_api = SlashNextUsers(self.api_key, self.base_url)

            if self.stat == 'active_users_count':
                status, response = snx_users_api.active_user_count(self.globalFilterValue)
                yield self.format_event(response)
            elif self.stat == 'phishing_breakdown':
                status, response = snx_users_api.phishing_incident_count(self.globalFilterValue)
                yield self.format_event(response)
            elif self.stat == 'top_affected_groups':
                status, response = snx_users_api.affected_groups(self.globalFilterValue)
                yield self.format_event(response)
            elif self.stat == 'incidents_timeline_graph':
                status, response = snx_users_api.incident_timeline(self.globalFilterValue, self.incidentFilterValue)
                yield self.format_event(response)
            elif self.stat == 'recent_incidents':
                status, response = snx_users_api.recent_incidents(self.globalFilterValue)
                yield self.format_event(response)
            elif self.stat == 'high_risk_users':
                status, response = snx_users_api.high_risk_users(self.globalFilterValue)
                yield self.format_event(response)
            else:
                yield {'ERROR': 'Please enter the correct value for stat'}
                return

        except Exception as e:
            stack = traceback.format_exc()
            splunk.Intersplunk.generateErrorResults(str(e))
            self.snx_logger.error(str(e) + ". Traceback: " + str(stack))


dispatch(SnxUsersCommand, sys.argv, sys.stdin, sys.stdout, __name__)
