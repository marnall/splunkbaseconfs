
# encoding = utf-8

import time
import traceback
import requests
import json

import proofpoint_digital_risk_constants as constants


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    pass


def collect_events(helper, ew):
    """Splunk default collect event method for core logic of data collection and ingestion."""
    try:
        start_time = time.time()
        input_name = helper.get_input_stanza_names()
        helper.log_info("Starting data collection for input {}".format(input_name))
        global_account = helper.get_arg('global_account')
        if not global_account:
            raise Exception(
                "Invalid global_account for input '{}'.".format(input_name))

        access_token = global_account.get("access_token").strip()
        url = constants.PROOFPOINT_DIGITALRISK_URL
        headers = {"Authorization": "Bearer {}".format(access_token)}

        # Fetching proxy data
        proxy_uri = helper._get_proxy_uri()
        if proxy_uri is not None:
            helper.log_info("Proxy is enabled. Using proxy server.")

        proxy_settings = {"http": proxy_uri, "https": proxy_uri}
        response = requests.get(url=url,
                                headers=headers,
                                verify=constants.SSL_VERIFY,
                                proxies=proxy_settings)
        response.raise_for_status()
        data = json.loads(response.text)
        events = 0
        if data:
            for record in data.get('event'):
                event = helper.new_event(index=helper.get_output_index(),
                                         sourcetype=helper.get_sourcetype(),
                                         source=helper.get_input_type(),
                                         data=json.dumps(record))
                ew.write_event(event)
                events += 1
            helper.log_info("Data collected successfully for input {}".format(input_name))
        else:
            helper.log_debug('Skipping ingestion as there are no records in the response object for '
                             'input {}'.format(input_name))
        elapsed_time_event_collection = (time.time() - start_time)
    except requests.exceptions.HTTPError:
        helper.log_error('Invalid Access Token. Please enter the valid credentials.')
    except requests.exceptions.ConnectionError:
        helper.log_error('Unable to request to Proofpoint Digital Risk Instance. '
                         'Please validate the provided credentials and Proxy configurations '
                         'or check the network connectivity.')
    except Exception:
        helper.log_error('Data Collection failed for input {} : {}'.format(input_name, traceback.format_exc()))
    finally:
        helper.log_info("Total events collected are {}".format(events))
        helper.log_info("Time elapsed in data collection is {}".format(elapsed_time_event_collection))
