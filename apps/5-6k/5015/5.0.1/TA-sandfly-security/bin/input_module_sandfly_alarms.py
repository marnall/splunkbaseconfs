
# encoding = utf-8

import os
import sys
import time
import json
from datetime import datetime
from datetime import timezone
from datetime import timedelta
import collections
import csv
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
    # sandfly_results = definition.parameters.get('sandfly_results', None)
    # start_time = definition.parameters.get('start_time', None)
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


def create_lookup( helper, ew, sandfly_list ):
    my_path = os.path.abspath( os.path.dirname( __file__ ) )
    #data = my_path
    #event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    #ew.write_event(event)

    lookup_path = os.path.abspath( os.path.join( my_path, "..", "lookups") )
    #data = lookup_path
    #event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    #ew.write_event(event)

    if not os.path.exists( lookup_path ):
        try:
            os.mkdir( lookup_path )
            helper.log_debug( 'Created Lookup Path: {}'.format( lookup_path ) )
        except Exception as e:
            helper.log_error( 'SANDFLY_ERROR(create_lookup): {}'.format( str( e ) ) )
            return

    lookup_file = lookup_path + '/sandflies.csv'

    #data = json.dumps( sandfly_list, indent=4, default=str, sort_keys=False )
    #event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    #ew.write_event(event)

    csv_file = open( lookup_file, 'wt' )
    csv_writer = csv.DictWriter( csv_file, fieldnames=sandfly_list[0].keys() )
    csv_writer.writeheader()

    for row in sandfly_list:
        csv_writer.writerow( row )

    csv_file.close()

    helper.log_debug( 'Created Lookup File: count [{}] {}'.format( len(sandfly_list), lookup_file ) )

    return


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

    for h in hits_list:
        ## the_id = h['id'] # deprecated in 4.6.0
        the_name = h['name']
        the_type = h['type']
        ##the_cpu = h['_source']['max_cpu_load']
        ##the_disk = h['_source']['max_disk_load']
        the_desc = h['description']
        the_active = h['active']
#        helper.log_debug('get_sandfles name [{}] desc [{}]'.format(the_name, the_desc))
        d = collections.OrderedDict()
        ## d['sandfly_id'] = the_id
        d['sandfly_name'] = the_name
        d['sandfly_title'] = the_name.replace( '_', ' ').upper()
        d['sandfly_type'] = the_type
        d['sandfly_active'] = the_active
        d['sandfly_description'] = the_desc
        sandfly_list.append( d )

    return scroll_id, sandfly_list


def do_process_alarms( helper, ew, json_data, last_seen_time, b_summary, tag ):
    count = 0
    last_sequence_id = None
    b_more_results = False
    total = 0

    hits_list = json_data['data']

    if len(hits_list) > 0:
        b_more_results = json_data['more_results']
        total = json_data['total']

        for h in hits_list:
            last_sequence_id = h['sequence_id']
            my_timestamp = h['last_seen']
            if last_seen_time is None:
                last_seen_time = my_timestamp
            else:
                dt1 = datetime.strptime(last_seen_time, "%Y-%m-%dT%H:%M:%SZ" )
                dt2 = datetime.strptime(my_timestamp, "%Y-%m-%dT%H:%M:%SZ" )
                if dt2 > dt1:
                    last_seen_time = my_timestamp
            if not 'timestamp' in h:
                h['timestamp'] = my_timestamp
            if not 'sandfly_input' in h:
                h['sandfly_input'] = helper.get_input_stanza_names()
            if not 'sandfly_tag' in h:
                h['sandfly_tag'] = tag
            if not 'sandfly_summary' in h:
                h['sandfly_summary'] = b_summary
            data = json.dumps( h, default=str, sort_keys=False )
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
            ew.write_event(event)
            count += 1

    helper.log_debug('do_process_alarms: sandfly_tag      [{}]'.format(tag))
    helper.log_debug('do_process_alarms: summary_flag     [{}]'.format(b_summary))
    helper.log_debug('do_process_alarms: more_results     [{}]'.format(b_more_results))
    helper.log_debug('do_process_alarms: last_sequence_id [{}]'.format(last_sequence_id))
    helper.log_debug('do_process_alarms: last_seen_time   [{}]'.format(last_seen_time))
    helper.log_debug('do_process_alarms: total            [{}]'.format(total))
    helper.log_debug('do_process_alarms: count            [{}]'.format(count))

    return count, b_more_results, last_sequence_id, last_seen_time


