
# encoding = utf-8

import os
import sys
import base64
import urlparse
import json
from datetime import datetime, timedelta, date, time
from utils import get_checkpoint, save_checkpoint, access_token_storage, get_enterprise_profile, save_last_pushed_date

base_api_seam_url = "https://bluejeans.com/seamapi"
base_api_indigo_url = "https://indigo-api.bluejeans.com"
DATE_RANGE_DAYS = 1
FIRST_SYNC_DAYS = 30
last_pushed_date = None

#check if first call has been made
def first_call_check(helper):
    global last_pushed_date
    inputtype = helper.get_input_type()
    key_name = str(inputtype) + "_last_pushed_date"
    last_pushed_date = helper.get_check_point(key_name)

    helper.log_debug("******** last_pushed_date IN FIRST CALL ******** " + str(last_pushed_date))
    
    if isinstance(last_pushed_date, (int, long)) or isinstance(last_pushed_date, int):
        helper.log_debug("******** last_pushed_date Found ******** ") 
    else:
        utc_today = datetime.utcnow()
        first_sync_days_ago = utc_today - timedelta(FIRST_SYNC_DAYS)
        first_sync_days_ago = int(round((first_sync_days_ago - datetime(1970, 1, 1)).total_seconds()))
        last_pushed_date = first_sync_days_ago
        helper.log_debug("******** last_pushed_date NOT found ******** ")
        save_last_pushed_date(helper, first_sync_days_ago)

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
        last_date = datetime.utcfromtimestamp(last_pushed_date).date()
        utc_today = datetime.utcnow().date()
        utc_yesterday = utc_today - timedelta(1)
        DATE_RANGE_DAYS = (utc_today - last_date).days

        # start date-time will be "Date = (Today's date - DATE_RANGE_DAYS+1), Time = 23:59.00  "
        start_date = utc_today - timedelta(DATE_RANGE_DAYS + 1)
        start_datetime = datetime.combine(start_date, datetime.max.time())

        # End date-time will be "Date = Yesterday's date, Time = 23:59.59 "
        end_datetime = datetime.combine(utc_yesterday, datetime.max.time())

        # Ex. values: starttime: 2018-06-07T23:59.59 to endtime: 2018-06-08T23:59.59

        start_datetime = start_datetime.strftime('%Y-%m-%dT%H:%M:%S%z') + '+00:00'
        end_datetime = end_datetime.strftime('%Y-%m-%dT%H:%M:%S%z') + '+00:00'

        parameter = {
            'clientTZ': 'GMT',
            'filter': '[{"type":"string","comparison":"eq","value":"DAY","field":"groupInterval"},{"type":"date","comparison":"eq","value":"' + start_datetime + '","field":"lowts"},{"type":"date","comparison":"eq","value":"' + end_datetime + '","field":"hights"}]',
            'access_token': user_access_token,
            'app_name': 'command_center_splunk'
        }
        url = base_api_indigo_url + "/v2/enterprise/" + str(enterprise_id) + "/indigo/analytics/meetings/usage"
                
        response = helper.send_http_request(url, method, parameters=parameter, payload=None, headers=header, cookies=None, verify=True, cert=None, timeout=50, use_proxy=False)
        
        helper.log_debug("input_type={0:s} input={1:s} message='Requesting commit data from Meetings Usage Summary API.' url='{2:s}' parameters='{3:s}'".format(inputtype, inputname, url, json.dumps(parameter)))

        # Return API response code
        r_status = response.status_code
        helper.log_debug("input_type={0:s} input={1:s} message='Meetings Usage Summary API response code' status_code={2:d}".format(inputtype,inputname, r_status))

        # Return API request status_code
        if r_status is not 200:
            helper.log_error("input_type={0:s} input={1:s} message='Meetings Usage Summary API request unsuccessful.' status_code={2:d}".format(inputtype,inputname,r_status))
            response.raise_for_status()

        # Return API request as JSON
        obj = response.json()
        usage = obj['usage']

        for item in usage:
            event = item
            epochTimestamp = event['Date']
            t_utc = datetime.utcfromtimestamp(epochTimestamp/1000)
            fmt = '%Y-%m-%d' 
            eventTimestamp = t_utc.strftime(fmt) + 'T10:15:00.000Z'
            helper.log_debug('\n\n eventTimestamp: ' + str(eventTimestamp))
            checkpoint_value = get_checkpoint(helper, eventTimestamp)

            if checkpoint_value:
                helper.log_debug("input_type={0:s} input={1:s} message='Event already pushed for Meetings Usage Summary data at timestamp key {2:s}. Skipping this..'".format(inputtype, inputname, eventTimestamp))
            else:
                event['timestamp'] = eventTimestamp
                helper.log_debug("input_type={0:s} input={1:s} message='Pushing Meetings Usage Summary Event to Splunk'".format(inputtype, inputname))
                splunkEvent = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(event))
                ew.write_event(splunkEvent)
                save_checkpoint(helper, eventTimestamp, True)
                save_last_pushed_date(helper, int(round(epochTimestamp/1000)))
            
        helper.log_info("input_type={0:s} input={1:s} message='Collection complete.'".format(inputtype, inputname))

    except Exception as error:
        helper.log_error("input_type={0:s} input={1:s} message='An unknown error occurred'".format(inputtype, inputname))
        raise error