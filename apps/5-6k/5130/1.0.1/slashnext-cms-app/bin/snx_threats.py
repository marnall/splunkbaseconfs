import sys
sys.path.append('../lib')

import traceback
import time
import json
import splunk.Intersplunk
import snx_utils
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from SlashNextCMS import SlashNextThreats


@Configuration()
class SnxThreatsCommand(GeneratingCommand):
    # Class variables
    # Type of stat to fetch
    stat = Option(require=False)

    # globalFilterValue (Number of days)
    globalFilterValue = Option(require=False, validate=validators.Integer())

    # The page number for API
    page = Option(require=False, validate=validators.Integer())

    # The rpp for API
    rpp = Option(require=False, validate=validators.Integer())

    # The thread ID
    threatId = Option(require=False)

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
            self.snx_logger.info('Running "snxthreats" Command')

            # Get API information
            api_config = snx_utils.get_config("slashnext.conf", "api-setup")
            self.base_url = api_config['base_url']
            self.api_key = api_config['api_key']

            self.snx_logger.info("Found API Key: {0} and Base URL: {1}".format(self.api_key, self.base_url))

            snx_threats_api = SlashNextThreats(self.api_key, self.base_url)

            if self.stat == 'recent_threats_listing':
                status, response = snx_threats_api.recent_threats(self.globalFilterValue, self.page, self.rpp)
                self.snx_logger.info("Getting Stat: {0} with globalFilterValue: {1}, page: {2} and rpp: {3}".
                                     format(self.stat, self.globalFilterValue, self.page, self.rpp))
                yield self.format_event(response)
            elif self.stat == 'threats_screenshot':
                status, response = snx_threats_api.threat_screenshot(self.threatId)
                self.snx_logger.info("Getting Stat: {0} with threatId: {1}".format(self.stat, self.threatId))
                yield self.format_event(response)
            elif self.stat == 'threat_targeted_users':
                status, response = snx_threats_api.threat_targeted_user(self.threatId)
                self.snx_logger.info("Getting Stat: {0} with threatId: {1}".format(self.stat, self.threatId))
                yield self.format_event(response)
            elif self.stat == 'vector_breakdown_urls':
                status, response = snx_threats_api.threat_url_count(self.globalFilterValue)
                self.snx_logger.info("Getting Stat: {0} with globalFilterValue: {1}".format(self.stat, self.globalFilterValue))
                yield self.format_event(response)
            elif self.stat == 'vector_breakdown_sms':
                status, response = snx_threats_api.threat_sms_count(self.globalFilterValue)
                self.snx_logger.info("Getting Stat: {0} with globalFilterValue: {1}".format(self.stat, self.globalFilterValue))
                yield self.format_event(response)
            elif self.stat == 'threat_timeline':
                status, response = snx_threats_api.threat_timeline(self.globalFilterValue, self.incidentFilterValue)
                self.snx_logger.info("Getting Stat: {0} with globalFilterValue: {1} and incidentFilterValue: {2}"
                                     .format(self.stat, self.globalFilterValue, self.incidentFilterValue))
                yield self.format_event(response)
            elif self.stat == 'threat_breakdown':
                status, response = snx_threats_api.threat_breakdown(self.globalFilterValue)
                self.snx_logger.info("Getting Stat: {0} with globalFilterValue: {1}".format(self.stat, self.globalFilterValue))
                yield self.format_event(response)
            else:
                yield {'ERROR': 'Please enter the correct value for stat'}
                return

        except Exception as e:
            stack = traceback.format_exc()
            splunk.Intersplunk.generateErrorResults(str(e))
            self.snx_logger.error(str(e) + ". Traceback: " + str(stack))


dispatch(SnxThreatsCommand, sys.argv, sys.stdin, sys.stdout, __name__)