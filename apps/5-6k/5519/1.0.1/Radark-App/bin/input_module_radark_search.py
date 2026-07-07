# encoding = utf-8

import sys
from datetime import datetime
import time
import calendar
from base64 import b64encode
from intelact_app_utility import set_input, get_request_parameters, scroll_incidents, retrieve_verbose_incidents, \
    retrieve_risk_pipeline, retrieve_intel_ioc

input_stanza = None
input_name = None


def validate_input(helper, definition):
    """ This method validates the input fields
        :param helper:
        :param definition:
        :return: None
    """
    since = definition.parameters.get('since', None)
    if not since:
        return
    try:
        datetime.strptime(since, '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        raise Exception('Since field has improper date format. Please enter date in mentioned format')
    except Exception as e:
        raise e
    try:
        pattern = '%Y-%m-%dT%H:%M:%S.%f'
        epoch = int(calendar.timegm(time.strptime(since, pattern)))
        current = int(calendar.timegm(time.gmtime()))
        if epoch - current > 0 or epoch < 0:
            raise Exception('Future date or the date before epoch is not allowed')
    except Exception as e:
        raise e


def collect_events(helper, ew):
    """ This is the main method which is called when input is run
        :param helper:
        :param ew:
        :return:
    """
    
    try:
        # Check the proxy settings
        proxy_settings = helper.get_proxy()
        proxy = True if proxy_settings else False
        # Get the name of the input Stanza and input stanza itself
        global input_name, input_stanza
        input_name = helper.get_input_stanza_names()
        input_stanza = helper.get_input_stanza()
        set_input(input_stanza, input_name)
        # Get the authorization header for the basic auth
        auth = str(input_stanza[input_name]['global_account']['access_key']) + ':' \
               + str(input_stanza[input_name]['global_account']['secret_key'])
        authorization = b64encode(auth.encode()).decode()
        retrieve_private_incidents(helper, authorization, proxy, ew)
        if input_stanza[input_name]['verbose'] == '1':
            retrieve_verbose_incidents(helper, authorization, proxy, ew)
        retrieve_risk_pipeline(helper, authorization, proxy, ew)
        if input_stanza[input_name]['global_incident'] == '1':
            retrieve_intel_incidents(helper, authorization, proxy, ew)
            retrieve_intel_ioc(helper, authorization, proxy, ew)
    except Exception as e:
        helper.log_error('Unexpected error:' + str(e))


def retrieve_private_incidents(helper, authorization, proxy, ew):
    """ This method retrieves private incidents and writes them to splunk and simultaneously
        updates the checkpoint
        :param helper:
        :param authorization: auth which can be used in request headers
        :param proxy Decides if proxy is enabled or not
        :param ew:
        :return:
    """
    try:
        final_time = str(datetime.utcnow().isoformat()) + 'Z'
        info = get_request_parameters('incidents', authorization, helper, final_time)

        # This method will retrieve private incidents in batch and writes them to splunk
        scroll_incidents(helper, proxy, ew, info, 'incidents')
        checkpoint = helper.get_check_point(input_name) or dict()
        checkpoint["private_incident"] = final_time
        helper.save_check_point(input_name, checkpoint)
    except Exception as e:
        helper.log_error('Exception while retrieving private incidents:' + str(e))
        raise


def retrieve_intel_incidents(helper, authorization, proxy, ew):
    """ This method retrieves private incidents and writes them to splunk and simultaneously
        updates the checkpoint
        :param helper:
        :param authorization: auth which can be used in request headers
        :param proxy Decides if proxy is enabled or not
        :param ew:
        :return:
    """
    try:
        final_time = str(datetime.utcnow().isoformat()) + 'Z'
        info = get_request_parameters('intel_incidents', authorization, helper, final_time)

        # This method will retrieve private incidents in batch and writes them to splunk
        scroll_incidents(helper, proxy, ew, info, 'intel_incidents')

        checkpoint = helper.get_check_point(input_name) or dict()
        checkpoint["intel_incident"] = final_time
        helper.save_check_point(input_name, checkpoint)
    except Exception as e:
        helper.log_error('Exception while retrieving intelligence incidents:' + str(e))
        raise