def get_sandfly_alarms_by_last_seen( helper, ew, alarm_type, b_summary, base_url, access_token, max_sequence_id, min_sequence_id, last_seen_time ):
    headers = { "Accept": "application/json", "Content-Type": "application/json" }

    if access_token is not None:
        headers['Authorization'] = 'Bearer ' + access_token

    url_to_query = base_url + '/results'
    payload = {
        "size": 999,
        "summary": b_summary,
        "filter": {
            "items": [
                { "columnField": "data.status", "operatorValue": "equals", "value": alarm_type},
                { "columnField": "last_seen", "operatorValue": "after", "value": last_seen_time},
                { "columnField": "sequence_id", "operatorValue": ">", "value": min_sequence_id},
                { "columnField": "sequence_id", "operatorValue": "<=", "value": max_sequence_id}
            ],
            "linkoperator": "and"
        },
        "sort": [
                { "Field": "sequence_id", "sort": "asc"}
        ]
    }
    method = 'POST'

    proxy_settings = helper.get_proxy()
    use_proxy = bool( proxy_settings )
    verify_ssl = get_verify_ssl(helper)

    try:
        r = helper.send_http_request(
            url=url_to_query,
            method=method,
            headers=headers,
            payload=json.dumps( payload ),
            use_proxy=use_proxy,
            timeout=30.0,
            verify=verify_ssl
            )
    except Exception as e:
        helper.log_error( 'SANDFLY_ERROR(get_sandfly_alarms_by_last_seen): {}'.format( str( e ) ) )
        return 0, None, None, None

    if r.status_code != 200:    # requests.codes.ok
        error_msg = 'SANDFLY_ERROR(get_sandfly_alarms_by_last_seen): alarm_type {} code {} reason {}'
        helper.log_error( error_msg.format( alarm_type, r.status_code, r.reason ) )
        return 0, None, None, None

    json_data = r.json()

    count, b_more_results, last_sequence_id, last_seen_time = do_process_alarms( helper, ew, json_data, last_seen_time, b_summary, "last_seen" )

    helper.log_debug('get_sandfly_alarms_by_last_seen: [{}] RETURN count [{}] more_results [{}] last_sequence_id [{}] last_seen_time [{}]'.format(alarm_type, count, b_more_results, last_sequence_id, last_seen_time))

    return count, b_more_results, last_sequence_id, last_seen_time


