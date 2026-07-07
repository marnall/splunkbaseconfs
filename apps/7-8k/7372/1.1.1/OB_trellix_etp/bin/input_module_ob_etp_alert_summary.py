
# encoding = utf-8
import base64
import os
import sys
import time
import json
import datetime
import re

import utils
import requests
from dateutil import parser

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

CHECK_POINT_KEY = "from_last_modified_on"
STATUS_LIST = ("accepted", "deleted", "delivered", "dropped", "dropped oob", "permanent failure", "quarantined", "rejected", "scanned")

def _show_tmp(helper, ew, data):
    event = helper.new_event(
            data = json.dumps(data), 
            index = helper.get_output_index(), 
            sourcetype = helper.get_sourcetype()
        )
    ew.write_event(event)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # etp_service_region = definition.parameters.get('etp_service_region', None)
    # email_status = definition.parameters.get('email_status', None)
    from_last_modified_on = definition.parameters.get('from_last_modified_on', None)
    if from_last_modified_on is not None:
        result = re.match("20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d.\d\d\d", from_last_modified_on)
        if result is None:
            raise ValueError('Format must be ISO format (yyyy-mm-ddTHH:MM:SS.fff)')
        else:
            pass
        try:
            res = datetime.datetime.fromisoformat(from_last_modified_on)
        except Exception as e:
            raise e
        
def get_token(client_id, secret):
    try:
        auth_key_bytes = f'{client_id}:{secret}'.encode('ascii')
        auth_key_base64 = base64.b64encode(auth_key_bytes)
        auth_key_base64_str = auth_key_base64.decode('ascii')

        authentication = f'Basic {auth_key_base64_str}'

        url = 'https://auth.trellix.com/auth/realms/IAM/protocol/openid-connect/token'
        data = {'grant_type': 'client_credentials',
                'scope': 'etp.alrt.ro etp.trce.ro etp.admn.ro'}
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'{authentication}'}

        response = requests.post(url, data=data, headers=headers)

        response_data = response.json()
        access_token = response_data['access_token']

        return access_token
    except Exception as e:
        raise e



