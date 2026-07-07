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
class SnxAPIQuotaCommand(GeneratingCommand):

    # Internal variables
    api_key = None
    base_url = None
    snx_logger = None

    def format_event(self, event, raw_json, action='new'):
        if action == 'new':
            event['_time'] = time.time()
            event['_raw'] = json.dumps(raw_json)

        event['licensed_quota'] = raw_json.get('quotaDetails').get('licensedQuota')
        event['remaining_quota'] = raw_json.get('quotaDetails').get('remainingQuota')
        event['expiryDate'] = raw_json.get('quotaDetails').get('expiryDate')
        if raw_json.get('quotaDetails').get('isExpired') == 1:
            event['isExpired'] = 'Yes'
        else:
            event['isExpired'] = 'No'
        event['note'] = raw_json.get('quotaDetails').get('note')

        return event

    def generate(self):
        try:
            # Accquire the logger
            self.snx_logger = snx_utils.setup_logging()
            self.snx_logger.info('Running "snxapiquota" Command')

            # Get API information
            api_config = snx_utils.get_config("slashnext.conf", "api-setup")
            self.base_url = api_config['base_url']
            self.api_key = api_config['api_key']

            # Make a call to SlashNext - OTI Endpoint
            api_quota_api = self.base_url + '/oti/v1/quota/status'
            ep_params = {
                'authkey': self.api_key,
            }

            response = requests.post(api_quota_api, ep_params)
            if response.ok:
                data = response.json()
                if data.get('errorNo') == 0:
                    event = {}
                    yield self.format_event(event, data, action='new')

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


dispatch(SnxAPIQuotaCommand, sys.argv, sys.stdin, sys.stdout, __name__)