def get_sandfly_alarms_by_sequence_id( helper, ew, alarm_type, b_summary, base_url, access_token, last_sequence_id, last_seen_time ):
    headers = { "Accept": "application/json", "Content-Type": "application/json" }

    if access_token is not None:
        headers['Authorization'] = 'Bearer ' + access_token

    url_to_query = base_url + '/results'
    payload = {
        "size": 999,
        "summary": b_summary,
        "filter": {
            "items": [
                { "columnField": "data.status", "operatorValue": "equals", "value": alarm_type},
                { "columnField": "sequence_id", "operatorValue": ">", "value": last_sequence_id}
            ],
            "linkoperator": "and"
        },
        "sort": [
                { "Field": "sequence_id", "sort": "asc"}
        ]
    }
    method = 'POST'

    proxy_settings = helper.get_proxy()
    use_proxy = bool( proxy_settings )
    verify_ssl = get_verify_ssl(helper)

    try:
        r = helper.send_http_request(
            url=url_to_query,
            method=method,
            headers=headers,
            payload=json.dumps( payload ),
            use_proxy=use_proxy,
            timeout=30.0,
            verify=verify_ssl
            )
    except Exception as e:
        helper.log_error( 'SANDFLY_ERROR(get_sandfly_alarms_by_sequence_id): {}'.format( str( e ) ) )
        return 0, None, None, None

    if r.status_code != 200:    # requests.codes.ok
        error_msg = 'SANDFLY_ERROR(get_sandfly_alarms_by_sequence_id): alarm_type {} code {} reason {}'
        helper.log_error( error_msg.format( alarm_type, r.status_code, r.reason ) )
        return 0, None, None, None

    json_data = r.json()

    count, b_more_results, last_sequence_id, last_seen_time = do_process_alarms( helper, ew, json_data, last_seen_time, b_summary, "first_seen" )

    helper.log_debug('get_sandfly_alarms_by_sequence_id: [{}] RETURN count [{}] more_results [{}] last_sequence_id [{}] last_seen_time [{}]'.format(alarm_type, count, b_more_results, last_sequence_id, last_seen_time))

    return count, b_more_results, last_sequence_id, last_seen_time


def get_sandfly_alarms_by_timestamp( helper, ew, alarm_type, b_summary, base_url, access_token, last_timestamp, last_seen_time ):
    headers = { "Accept": "application/json", "Content-Type": "application/json" }

    if access_token is not None:
        headers['Authorization'] = 'Bearer ' + access_token

    url_to_query = base_url + '/results'
    payload = {
        "size": 999,
        "summary": b_summary,
        "time_since": last_timestamp,
        "filter": {
            "items": [
                { "columnField": "data.status", "operatorValue": "equals", "value": alarm_type}
            ] 
        },
        "sort": [
                { "Field": "sequence_id", "sort": "asc"}
        ]
    }
    method = 'POST'

    proxy_settings = helper.get_proxy()
    use_proxy = bool( proxy_settings )
    verify_ssl = get_verify_ssl(helper)

    try:
        r = helper.send_http_request(
            url=url_to_query,
            method=method,
            headers=headers,
            payload=json.dumps( payload ),
            use_proxy=use_proxy,
            timeout=30.0,
            verify=verify_ssl
            )
    except Exception as e:
        helper.log_error( 'SANDFLY_ERROR(get_sandfly_alarms_by_timestamp): {}'.format( str( e ) ) )
        return 0, None, None, None

    if r.status_code != 200:    # requests.codes.ok
        error_msg = 'SANDFLY_ERROR(get_sandfly_alarms_by_timestamp): alarm_type {} code {} reason {}'
        helper.log_error( error_msg.format( alarm_type, r.status_code, r.reason ) )
        return 0, None, None, None

    json_data = r.json()

    count, b_more_results, last_sequence_id, last_seen_time = do_process_alarms( helper, ew, json_data, last_seen_time, b_summary, "first_seen" )

    helper.log_debug('get_sandfly_alarms_by_timestamp: [{}] RETURN count [{}] more_results [{}] last_sequence_id [{}] last_seen_time [{}]'.format(alarm_type, count, b_more_results, last_sequence_id, last_seen_time))

    return count, b_more_results, last_sequence_id, last_seen_time


