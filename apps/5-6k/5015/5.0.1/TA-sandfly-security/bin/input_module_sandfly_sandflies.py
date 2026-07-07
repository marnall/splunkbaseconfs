
# encoding = utf-8

import os
import sys
import time
import json
from datetime import datetime
from datetime import timezone
from datetime import timedelta
import collections
import re
from solnlib import server_info

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

g_b_verify_ssl = None   # default to None until set by get_verify_ssl function


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # sandfly_server_url = definition.parameters.get('sandfly_server_url', None)
    # global_account = definition.parameters.get('global_account', None)
    pass


def get_verify_ssl(helper):
    global g_b_verify_ssl

    # if the global flag is already set, just return now
    if g_b_verify_ssl is not None:
        helper.log_debug("get_verify_ssl: global g_b_verify_ssl [{}]".format(g_b_verify_ssl))
        return g_b_verify_ssl

    # Force Verify SSL to True by default
    g_b_verify_ssl = True

    t_server_info = server_info.ServerInfo(helper.context_meta['session_key'])
    # t_server_data = t_server_info.to_dict()
    # helper.log_debug("get_verify_ssl: server_data")
    # helper.log_debug(json.dumps(t_server_data, default=str, indent=4))
    b_is_cloud = t_server_info.is_cloud_instance()
    helper.log_debug("get_verify_ssl: is_cloud_instance [{}]".format(b_is_cloud))

    if b_is_cloud is True:
        helper.log_debug("get_verify_ssl: Splunk Cloud return g_b_verify_ssl [{}]".format(g_b_verify_ssl))
        return g_b_verify_ssl

    b_verify_ssl = helper.get_arg('enable_ssl_verification')
    if b_verify_ssl is not None:
        g_b_verify_ssl = b_verify_ssl
        helper.log_debug("get_verify_ssl: enable_ssl_verification flag [{}]".format(b_verify_ssl))

    helper.log_debug("get_verify_ssl: Splunk Enterprise return g_b_verify_ssl [{}]".format(g_b_verify_ssl))
    return g_b_verify_ssl


def validate_secure_url(helper, url):
    if get_verify_ssl(helper) is False:
        helper.log_error("SANDFLY_WARNING(validate_secure_url): SSL certificate verification is disaled, NOT RECOMMENDED")

    # pattern = "^https:\/\/[0-9A-z.]+.[0-9A-z.]+.[a-z]+$"
    pattern = "^https:\/\/(.*)$"

    result = re.match(pattern, url)
    if result is not None:
        helper.log_debug("VALID SECURE URL: [{}]".format(url))
        return True

    helper.log_error("SANDFLY_ERROR(validate_secure_url): insecure URL [{}]".format(url))
    return False


def get_whitelist_rules( helper, ew, base_url, access_token, white_list ):
    headers = { "Accept": "application/json", "Content-Type": "application/json" }

    if access_token is not None:
        headers['Authorization'] = 'Bearer ' + access_token

    proxy_settings = helper.get_proxy()
    use_proxy = bool( proxy_settings )
    verify_ssl = get_verify_ssl(helper)

    url_to_query = base_url + '/whitelistrules'
    r = helper.send_http_request(
        url=url_to_query,
        method='GET',
        headers=headers,
        use_proxy=use_proxy,
        verify=verify_ssl
        )

    if r.status_code != 200:    # requests.codes.ok
        error_msg = 'SANDFLY_ERROR(get_whitelistrule): {} {}'
        helper.log_error( error_msg.format( r.status_code, r.reason ) )
        return None, sandfly_list

    json_data = r.json()

    total_count = json_data['total']

    helper.log_info( 'Whitelist Rules Total: [{}]'.format( total_count ) )

    hits_list = json_data['data']

    if len(hits_list) == 0:
        return white_list

    for d in hits_list:
        white_list.append( d )

    return white_list


