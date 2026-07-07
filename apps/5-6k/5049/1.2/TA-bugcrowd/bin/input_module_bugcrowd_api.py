
# encoding = utf-8

import os
import sys
import time
import datetime

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # api_key = definition.parameters.get('api_key', None)
    # starting_from = definition.parameters.get('starting_from', None)
    # track_states = definition.parameters.get('track_states', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_api_key = helper.get_arg('api_key')
    opt_starting_from = helper.get_arg('starting_from')
    opt_track_states = helper.get_arg('track_states')
    # In single instance mode, to get arguments of a particular input, use
    opt_api_key = helper.get_arg('api_key', stanza_name)
    opt_starting_from = helper.get_arg('starting_from', stanza_name)
    opt_track_states = helper.get_arg('track_states', stanza_name)

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    helper.get_input_stanza()
    # get specific input stanza with stanza name
    helper.get_input_stanza(stanza_name)
    # get all stanza names
    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    account = helper.get_user_credential_by_username("username")
    account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")

    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    helper.log("log message")
    # write to the log using specified log level
    helper.log_debug("log message")
    helper.log_info("log message")
    helper.log_warning("log message")
    helper.log_error("log message")
    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    # get the response headers
    r_headers = response.headers
    # get the response body as text
    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # get response cookies
    r_cookies = response.cookies
    # get redirect history
    historical_responses = response.history
    # get response status code
    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
    helper.save_check_point(key, state)
    # delete checkpoint
    helper.delete_check_point(key)
    # get checkpoint
    state = helper.get_check_point(key)

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    """

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''

    from datetime import datetime
    import json

    helper.set_log_level('info')

    url            = 'https://api.bugcrowd.com'
    api_key        = helper.get_arg('api_key')
    starting_from  = helper.get_arg('starting_from')
    track_states   = helper.get_arg('track_states')
    closed_states  = ['resolved', 'duplicate', 'out_of_scope', 'not_reproducible', 'wont_fix', 'not_applicable']
    bounties       = []

    # Retrieve bounties
    # Leave error handling to Splunk Add-on builder functionality
    response = helper.send_http_request('{0}/bounties'.format(url), 'GET', parameters = None, payload = None, \
                                        headers = {'Accept': 'application/vnd.bugcrowd+json', 'Authorization': 'Token {0}'.format(api_key)}, \
                                        cookies = None, verify = True, cert = None, timeout = None, use_proxy = True)

    if response.status_code == 200:
        r_json = response.json()
    else:
        helper.log_error("Bugcrowd API querying failed with HTTP status code {0}.".format(response.status_code))
        helper.log_error("Returning and retrying during next input run.")
        return

    for bounty in r_json['bounties']:
        bounties.append(bounty['uuid'])

    # Retrieve submissions & create Splunk events
    # Leave error handling to Splunk Add-on builder functionality
    for bounty in bounties:
        if track_states in [False, 'false', 'False', 0]:
            checkpoint = 0 if not helper.get_check_point(bounty) else helper.get_check_point(bounty)

            response = helper.send_http_request('{0}/bounties/{1}/submissions?sort=newest&limit=2500&offset={2}&filter={3}'.format(url, bounty, checkpoint, str(starting_from)), \
                                                'GET', parameters = None, payload = None, \
                                                headers = {'Accept': 'application/vnd.bugcrowd+json', 'Authorization': 'Token {0}'.format(api_key)}, \
                                                cookies = None, verify = True, cert = None, timeout = 60.0, use_proxy = True)

            r_json = response.json()

            helper.save_check_point(bounty, checkpoint + r_json['meta']['count'])

            for submission in r_json['submissions']:
                # Check point handling for the case that state tracking configuration will be changed
                checkpoint = 0 if not helper.get_check_point(submission['uuid']) else helper.get_check_point(submission['uuid'])

                if submission['substate'] == checkpoint:
                    continue

                helper.save_check_point(submission['uuid'], submission['substate'])

                # Strip irrelevant information
                submission['submission_source'] = submission.pop('source', None)
                submission.pop('vulnerability_references_markdown', None)
                submission.pop('uuid', None)
                submission.pop('vrt_version', None)
                submission.pop('remediation_advice_markdown', None)
                submission['bounty'].pop('uuid', None)
                submission['bounty'].pop('description_markdown', None)
                submission['bounty'].pop('targets_overview_markdown', None)
                submission['bounty'].pop('tagline', None)

                # Add custom event time field for easier time recognition
                if submission['substate'] == 'nue':
                    submission['_time'] = submission['submitted_at']
                # TODO Work with Bugcrowd to enable retrieval of submissions' change times via API
                # Set current time for "triaged" and "unresolved" submission. This is as good as it gets for now
                else:
                    submission['_time'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z"

                # Write Splunk event
                event = helper.new_event(source = 'bugcrowd.com/{0}'.format(submission['bounty_code']), \
                                         host = 'api.bugcrowd.com', \
                                         index = helper.get_output_index(), \
                                         sourcetype = helper.get_sourcetype(), \
                                         data = json.dumps(submission))
                ew.write_event(event)

        else:
            response = helper.send_http_request('{0}/bounties/{1}/submissions?sort=newest&limit=2500'.format(url, bounty), \
                                                'GET', parameters = None, payload = None, \
                                                headers = {'Accept': 'application/vnd.bugcrowd+json', 'Authorization': 'Token {0}'.format(api_key)}, \
                                                cookies = None, verify = True, cert = None, timeout = 60.0, use_proxy = True)

            r_json = response.json()

            for submission in r_json['submissions']:
                # Check point handling to avoid duplicate events
                checkpoint = 0 if not helper.get_check_point(submission['uuid']) else helper.get_check_point(submission['uuid'])

                if submission['substate'] == checkpoint or checkpoint in closed_states:
                    continue
                if starting_from == 'triaged' and submission['substate'] == 'nue':
                    continue
                if starting_from == 'unresolved' and submission['substate'] in ['nue', 'triaged']:
                    continue
                if starting_from in ['triaged', 'unresolved'] and checkpoint == 0 and submission['substate'] in closed_states:
                    continue

                helper.save_check_point(submission['uuid'], submission['substate'])

                # Strip irrelevant information
                submission['submission_source'] = submission.pop('source', None)
                submission.pop('vulnerability_references_markdown', None)
                submission.pop('uuid', None)
                submission.pop('vrt_version', None)
                submission.pop('remediation_advice_markdown', None)
                submission['bounty'].pop('uuid', None)
                submission['bounty'].pop('description_markdown', None)
                submission['bounty'].pop('targets_overview_markdown', None)
                submission['bounty'].pop('tagline', None)

                # Add custom event time field for easier time recognition
                if submission['substate'] == 'nue':
                    submission['_time'] = submission['submitted_at']
                # TODO Work with Bugcrowd to enable retrieval of submissions' change times via API
                # Set current time for updated submission. This is as good as it gets for now
                else:
                    submission['_time'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z"

                # Write Splunk event
                event = helper.new_event(source = 'bugcrowd.com/{0}'.format(submission['bounty_code']), \
                                         host = 'api.bugcrowd.com', \
                                         index = helper.get_output_index(), \
                                         sourcetype = helper.get_sourcetype(), \
                                         data = json.dumps(submission))
                ew.write_event(event)

    helper.log_info("Successfully retrieved and indexed new/updated Bugcrowd submissions.")
