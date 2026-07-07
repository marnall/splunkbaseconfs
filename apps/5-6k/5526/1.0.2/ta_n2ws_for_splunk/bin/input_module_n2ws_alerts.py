

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

    # alerts = definition.parameters.get('alerts', None)

    # dashboard = definition.parameters.get('dashboard', None)

    pass

   



def collect_events(helper, ew):
    helper.log_info("collecting events")

    class vars:
        opt_alerts = helper.get_arg('alerts')
        opt_dashboard = helper.get_arg('dashboard')
        global_n2ws_api_url = helper.get_global_setting("api_url")
        global_n2ws_api_key = helper.get_global_setting("api_key")
        access_key = helper.get_check_point("access_key")
        refresh_key = helper.get_check_point("refresh_key")
        last_from_id = helper.get_global_setting("last_from_id")

    

    def generate_access_keys():



        response = helper.send_http_request(vars.global_n2ws_api_url + "/token/obtain/external_monitoring/", "POST",

        parameters=None, payload={ "api_key": vars.global_n2ws_api_key },

            headers= {

                 'Content-Type': 'application/json',

                  'Authorization': 'true'

              }, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)

        response.raise_for_status()

        jobj = response.json()

        vars.access_key = jobj["access"]

        vars.refresh_key = jobj["refresh"]

        helper.save_check_point("access_key", vars.access_key)

        helper.save_check_point("refresh_key", vars.refresh_key)

            

    def refresh_access_key():



        response = helper.send_http_request(vars.global_n2ws_api_url + "/token/refresh/", "POST",

        parameters=None, payload={ "refresh": vars.refresh_key },

            headers= {

                 'Content-Type': 'application/json',

                  'Authorization': 'true'

              }, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)              

        if response.status_code == 200:

            jobj = response.json()

            vars.access_key = jobj["access"]

            helper.save_check_point("access_key", vars.access_key)

            return True

        else:

            helper.log_debug("refresh key failed with status code '{}'".format(response.status_code));

            return False

        

    def n2ws_get(api):



        url = vars.global_n2ws_api_url + api

        helper.log_debug("get url '{}'".format(url))

        

        if vars.access_key is None:

            helper.log_debug("no access key, generating.")

            generate_access_keys()

            helper.log_debug("generated access key '{}', refresh key '{}'".format(vars.access_key, vars.refresh_key))

        

        headers = {

          'Content-Type': 'application/json',

          'Authorization': 'Bearer {}'.format(vars.access_key)

        }

        

        response = helper.send_http_request(url, "GET", parameters=None, payload=None, headers= headers, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)

        if response.status_code != 200:

            helper.log_debug("get - failure, status code {}".format(response.status_code))

            

            if response.status_code == 401:

                # try and refresh our token

                helper.log_debug("refreshing token using refresh key '{}'".format(vars.refresh_key))

                refresh_result = refresh_access_key()

                if not refresh_result:

                    helper.log_debug("could not refresh token '{}', re-generating keys".format(vars.access_key))

                    vars.access_key = None

                    vars.refresh_key = None

                    generate_access_keys()

                    

                helper.log_debug('regetting, using new access key {}'.format(vars.access_key))

                headers = {

                  'Content-Type': 'application/json',

                  'Authorization': 'Bearer {}'.format(vars.access_key)

                }

                response = helper.send_http_request(url, "GET", parameters=None, payload=None, headers=headers, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)

          

        if response.status_code == 200:

            return response.json()

        else:

            response.raise_for_status()

                     

                     

    helper.log_debug("initializing with:\nurl '{}'.\napi key '{}'.\nvars.access_key '{}'.\nvars.refresh_key '{}'"

        .format(vars.global_n2ws_api_url,vars.global_n2ws_api_key,vars.access_key,vars.refresh_key))




    # get alerts
    from_id = helper.get_check_point("from_id")
    if from_id is None:
        from_id = vars.last_from_id
    if from_id is None:
        url = "/external_monitoring/alerts"
    else:
        url = "/external_monitoring/alerts/?from_id={}".format(from_id)

    
    helper.log_debug("getting alerts using url '{}'".format(url))

    alerts = n2ws_get(url)
    import json
    for alert in alerts:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(alert))
        ew.write_event(event)
        alert_id =int(alert['id'])
        if from_id is None or from_id < alert_id:
            from_id = alert_id

    if from_id is not None:
        helper.save_check_point("from_id", from_id)