def get_sandflies( helper, ew, base_url, access_token, scroll_id, sandfly_list ):
    headers = { "Accept": "application/json", "Content-Type": "application/json" }

    if access_token is not None:
        headers['Authorization'] = 'Bearer ' + access_token

    proxy_settings = helper.get_proxy()
    use_proxy = bool( proxy_settings )
    verify_ssl = get_verify_ssl(helper)

    if scroll_id is not None:
        url_to_query = base_url + '/scroll'
        payload = { "scroll_id": scroll_id }
        r = helper.send_http_request(
            url=url_to_query,
            method='POST',
            headers=headers,
            payload=json.dumps( payload ),
            use_proxy=use_proxy,
            verify=verify_ssl
            )
    else:
        url_to_query = base_url + '/sandflies'
        r = helper.send_http_request(
            url=url_to_query,
            method='GET',
            headers=headers,
            use_proxy=use_proxy,
            verify=verify_ssl
            )

    if r.status_code != 200:    # requests.codes.ok
        error_msg = 'SANDFLY_ERROR(get_sandflies): {} {}'
        helper.log_error( error_msg.format( r.status_code, r.reason ) )
        return None, sandfly_list

    json_data = r.json()

    if "scroll_id" in json_data:
        scroll_id = json_data['scroll_id']
    else:
        scroll_id = None

    total_count = json_data['total']

    helper.log_info( 'Sandflies Total: [{}]'.format( total_count ) )

    hits_list = json_data['data']

    if len(hits_list) == 0:
        return None, sandfly_list

    for d in hits_list:
        sandfly_list.append( d )

    return scroll_id, sandfly_list


def do_process_whitelist_rules( helper, ew, white_list ):
    count = 0
    t_now = datetime.now(timezone.utc)

    if len(white_list) > 0:
        for d in white_list:
            t = {}
            t['timestamp'] = t_now.strftime( "%Y-%m-%dT%H:%M:%SZ" )
            t['event_type'] = 'sandfly_whitelist_rules'
            t['sandfly_input'] = helper.get_input_stanza_names()
            t['whitelist_rule'] = d
            data = json.dumps( t, default=str, sort_keys=False )
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="sandfly:whitelist", data=data)
            ew.write_event(event)
            count += 1

    helper.log_debug('do_process_white_list: count            [{}]'.format(count))

    return count


def do_process_sandflies( helper, ew, sandfly_list ):
    count = 0
    t_now = datetime.now(timezone.utc)

    if len(sandfly_list) > 0:
        for d in sandfly_list:
            t = {}
            t['timestamp'] = t_now.strftime( "%Y-%m-%dT%H:%M:%SZ" )
            t['event_type'] = 'sandfly_sandflies'
            t['sandfly_input'] = helper.get_input_stanza_names()
            t['sandfly_info'] = d
            data = json.dumps( t, default=str, sort_keys=False )
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
            ew.write_event(event)
            count += 1

    helper.log_debug('do_process_sandflies: count            [{}]'.format(count))

    return count


def validate_license( helper, ew, base_url, access_token ):
    headers = { "Accept": "application/json", "Content-Type": "application/json" }

    if access_token is not None:
        headers['Authorization'] = 'Bearer ' + access_token

    proxy_settings = helper.get_proxy()
    use_proxy = bool( proxy_settings )
    verify_ssl = get_verify_ssl(helper)

    url_to_query = base_url + '/license'
    r = helper.send_http_request(
        url=url_to_query,
        method='GET',
        headers=headers,
        use_proxy=use_proxy,
        verify=verify_ssl
        )

    if r.status_code != 200:    # requests.codes.ok
        error_msg = 'SANDFLY_ERROR(validate_license): {} {}'
        helper.log_error( error_msg.format( r.status_code, r.reason ) )
        return False

    json_data = r.json()
    # helper.log_debug('validate_license: license info [{}]'.format(json.dumps(json_data, indent=4, default=str, sort_keys=False)))

    t_customer = json_data['customer']
    helper.log_info('validate_license: customer name [{}]'.format( t_customer['name'] ))

    t_date = json_data['date']
    t_expiry = datetime.strptime( t_date['expiry'], "%Y-%m-%dT%H:%M:%SZ" ).replace(tzinfo=timezone.utc)
    helper.log_debug('validate_license: expiry date [{}]'.format( t_expiry ))
    t_now = datetime.now(timezone.utc)
    helper.log_debug('validate_license: todays date [{}]'.format( t_now ))

    if t_expiry < t_now:
        helper.log_error('SANDFLY_ERROR(validate_license): expiry date [{}] EXPIRED'.format( t_date['expiry'] ))
        return False

    helper.log_info('validate_license: expiry date [{}] VALID'.format( t_date['expiry'] ))

    t_limits = json_data['limits']
    features_list = t_limits['features']

    if len(features_list) == 0:
        helper.log_error( 'SANDFLY_ERROR(validate_license): unable to find features in license' )
        return False

    for f in features_list:
        if f == 'splunk_connector':
            helper.log_info('validate_license: feature [{}] VALID'.format( f ))
            return True

    helper.log_info('validate_license: feature [splunk_connector] NOT FOUND')
    helper.log_debug('validate_license: features_list [{}]'.format(json.dumps(features_list, indent=4, default=str, sort_keys=False)))

    return False


