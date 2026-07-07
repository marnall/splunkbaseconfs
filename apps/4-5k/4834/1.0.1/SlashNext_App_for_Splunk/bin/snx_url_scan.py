import sys
sys.path.append('../lib')

import requests
import snx_utils
import traceback
import time
import json
import splunk.Intersplunk
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class SnxUrlScanCommand(StreamingCommand):
    # Class variables
    url = Option(require=False)

    url_field = Option(require=False, validate=validators.Fieldname())

    # Internal variables
    api_key = None
    base_url = None
    snx_logger = None

    def format_event(self, event, raw_json, action='new'):
        if action == 'new':
            event['_time'] = time.time()
            event['_raw'] = json.dumps(raw_json)

        event['url'] = raw_json.get('urlData').get('url')
        event['url_scanId'] = raw_json.get('urlData').get('scanId')
        event['url_verdict'] = raw_json.get('urlData').get('threatData').get('verdict')
        event['url_threatStatus'] = raw_json.get('urlData').get('threatData').get('threatStatus')
        event['url_threatType'] = raw_json.get('urlData').get('threatData').get('threatType')
        event['url_threatName'] = raw_json.get('urlData').get('threatData').get('threatName')
        event['url_firstSeen'] = raw_json.get('urlData').get('threatData').get('firstSeen')
        event['url_lastSeen'] = raw_json.get('urlData').get('threatData').get('lastSeen')

        if 'finalUrl' in raw_json.get('urlData'):
            event['finalUrl'] = raw_json.get('urlData').get('finalUrl')
        else:
            event['finalUrl'] = None

        if 'landingUrl' in raw_json.get('urlData'):
            event['landingUrl'] = raw_json.get('urlData').get('landingUrl').get('url')
            event['landingUrl_scanId'] = raw_json.get('urlData').get('landingUrl').get('scanId')
            event['landingUrl_verdict'] = raw_json.get('urlData').get('landingUrl').get('threatData').get('verdict')
            event['landingUrl_threatStatus'] = raw_json.get('urlData').get('landingUrl')\
                .get('threatData').get('threatStatus')
            event['landingUrl_threatType'] = raw_json.get('urlData').get('landingUrl')\
                .get('threatData').get('threatType')
            event['landingUrl_threatName'] = raw_json.get('urlData').get('landingUrl')\
                .get('threatData').get('threatName')
            event['landingUrl_firstSeen'] = raw_json.get('urlData').get('landingUrl')\
                .get('threatData').get('firstSeen')
            event['landingUrl_lastSeen'] = raw_json.get('urlData').get('landingUrl')\
                .get('threatData').get('lastSeen')
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

    def stream(self, records):
        # Initial Settings for logging and credentials
        try:
            # Accquire the logger
            self.snx_logger = snx_utils.setup_logging()
            self.snx_logger.info('Running "snxurlscan" Command')

            # Get API information
            api_config = snx_utils.get_config("slashnext.conf", "api-setup")
            self.base_url = api_config['base_url']
            self.api_key = api_config['api_key']

            if self.url is not None:
                # We perform a URL Scan command
                self.snx_logger.info('Checking URL Scan for URL: {0}'.format(self.url))

                # Make a call to SlashNext - OTI Endpoint
                url_scan_api = self.base_url + '/oti/v1/url/scan'
                ep_params = {
                    'authkey': self.api_key,
                    'url': self.url
                }

                response = requests.post(url_scan_api, ep_params)
                if response.ok:
                    data = response.json()
                    if data.get('errorNo') == 0:
                        msg = '"snxurlscan" Successful'
                        self.snx_logger.info(msg)
                        new_event = {}
                        yield self.format_event(new_event, data, action='new')

                    elif data.get('errorNo') == 1:
                        msg = 'Your URL Scan request is submitted to the cloud and may take up-to 60 ' \
                              'seconds to complete. Please check back later using "snxurlscanreport" ' \
                              'action with scan_id = {0} or running the same "snxurlscan" action one more time'\
                            .format(data.get('urlData').get('scanId'))
                        self.snx_logger.error(msg)
                        yield {'ERROR': msg}
                        return

                    else:
                        msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                        self.snx_logger.error(msg)
                        # Return Error
                        yield {'ERROR': msg}
                        return
                else:
                    msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(response.reason)
                    self.snx_logger.error(msg)
                    # Return Error
                    yield {'ERROR': msg}
                    return

            elif self.url_field is not None:
                # User passed a field in url_field value so we iterate over all the events passed
                # from previous command in the pipeline
                for record in records:
                    # Get the URL value from the field in the events
                    url = record.get(str(self.url_field))
                    if url is None:
                        msg = 'No URL value found in the specified field'
                        record['snx-error'] = msg
                        self.snx_logger.error(msg)

                    else:
                        # Call URL Scan for each URL in the events
                        self.snx_logger.info('Checking URL Scan for URL: {0}'.format(url))

                        # Make a call to SlashNext - OTI Endpoint
                        url_scan_api = self.base_url + '/oti/v1/url/scan'
                        ep_params = {
                            'authkey': self.api_key,
                            'url': url
                        }

                        response = requests.post(url_scan_api, ep_params)
                        if response.ok:
                            data = response.json()
                            if data.get('errorNo') == 0:
                                msg = '"snxurlscan" Successful'
                                self.snx_logger.info(msg)
                                self.format_event(record, data, action='add')

                            elif data.get('errorNo') == 1:
                                msg = 'Your URL Scan request is submitted to the cloud and may take up-to 60 ' \
                                      'seconds to complete. Please check back later using "snxurlscanreport" ' \
                                      'action with scan_id = {0} or running the same "snxurlscan" action one more time' \
                                    .format(data.get('urlData').get('scanId'))
                                record['snx_error'] = msg
                                self.snx_logger.error(msg)

                            else:
                                msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                                record['snx_error'] = msg
                                self.snx_logger.error(msg)
                        else:
                            msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(response.reason)
                            record['snx_error'] = msg
                            self.snx_logger.error(msg)

                    # Yield the modified event back to search
                    yield record
            else:
                yield {'ERROR': 'No Parameter value specified. Please url value.'}

        except Exception as e:
            stack = traceback.format_exc()
            # splunk.Intersplunk.generateErrorResults(str(e))
            self.snx_logger.error(str(e) + ". Traceback: " + str(stack))


dispatch(SnxUrlScanCommand, sys.argv, sys.stdin, sys.stdout, __name__)