def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    """
    opt_use_api_v1 = helper.get_arg('use_api_v1')
    opt_email_status = helper.get_arg('email_status')
    opt_from_last_modified_on = helper.get_arg('from_last_modified_on')
    opt_time_lag_guard = helper.get_arg('time_lag_guard')

    helper.log_info( { 'opt_use_api_v1': opt_use_api_v1 } )
    helper.log_info( { 'opt_time_lag_guard': opt_time_lag_guard } )
    
    # get all detailed input stanzas
    input_all_stanza =  helper.get_input_stanza()
    
    # get global variable configuration
    global_trellix_auth_method = helper.get_global_setting("trellix_auth_method")
    global_api_key = helper.get_global_setting("api_key")
    global_client_id = helper.get_global_setting("client_id")
    global_secret = helper.get_global_setting("secret")
    global_etp_service_region = helper.get_global_setting("etp_service_region")
    global_ssl_verify = True if helper.get_global_setting("ssl_verify") == '1' else False

    access_token = ''

    if global_trellix_auth_method == 'client_credentials':
        if len(global_client_id) > 0 and len(global_secret) > 0:
            access_token = get_token(global_client_id, global_secret)
        else:
            helper.log_error('Trellix Client ID or Secret does not exist.')
            return


    # in Splunk cloud, it should be forced to set ssl verify true.
    try:
        server_info = utils.get_server_info(helper.service.token)
        if server_info.is_cloud_instance():
            global_ssl_verify = True
    except Exception as e: 
      helper.log_error(e)

    # get the loglevel from the setup page
    log_level = helper.get_log_level()
    
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)
    
    # delete checkpoint 
    # helper.delete_check_point(CHECK_POINT_KEY)

    # get checkpoint
    state = helper.get_check_point(CHECK_POINT_KEY)

    if state is None:
        # if there's no checkpoint(first time run), get time from user setting or current time
        if opt_from_last_modified_on is not None:
            state = opt_from_last_modified_on

        if opt_from_last_modified_on is None:
            state = datetime.datetime.now(datetime.timezone.utc)
            state = f'{state:%Y-%m-%dT%H:%M:%S.%f}'[:-3]

        helper.save_check_point(CHECK_POINT_KEY, state)
   
    if opt_time_lag_guard:
        opt_time_lag_guard = int(opt_time_lag_guard)
    else:
        opt_time_lag_guard = 5

    if opt_use_api_v1:
        opt_use_api_v1 = int(opt_use_api_v1)
    else:
        # default is using api v1
        opt_use_api_v1 = 1

    helper.log_info(f'(Inbound) Retrieve alerts from: {state}')

    if global_trellix_auth_method == 'client_credentials':
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
    else:
        headers = {
            'Content-Type': 'application/json',
            'x-fireeye-api-key': global_api_key
        }

    method = 'POST'
    payload = {
        'traffic_type': 'inbound',
        'size': 100,
    }
    if '[]' in opt_email_status:
        opt_email_status.remove('[]')

    # set url and payload depending api version
    if opt_use_api_v1:
        url = f'https://{global_etp_service_region}/api/v1/alerts'
        payload['fromLastModifiedOn'] = state
        if len(opt_email_status) > 0:
            payload['attributes'] = {
                'email_status': opt_email_status
            }
    else:
        url = f'https://{global_etp_service_region}/api/v2/public/alerts/search'
        payload['date_range'] = {
            'from': ((datetime.datetime.strptime(state, '%Y-%m-%dT%H:%M:%S.%f')).replace(tzinfo=datetime.timezone.utc)).isoformat().replace('+00:00', 'Z') ,
            'to': (datetime.datetime.now(datetime.timezone.utc)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        }
        if len(opt_email_status) > 0:
            payload['email_status'] = opt_email_status

    current_time = datetime.datetime.now(datetime.timezone.utc)
    state_dt = datetime.datetime.fromisoformat(state.replace('Z', '')+'+00:00')
    if utils.check_within_timedelta(helper, current_time, state_dt, opt_time_lag_guard):
        helper.log_info({
              'message': 'Skipped this interval because of time_lag_guard',
              'state': state
            })
        return

    #_show_tmp(helper, ew, payload)
    response = helper.send_http_request(url, method, payload=payload,
                                        headers=headers, use_proxy=True,
                                        verify=global_ssl_verify)

    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()

    size = r_json.get('meta').get('size')
    helper.log_info(r_json.get('meta'))

    if size == 0 or r_json.get('data') is None:
        helper.log_info(f'No data has been found from {state}')
        return

    if opt_use_api_v1:
        sorted_data = sorted(r_json.get('data'), key=lambda x: x['attributes']['meta']['last_modified_on'])
    else:
        sorted_data = sorted(r_json.get('data'), key=lambda x: x['alert_date'])

    # To create a splunk event
    for data in sorted_data:
        # datetime_str_gmt = f"{data.get('attributes').get('alert').get('timestamp')}"
        # origin_time = datetime.datetime.strptime(datetime_str_gmt, "%Y-%m-%dT%H:%M:%S.%f")
        # _time_epoch = datetime.datetime.fromisoformat(origin_time.strftime("%Y-%m-%dT%H:%M:%S.%f")).timestamp()
        if opt_use_api_v1:
            # 2025-05-26T14:35:12.123
            alert_dt = data.get('attributes').get('alert').get('timestamp') + '+00:00'
            modified_dt = data.get('attributes').get('meta').get('last_modified_on') + '+00:00'

            _time_epoch = datetime.datetime.fromisoformat(alert_dt).timestamp()
            data_last_modified_datetime = datetime.datetime.fromisoformat(modified_dt)
        else:
            # 2025-05-08T08:00:21Z
            alert_dt = data.get('alert_date')
            modified_dt = data.get('accepted_time')

            _time_epoch = parser.isoparse(alert_dt).timestamp()
            data_last_modified_datetime = parser.isoparse(modified_dt)

        if utils.check_within_timedelta(helper, current_time, data_last_modified_datetime, opt_time_lag_guard):
            helper.log_info({
              'message': 'Stopped importing alert data in the middle of the process because of time_lag_guard.',
              'data.attributes.meta.last_modified_on': state
            })
            break

        # state: 2025-05-26T14:35:12.123 포맷으로 저장
        if opt_use_api_v1:
            state = data.get('attributes').get('meta').get('last_modified_on')
        else:
            state = f"{(datetime.datetime.strptime(data.get('alert_date'), '%Y-%m-%dT%H:%M:%SZ') + datetime.timedelta(seconds=1)).replace(tzinfo=datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}"

        event = helper.new_event(
            data = json.dumps(data, ensure_ascii=False),
            time = _time_epoch,
            index = helper.get_output_index(),
            sourcetype = helper.get_sourcetype()
        )
        ew.write_event(event)
    helper.save_check_point(CHECK_POINT_KEY, state)