def validate_checkpoint_timestamp( helper, ew, checkpoint_ts_key, start_time_str ):
    if len(start_time_str) == 0:
        helper.log_debug('validate_checkpoint_timestamp : start_time_str [{}], so just return False'.format(start_time_str))
        return False

    helper.log_debug('validate_checkpoint_timestamp [{}] - start_time_str [{}]'.format(checkpoint_ts_key, start_time_str))
    checkpoint_ts = helper.get_check_point( checkpoint_ts_key )
    if checkpoint_ts is None:
        helper.log_debug('validate_checkpoint_timestamp : [{}] does not exist, so just return False'.format(checkpoint_ts_key))
        return False

    t_last = datetime.strptime( checkpoint_ts, "%Y-%m-%dT%H:%M:%SZ" )
    t_test = datetime.strptime( start_time_str, "%Y-%m-%dT%H:%M:%SZ" )

    helper.log_debug('validate_checkpoint_timestamp : last [{}]'.format(checkpoint_ts))
    helper.log_debug('validate_checkpoint_timestamp : test [{}]'.format(start_time_str))

    if t_last < t_test:
        helper.log_error('SANDFLY_ERROR(validate_checkpoint_timestamp): last date [{}] older than test date [{}], return True'.format( checkpoint_ts, start_time_str ))
        return True

    helper.log_debug('validate_checkpoint_timestamp : last date [{}] is not older than test date [{}], return False'.format(checkpoint_ts, start_time_str))
    return False


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


def get_checkpoint_info( helper, my_stanza_name, alarm_type, start_time_str, reset_checkpoint_keys ):
    checkpoint_timestamp = 'sandfly_alarms_timestamp_' + alarm_type
    last_timestamp = None

    checkpoint_old = 'sandfly_alarms_sequenceid_' + alarm_type
    checkpoint_key = 'sandfly_alarms_sequenceid_' + my_stanza_name + '_' + alarm_type
    last_seen_key = 'sandfly_alarms_lastseen_' + my_stanza_name + '_' + alarm_type

    last_sequence_id = helper.get_check_point( checkpoint_old )
    if last_sequence_id is not None:
        helper.log_debug('OLD LAST SEQUENCE_ID : {}'.format(last_sequence_id))
        helper.delete_check_point( checkpoint_old )
        helper.save_check_point( checkpoint_key, last_sequence_id )

    if reset_checkpoint_keys is True:
        helper.delete_check_point( checkpoint_key )
        helper.delete_check_point( last_seen_key )

    last_sequence_id = helper.get_check_point( checkpoint_key )
    helper.log_debug('GET LAST SEQUENCE_ID : {}'.format(last_sequence_id))

    if last_sequence_id is None:
        last_timestamp = helper.get_check_point( checkpoint_timestamp )
        helper.log_debug('GET LAST TIMESTAMP   : {}'.format(last_timestamp))
        if last_timestamp is not None:
            helper.delete_check_point( checkpoint_timestamp )

        if last_timestamp is None:
            if len(start_time_str) == 0:
                t_now = datetime.now(timezone.utc) - timedelta(hours=24)
                last_timestamp = t_now.strftime( "%Y-%m-%dT%H:%M:%SZ" )
            else:
                last_timestamp = start_time_str

        helper.log_debug('NEW LAST_TIMESTAMP: {}'.format(last_timestamp))
        helper.log_debug('NEW LAST_SEQUENCE : {}'.format(last_sequence_id))
    else:
        helper.delete_check_point( checkpoint_timestamp )

    last_seen_time = helper.get_check_point( last_seen_key )
    helper.log_debug('GET LAST SEEN TIME   : [{}]'.format(last_seen_time))

    helper.log_info('get_checkpoint_info checkpoint_timestamp  : [{}] [{}]'.format(checkpoint_timestamp, last_timestamp))
    helper.log_info('get_checkpoint_info checkpoint_sequenceid : [{}] [{}]'.format(checkpoint_key, last_sequence_id))
    helper.log_info('get_checkpoint_info checkpoint_lastseen   : [{}] [{}]'.format(last_seen_key, last_seen_time))

    return checkpoint_key, last_sequence_id, last_seen_key, last_seen_time, last_timestamp


