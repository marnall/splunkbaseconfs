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
class SnxHostReputationCommand(StreamingCommand):
    # Class variable
    # host variable incase user provides a single ip/domain to lookup
    host = Option(require=False)

    # field variable incase user points to a field in events to lookup
    host_field = Option(require=False, validate=validators.Fieldname())

    # Internal variables
    api_key = None
    base_url = None
    snx_logger = None

    def format_event(self, event, raw_json, action='new'):
        # Format event according to Host Reputation API
        if action == 'new':
            # If we are creating new events then we must
            # add these fields (Splunk Requirement)
            event['_time'] = time.time()
            event['_raw'] = json.dumps(raw_json)
        event['verdict'] = raw_json.get('threatData').get('verdict')
        event['threat_status'] = raw_json.get('threatData').get('threatStatus')
        event['threat_type'] = raw_json.get('threatData').get('threatType')
        event['threat_name'] = raw_json.get('threatData').get('threatName')
        event['first_seen'] = raw_json.get('threatData').get('firstSeen')
        event['last_seen'] = raw_json.get('threatData').get('lastSeen')

        return event

    def stream(self, records):
        # Initial Settings for logging and credentials
        # (FYI: I tried overriding the prepare method which apparently gets called
        # by splunkd before running the command but for some reason it was being called
        # 3 times, which I thought was a waste so just getting the settings here now)
        try:
            # Accquire the logger
            self.snx_logger = snx_utils.setup_logging()
            self.snx_logger.info('Running "snxhostreputation" Command')

            # Get API information
            api_config = snx_utils.get_config("slashnext.conf", "api-setup")
            self.base_url = api_config['base_url']
            self.api_key = api_config['api_key']

            if self.host is not None:
                # User only passed one host value so we generate one event only for that host only
                self.snx_logger.info("Checking Host Reputation for Host: {0}".format(self.host))

                # Make a call to SlashNext - OTI Endpoint
                host_repute_api = self.base_url + '/oti/v1/host/reputation'
                ep_params = {
                    'authkey': self.api_key,
                    'host': self.host
                }

                response = requests.post(host_repute_api, ep_params)
                if response.ok:
                    data = response.json()
                    if data.get('errorNo') == 0:
                        msg = '"snxhostreputation" Successful'
                        self.snx_logger.info(msg)
                        new_event = {}
                        # Yield the new event
                        yield self.format_event(new_event, data, action='new')
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

            elif self.host_field is not None:
                # User passed a field in host_field value so we iterate over all the events passed
                # from previous command in the pipeline
                for record in records:
                    try:
                        # Get the host value from the field in the events
                        host = record.get(str(self.host_field))
                        if host is None:
                            # For the scenario where user has no domain in the field
                            msg = 'No Host Value found in the specified field'
                            record['snx-error'] = msg
                            self.snx_logger.error(msg)
                        else:
                            # Check the Host Reputation for each host in the events
                            self.snx_logger.info("Checking Host Reputation for Host: {0}".format(host))

                            # Make a call to SlashNext - OTI Endpoint
                            host_report_api = self.base_url + '/oti/v1/host/reputation'
                            ep_params = {
                                'authkey': self.api_key,
                                'host': host
                            }

                            response = requests.post(host_report_api, ep_params)
                            if response.ok:
                                data = response.json()
                                if data.get('errorNo') == 0:
                                    msg = '"snxhostreputation" Successful'
                                    self.snx_logger.info(msg)
                                    # Format the event but do not yield anything as we don't want
                                    # to create a new event rather, just append the threat information
                                    self.format_event(record, data, action='add')
                                else:
                                    msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                                    record['snx_error'] = msg
                                    self.snx_logger.error(msg)
                            else:
                                msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(response.reason)
                                self.snx_logger.error(msg)
                                record['snx_error'] = msg

                        # Yield the modified event back to search
                        yield record

                    except Exception as e:
                        stack = traceback.format_exc()
                        # splunk.Intersplunk.generateErrorResults(str(e))
                        self.snx_logger.error(str(e) + ". Traceback: " + str(stack))

            else:
                yield {'ERROR': 'No Parameter value specified. Please specify host or host_field parameter value.'}

        except Exception as e:
            stack = traceback.format_exc()
            # splunk.Intersplunk.generateErrorResults(str(e))
            self.snx_logger.error(str(e) + ". Traceback: " + str(stack))


dispatch(SnxHostReputationCommand, sys.argv, sys.stdin, sys.stdout, __name__)
