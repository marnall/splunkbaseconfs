import sys
sys.path.append('../lib')

import requests
import snx_utils
import traceback
import time
import json
import splunk.Intersplunk
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration()
class SnxHostUrlsCommand(GeneratingCommand):
    # Class variables
    # Number of URLs to fetch
    urls_limit = Option(require=True, validate=validators.Integer())

    # Host against which URLs are to be fetched
    host = Option(require=True)

    # Internal variables
    api_key = None
    base_url = None
    snx_logger = None

    def format_event(self, event, raw_json, action='new'):
        if action == 'new':
            event['_time'] = time.time()
            event['_raw'] = json.dumps(raw_json)

        event['url'] = raw_json.get('url')
        event['scanId'] = raw_json.get('scanId')
        event['verdict'] = raw_json.get('threatData').get('verdict')
        event['threat_status'] = raw_json.get('threatData').get('threatStatus')
        event['threat_type'] = raw_json.get('threatData').get('threatType')
        event['threat_name'] = raw_json.get('threatData').get('threatName')
        event['first_seen'] = raw_json.get('threatData').get('firstSeen')
        event['last_seen'] = raw_json.get('threatData').get('lastSeen')

        if 'finalUrl' in raw_json:
            event['finalUrl'] = raw_json.get('finalUrl')
        else:
            event['finalUrl'] = None

        if 'landingUrl' in raw_json:
            event['landingUrl'] = raw_json.get('landingUrl').get('url')
            event['landingUrl_scanId'] = raw_json.get('landingUrl').get('scanId')
            event['landingUrl_verdict'] = raw_json.get('landingUrl').get('threatData').get('verdict')
            event['landingUrl_threatStatus'] = raw_json.get('landingUrl').get('threatData').get('threatStatus')
            event['landingUrl_threatType'] = raw_json.get('landingUrl').get('threatData').get('threatType')
            event['landingUrl_threatName'] = raw_json.get('landingUrl').get('threatData').get('threatName')
            event['landingUrl_firstSeen'] = raw_json.get('landingUrl').get('threatData').get('firstSeen')
            event['landingUrl_lastSeen'] = raw_json.get('landingUrl').get('threatData').get('lastSeen')
        else:
            event['landingUrl'] = None
            event['landingUrl_scanId'] = None
            event['landingUrl_verdict'] = None
            event['landingUrl_threatStatus'] = None
            event['landingUrl_threatType'] = None
            event['landingUrl_threatName'] = None
            event['landingUrl_firstSeen'] = None
            event['landingUrl_lastSeen'] = None

        return event

    def generate(self):
        # Initial Settings for logging and credentials
        try:
            # Accquire the logger
            self.snx_logger = snx_utils.setup_logging()
            self.snx_logger.info('Running "snxhosturls" Command')

            # Get API information
            api_config = snx_utils.get_config("slashnext.conf", "api-setup")
            self.base_url = api_config['base_url']
            self.api_key = api_config['api_key']

            self.snx_logger.info("Checking Host URLs for Host: {0} with Limit: {1}".format(self.host, self.urls_limit))

            # Make a call to SlashNext - OTI Endpoint
            host_report_api = self.base_url + '/oti/v1/host/report'
            ep_params = {
                'authkey': self.api_key,
                'host': self.host,
                'page': 1,
                'rpp': self.urls_limit
            }

            response = requests.post(host_report_api, ep_params)
            if response.ok:
                data = response.json()
                if data.get('errorNo') == 0:
                    msg = '"snxhosturls" Successful'
                    self.snx_logger.info(msg)

                    # Iterate through all the URLs and yield events after formatting
                    for url in data.get('urlDataList'):
                        new_event = {}
                        # Yield the new event
                        yield self.format_event(new_event, url, action='new')
                else:
                    msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                    self.snx_logger.error(msg)
                    # Yield and error and return
                    yield {'ERROR': msg}
                    return
            else:
                msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(response.reason)
                self.snx_logger.error(msg)
                # Yield and error and return
                yield {'ERROR': msg}
                return

        except Exception as e:
            stack = traceback.format_exc()
            # splunk.Intersplunk.generateErrorResults(str(e))
            self.snx_logger.error(str(e) + ". Traceback: " + str(stack))


dispatch(SnxHostUrlsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
