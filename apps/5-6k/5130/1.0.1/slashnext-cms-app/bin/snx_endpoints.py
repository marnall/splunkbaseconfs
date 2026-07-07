import sys
sys.path.append('../lib')

import traceback
import time
import json
import splunk.Intersplunk
import snx_utils
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from SlashNextCMS import SlashNextEndpoints


@Configuration()
class SnxEndpointsCommand(GeneratingCommand):
    # Class variables
    # Type of stat to fetch
    stat = Option(require=True)

    # globalFilterValue (Number of days)
    globalFilterValue = Option(require=False, validate=validators.Integer())

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
            self.snx_logger.info('Running "snxendpoints" Command')

            # Get API information
            api_config = snx_utils.get_config("slashnext.conf", "api-setup")
            self.base_url = api_config['base_url']
            self.api_key = api_config['api_key']

            self.snx_logger.info("Found API Key: {0} and Base URL: {1}".format(self.api_key, self.base_url))

            snx_endpoints_api = SlashNextEndpoints(self.api_key, self.base_url)

            if self.stat == 'endpoints_total':
                status, response = snx_endpoints_api.status_endpoints()
                self.snx_logger.info("Getting Stat: {0}".format(self.stat))
                yield self.format_event(response)
            elif self.stat == 'incidents_per_endpoint':
                status, response = snx_endpoints_api.endpoint_breakdown(self.globalFilterValue)
                self.snx_logger.info("Getting Stat: {0}".format(self.stat))
                yield self.format_event(response)
            elif self.stat == 'endpoints_timeline':
                status, response = snx_endpoints_api.endpoint_timeline(self.globalFilterValue, self.incidentFilterValue)
                self.snx_logger.info("Getting Stat: {0} with globalFilterValue: {1} and incidentFilterValue: {2}"
                                     .format(self.stat, self.globalFilterValue, self.incidentFilterValue))
                yield self.format_event(response)
            else:
                yield {'ERROR': 'Please enter the correct value for stat'}
                return

        except Exception as e:
            stack = traceback.format_exc()
            splunk.Intersplunk.generateErrorResults(str(e))
            self.snx_logger.error(str(e) + ". Traceback: " + str(stack))


dispatch(SnxEndpointsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
