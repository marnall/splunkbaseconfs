
# encoding = utf-8

import os
import sys
import base64
import urlparse
import json
from datetime import datetime, timedelta, date, time
from utils import get_checkpoint, save_checkpoint, access_token_storage, get_enterprise_profile

base_api_seam_url = "https://bluejeans.com/seamapi"
base_api_indigo_url = "https://indigo-api.bluejeans.com"
DATE_RANGE_DAYS = 1

#check if first call has been made
def first_call_check(helper):
    inputtype = helper.get_input_type()
    key_name = str(inputtype) + "_is_first_call"
    first_call_flag = helper.get_check_point(key_name)

    helper.log_debug("******** DATE RANGE IN FIRST CALL ******** " + str(first_call_flag))
    global DATE_RANGE_DAYS

    if first_call_flag == "true":
        helper.log_debug("******** DATE RANGE 1 ******** ")    
        DATE_RANGE_DAYS = 1
    else:
        DATE_RANGE_DAYS = 180
        helper.log_debug("******** DATE RANGE 180 ******** ")
        helper.save_check_point(key_name, "true")

def validate_input(helper, definition):
    bluejeans_creds = definition.parameters.get('bluejeans_creds', None)
    pass

def collect_events(helper, ew):
    # Retrieve runtime variables
    inputname = helper.get_input_stanza_names()
    inputtype = helper.get_input_type()
    inputsource = inputtype + ":" + inputname

    helper.log_info("input_type={0:s} input={1:s} message='Collecting events.'".format(inputtype,inputname))

    #validate access token
    user_details = access_token_storage(helper)
    
    # Create API request parameters
    method = 'GET'
    header = {}
    parameter = {}

    try:
        if not user_details['user_access_token']:
            helper.log_error("message='Error in generating user access token'")
            raise Exception('Error in generating user access token')

        user_access_token = user_details['user_access_token']
        user_id = user_details["user_id"]

        enterprise_profile = get_enterprise_profile(helper, user_id, user_access_token)

        if not enterprise_profile['user_enterprise_id']:
            helper.log_error("message='Error in fetching user's Enterprise Profile'")
            raise Exception("Error in fetching user's Enterprise Profile")

        enterprise_id = enterprise_profile['user_enterprise_id']

        helper.log_debug("input_type={0:s} input={1:s} message='Successfuly fetched Enterprise ID and Access token'".format(inputtype,inputname))

        first_call_check(helper)

        # Calculate Datetime Range for the API query parameters
        utc_today = datetime.utcnow().date()
        utc_yesterday = utc_today - timedelta(1)

        # start date-time will be "Date = (Yesterday's date - DATE_RANGE_DAYS+1), Time = 23:59.00  "
        start_date = utc_today - timedelta(DATE_RANGE_DAYS + 1)
        start_datetime = datetime.combine(start_date, datetime.max.time())

        # End date-time will be "Date = Yesterday's date, Time = 23:59.59 "
        end_datetime = datetime.combine(utc_yesterday, datetime.max.time())

        # Ex. values: starttime: 2018-06-07T23:59.59 to endtime: 2018-06-08T23:59.59

        start_datetime = start_datetime.strftime('%Y-%m-%dT%H:%M:%S%z') + '+00:00'
        end_datetime = end_datetime.strftime('%Y-%m-%dT%H:%M:%S%z') + '+00:00'

        parameter = {
            'limit': 0,
            'clientTZ': 'GMT',
            'filter': '[{"type":"string","comparison":"eq","value":"\'%Y-%m-%d\'","field":"dateFormat"},{"type":"date","comparison":"eq","value":"' + start_datetime + '","field":"lowts"},{"type":"date","comparison":"eq","value":"' + end_datetime + '","field":"hights"}]',
            'access_token': user_access_token,
            'app_name': 'command_center_splunk'
        }
        url = base_api_indigo_url + "/v2/enterprise/" + str(enterprise_id) + "/indigo/analytics/users/active"
                
        response = helper.send_http_request(url, method, parameters=parameter, payload=None, headers=header, cookies=None, verify=True, cert=None, timeout=50, use_proxy=False)
        
        helper.log_debug("input_type={0:s} input={1:s} message='Requesting commit data from Active Users Summary API.' url='{2:s}' parameters='{3:s}'".format(inputtype, inputname, url, json.dumps(parameter)))

        # Return API response code
        r_status = response.status_code
        helper.log_debug("input_type={0:s} input={1:s} message='Active Users Summary API response code' status_code={2:d}".format(inputtype,inputname, r_status))

        # Return API request status_code
        if r_status is not 200:
            helper.log_error("input_type={0:s} input={1:s} message='Active Users Summary API request unsuccessful.' status_code={2:d}".format(inputtype,inputname,r_status))
            response.raise_for_status()

        # Return API request as JSON
        obj = response.json()
        active_user_counts = obj['active']

        for item in active_user_counts:
            event = {}
            event = item

            eventTimestamp = str(item['the_date']) + 'T10:15:00.000Z'

            event['timestamp'] = eventTimestamp
            checkpoint_value = get_checkpoint(helper, eventTimestamp)

            if checkpoint_value:
                helper.log_debug("input_type={0:s} input={1:s} message='Event already pushed for Active Users Summary data at timestamp key {2:s}. Skipping this..'".format(inputtype, inputname, eventTimestamp))
            else:
                helper.log_debug("input_type={0:s} input={1:s} message='Pushing Active Users Summary data Event to Splunk at timestamp {2:s}'".format(inputtype, inputname, eventTimestamp))
                splunkEvent = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(event))
                ew.write_event(splunkEvent)
                save_checkpoint(helper, eventTimestamp, True)

        helper.log_info("input_type={0:s} input={1:s} message='Collection complete.'".format(inputtype, inputname))

    except Exception as error:
        helper.log_error("input_type={0:s} input={1:s} message='An unknown error occurred'".format(inputtype, inputname))
        raise error