def collect_events(helper, ew):
    global_account = helper.get_arg( 'global_account' )
    base_url = helper.get_arg( 'sandfly_server_url' )

    start_time_str = helper.get_arg( 'start_time' )
    if start_time_str is None:
        start_time_str = ""

    b_test_mode = helper.get_arg( 'test_mode' )
    if b_test_mode is None:
        b_test_mode = False

    b_results_summary = helper.get_arg( 'sandfly_results_summary_data' )
    if b_results_summary is None:
        b_results_summary = False

    b_duplicate_alerts = helper.get_arg( 'duplicate_alerts' )
    if b_duplicate_alerts is None:
        b_duplicate_alerts = False

    b_duplicate_summary = helper.get_arg( 'duplicate_alerts_summary_data' )
    if b_duplicate_summary is None:
        b_duplicate_summary = False

    try:
        if len(start_time_str) > 0:
            t_time_obj = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception as e:
        start_time_str = ""
        helper.log_error( 'SANDFLY_ERROR(collect_events): {}'.format( str( e ) ) )

    if b_test_mode is True:
        if len(start_time_str) == 0:
            t_now = datetime.now(timezone.utc) - timedelta(days=7)
            start_time_str = t_now.strftime( "%Y-%m-%dT%H:%M:%SZ" )

    my_app_name = helper.get_app_name()
    my_stanza_name = helper.get_input_stanza_names()
    my_input_type = helper.get_input_type()
    helper.log_debug('collect_events [{}] STARTMEUP - [{}] - [{}]'.format(my_input_type, my_app_name, my_stanza_name))

    if validate_secure_url(helper, base_url) is False:
        helper.log_error("collect_events insecure url")
        return

    helper.log_debug('collect_events START TIME - [{}] - [{}]'.format(len(start_time_str), start_time_str))
    helper.log_debug('collect_events RESULTS SUMMARY - [{}]'.format(b_results_summary))
    helper.log_debug('collect_events DUPLICATE ALERTS - [{}] - summary [{}]'.format(b_duplicate_alerts, b_duplicate_summary))
    helper.log_debug('collect_events TEST MODE - [{}]'.format(b_test_mode))

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

    scroll_id = None

    sandfly_list = []

    scroll_id, sandfly_list = get_sandflies( helper, ew, base_url, access_token, scroll_id, sandfly_list )

    while scroll_id is not None:
        scroll_id, sandfly_list = get_sandflies( helper, ew, base_url, access_token, scroll_id, sandfly_list )

    if sandfly_list is not None:
        create_lookup( helper, ew, sandfly_list )

    helper.log_debug('get_sandflies success')

    stanza_checkpoint_timestamp = 'sandfly_alarms_{}_timestamp'.format(my_stanza_name)
    reset_checkpoint_keys = validate_checkpoint_timestamp( helper, ew, stanza_checkpoint_timestamp, start_time_str )

    sandfly_results = helper.get_arg('sandfly_results')
    helper.log_debug('collect_events sandfly_results [{}]'.format(json.dumps(sandfly_results)))

    helper.log_debug('collect_events start_time_str [{}]'.format(start_time_str))
    helper.log_debug('collect_events reset_checkpt  [{}]'.format(reset_checkpoint_keys))

    if b_test_mode is True:
        reset_checkpoint_keys = True
        helper.log_debug('collect_events reset_checkpt  [{}]'.format(reset_checkpoint_keys))

    for alarm_type in sandfly_results:
        helper.log_debug('collect_events alarm_type: [{}]'.format(alarm_type))
        event_count = 0
        refresh_max = 20
        refresh_count = 0

        checkpoint_key, last_sequence_id, last_seen_key, last_seen_time, last_timestamp = get_checkpoint_info( helper, my_stanza_name, alarm_type, start_time_str, reset_checkpoint_keys )

        helper.log_info('collect_events checkpoint_timestamp  : [{}]'.format(last_timestamp))
        helper.log_info('collect_events checkpoint_key        : [{}]'.format(checkpoint_key))
        helper.log_info('collect_events checkpoint_sequenceid : [{}]'.format(last_sequence_id))
        helper.log_info('collect_events last_seen_key         : [{}]'.format(last_seen_key))
        helper.log_info('collect_events last_seen_time        : [{}]'.format(last_seen_time))

        try:
            access_token = sandfly_refresh( helper, base_url, refresh_token )
            if access_token is None:
                helper.log_error("collect_events failed refresh")
                return
            refresh_count = 0
        except Exception as e:
            helper.log_error( 'SANDFLY_ERROR(collect_events): {}'.format( str( e ) ) )
            return

        b_more_results = True

        if b_duplicate_alerts and b_test_mode is False and last_sequence_id is not None and last_seen_time is not None and alarm_type == "alert":
            min_last_sequence_id = "0"
            max_last_sequence_id = last_sequence_id
            while b_more_results is True:
                count, b_more_results, min_last_sequence_id, ignore_last_seen_time = get_sandfly_alarms_by_last_seen( helper, ew, alarm_type, b_duplicate_summary, base_url, access_token, max_last_sequence_id, min_last_sequence_id, last_seen_time )
                helper.log_info('collect_events last_seen result count: [{}] [{}]'.format(alarm_type, count))

        b_more_results = True

        if last_sequence_id is None and last_timestamp is not None:
            count, b_more_results, last_sequence_id, last_seen_time = get_sandfly_alarms_by_timestamp( helper, ew, alarm_type, b_results_summary, base_url, access_token, last_timestamp, last_seen_time )
            if last_sequence_id is not None:
                helper.save_check_point( checkpoint_key, last_sequence_id )
                helper.log_info('collect_events update checkpoint sequence_id: [{}] [{}]'.format(checkpoint_key, last_sequence_id))
            if last_seen_time is not None:
                helper.save_check_point( last_seen_key, last_seen_time )
                helper.log_info('collect_events update checkpoint last_seen  : [{}] [{}]'.format(last_seen_key, last_seen_time))
            event_count += count

        while b_more_results is True and b_test_mode is False:
            count, b_more_results, last_sequence_id, last_seen_time = get_sandfly_alarms_by_sequence_id( helper, ew, alarm_type, b_results_summary, base_url, access_token, last_sequence_id, last_seen_time )
            if last_sequence_id is not None:
                helper.save_check_point( checkpoint_key, last_sequence_id )
                helper.log_info('collect_events update checkpoint sequence_id: [{}] [{}]'.format(checkpoint_key, last_sequence_id))
            if last_seen_time is not None:
                helper.save_check_point( last_seen_key, last_seen_time )
                helper.log_info('collect_events update checkpoint last_seen  : [{}] [{}]'.format(last_seen_key, last_seen_time))
            event_count += count

        helper.log_info('collect_events event_count: [{}] [{}]'.format(alarm_type, event_count))

    t_now = datetime.now(timezone.utc)
    t_now_timestamp = t_now.strftime( "%Y-%m-%dT%H:%M:%SZ" )
    helper.save_check_point( stanza_checkpoint_timestamp, t_now_timestamp )
    helper.log_info('collect_events update checkpoint last_timestamp : [{}] [{}]'.format(stanza_checkpoint_timestamp, t_now_timestamp))

    helper.log_debug('collect_events [{}] success THE_END [{}] ===================='.format(my_input_type, my_stanza_name))

    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_sandfly_server_url = helper.get_arg('sandfly_server_url')
    opt_global_account = helper.get_arg('global_account')
    opt_sandfly_results = helper.get_arg('sandfly_results')
    opt_start_time = helper.get_arg('start_time')
    # In single instance mode, to get arguments of a particular input, use
    opt_sandfly_server_url = helper.get_arg('sandfly_server_url', stanza_name)
    opt_global_account = helper.get_arg('global_account', stanza_name)
    opt_sandfly_results = helper.get_arg('sandfly_results', stanza_name)
    opt_start_time = helper.get_arg('start_time', stanza_name)

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
