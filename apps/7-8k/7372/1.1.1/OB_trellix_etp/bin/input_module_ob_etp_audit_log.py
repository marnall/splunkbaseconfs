
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

CHECK_POINT_KEY = "audit_log_from"

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
    _from = definition.parameters.get('audit_log_from', None)
    if _from is not None:
        result = re.match("20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d.\d\d\d", _from)
        if result is None:
            raise ValueError('Format must be ISO format (yyyy-mm-ddTHH:MM:SS.fff)')
        else:
            pass
        try:
            res = datetime.datetime.fromisoformat(_from)
        except Exception as e:
            raise e
        
def get_token(client_id, secret):
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


def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    """
    opt_from = helper.get_arg('audit_log_from')
    opt_user_email_id = helper.get_arg('user_email_id')
    
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

    # first run time
    if state is None:
      if opt_from is not None:
        state = opt_from

      if opt_from is None:
          state = datetime.datetime.now(datetime.timezone.utc)
          state = f'{state:%Y-%m-%dT%H:%M:%S.%f}'[:-3]

      helper.save_check_point(CHECK_POINT_KEY, state)



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


    url = f'https://{global_etp_service_region}/api/v1/users/activitylogs/search'
    method = 'POST'
    _from = (datetime.datetime.strptime(state, "%Y-%m-%dT%H:%M:%S.%f")).replace(tzinfo=datetime.timezone.utc)
    # Trellix audit log API에 from만 넣을 경우 Internal server error 발생, 임시조치로 'to' 파라미터 추가
    _now = f'{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%dT%H:%M:%S.%f}'[:-3]
    _to = (datetime.datetime.strptime(_now, "%Y-%m-%dT%H:%M:%S.%f")).replace(tzinfo=datetime.timezone.utc)

    helper.log_info(f'Retrieve audit log from: {state}, to: {_now}')
    body = {
        'size': 100,
        'attributes': {
            # 'user_email_id': ['jabae2023@gmail.com'],
            'time': {
                'from': _from.strftime("%Y-%m-%dT%H:%M:%S+0000Z"),
                'to': _to.strftime("%Y-%m-%dT%H:%M:%S+0000Z")
            }
        }
    }
    if opt_user_email_id is not None and len(opt_user_email_id) > 0:
        user_email_list = [email.strip() for email in opt_user_email_id.split(';')]
        body['attributes']['user_mail_id'] = user_email_list

    #_show_tmp(helper, ew, payload)
    response = helper.send_http_request(url, method, payload=body,
                                        headers=headers, use_proxy=True, 
                                        verify=global_ssl_verify)
    
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()
    
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = json.loads(response.text)

    if r_json.get('data') is None:
        return
    else:
        size = len(r_json.get('data'))

    
    helper.log_info(f"Retrieve audit log successfully, size: {size}")
    #_show_tmp(helper, ew, r_json.get('meta'))

    sorted_data = sorted(r_json.get('data'), key=lambda x: x['attributes']['time'])
    # To create a splunk event
    for data in sorted_data:
        datetime_str_gmt = f"{data.get('attributes').get('time')}".replace('Z', '')
        origin_time = datetime.datetime.strptime(datetime_str_gmt, "%Y-%m-%dT%H:%M:%S%z")
        _time_epoch = origin_time.timestamp()

        state = (origin_time + datetime.timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S.%f")
        #state = origin_time.strftime("%Y-%m-%dT%H:%M:%S.%f")

        event = helper.new_event(
            data = json.dumps(data, ensure_ascii=False),
            time = _time_epoch, 
            index = helper.get_output_index(), 
            sourcetype = helper.get_sourcetype()
        )

        ew.write_event(event)
        
    helper.save_check_point(CHECK_POINT_KEY, state)