def sandfly_login( helper, base_url, username, password ):
    url_to_query = base_url + '/auth/login'
    headers = { "Accept": "application/json", "Content-Type": "application/json" }
    payload = { "username": username, "password": password }

    helper.log_debug('sandfly_login URL [{}]'.format(url_to_query))
    helper.log_debug('sandfly_login Headers [{}]'.format(headers))
    helper.log_debug('sandfly_login Username [{}]'.format(username))

    proxy_settings = helper.get_proxy()
    use_proxy = bool( proxy_settings )
    verify_ssl = get_verify_ssl(helper)

    r = helper.send_http_request(
        url=url_to_query,
        method='POST',
        headers=headers,
        payload=json.dumps( payload ),
        use_proxy=use_proxy,
        verify=verify_ssl
        )

    if r.status_code != 200:    # requests.codes.ok
        error_msg = 'SANDFLY_ERROR(sandfly_login): {} {}'
        helper.log_error( error_msg.format( r.status_code, r.reason ) )
        return None, None

    json_data = r.json()
    access_token = json_data['access_token']
    refresh_token = json_data['refresh_token']

    return access_token, refresh_token


def sandfly_refresh( helper, base_url, refresh_token ):
    url_to_query = base_url + '/auth/login_refresh'
    headers = { "Accept": "application/json", "Content-Type": "application/json" }
    headers['Authorization'] = 'Bearer ' + refresh_token
    payload = { "refresh_token": refresh_token }

    proxy_settings = helper.get_proxy()
    use_proxy = bool( proxy_settings )
    verify_ssl = get_verify_ssl(helper)

    r = helper.send_http_request(
        url=url_to_query,
        method='POST',
        headers=headers,
        payload=json.dumps( payload ),
        use_proxy=use_proxy,
        verify=verify_ssl
        )

    if r.status_code != 200:    # requests.codes.ok
        error_msg = 'SANDFLY_ERROR(sandfly_refresh): {} {}'
        helper.log_error( error_msg.format( r.status_code, r.reason ) )
        return None

    json_data = r.json()
    access_token = json_data['access_token']

    return access_token


def collect_events(helper, ew):
    global_account = helper.get_arg( 'global_account' )
    base_url = helper.get_arg( 'sandfly_server_url' )

    my_app_name = helper.get_app_name()
    my_stanza_name = helper.get_input_stanza_names()
    my_input_type = helper.get_input_type()
    helper.log_debug('collect_events [{}] STARTMEUP - [{}] - [{}]'.format(my_input_type, my_app_name, my_stanza_name))

    if validate_secure_url(helper, base_url) is False:
        helper.log_error("collect_events insecure url")
        return

    try:
        access_token, refresh_token = sandfly_login( helper, base_url, global_account['username'], global_account['password'] )
        if access_token is None:
            helper.log_error("collect_events failed login")
            return
    except Exception as e:
        helper.log_error( 'SANDFLY_ERROR(collect_events): {}'.format( str( e ) ) )
        return

    b_valid_license = validate_license( helper, ew, base_url, access_token )
    if b_valid_license is False:
        helper.log_error("collect_events invalid license")
        return

    stanza_checkpoint_timestamp = 'sandfly_sandflies_{}_timestamp'.format(my_stanza_name)

    # sandflies
    #

    scroll_id = None

    sandfly_list = []

    scroll_id, sandfly_list = get_sandflies( helper, ew, base_url, access_token, scroll_id, sandfly_list )

    while scroll_id is not None:
        scroll_id, sandfly_list = get_sandflies( helper, ew, base_url, access_token, scroll_id, sandfly_list )

    if sandfly_list is not None:
        do_process_sandflies( helper, ew, sandfly_list )

    helper.log_debug('get_sandflies success')

    # whitelist rules
    #

    white_list = []

    white_list = get_whitelist_rules( helper, ew, base_url, access_token, white_list )

    if white_list is not None:
        do_process_whitelist_rules( helper, ew, white_list )

    helper.log_debug('get_whitelist_rules success')

    t_now = datetime.now(timezone.utc)
    t_now_timestamp = t_now.strftime( "%Y-%m-%dT%H:%M:%SZ" )
    helper.save_check_point( stanza_checkpoint_timestamp, t_now_timestamp )

    helper.log_debug('collect_events [{}] success THE_END [{}] ===================='.format(my_input_type, my_stanza_name))

    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_sandfly_server_url = helper.get_arg('sandfly_server_url')
    opt_global_account = helper.get_arg('global_account')
    # In single instance mode, to get arguments of a particular input, use
    opt_sandfly_server_url = helper.get_arg('sandfly_server_url', stanza_name)
    opt_global_account = helper.get_arg('global_account', stanza_name)

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
