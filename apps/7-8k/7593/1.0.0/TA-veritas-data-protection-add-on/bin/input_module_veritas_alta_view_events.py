# Copyright (c) 2024 Veritas Technologies LLC. All rights reserved
# encoding = utf-8
import json
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
#CONSTANT - do not change
HOSTNAME = 'hostname'
API_KEY = 'api_key'
ALTA = 'alta'
INDEX = 'index'
UNDERSCORE = '_'
AUDIT_EVENT_FORMAT = 'audit_event_format'
ALTA_NATIVE_HEADER = 'application/vnd.api+json;version=1.0'
ALTA_OCSF_HEADER = 'application/vnd.api+ocsf+json;version=1.0'


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # hostname = definition.parameters.get('hostname', None)
    # api_key = definition.parameters.get('api_key', None)
    pass

def collect_events(helper, ew):
    opt_hostname = helper.get_arg(HOSTNAME)
    opt_api_key = helper.get_arg(API_KEY)
    opt_audit_event_format = helper.get_arg(AUDIT_EVENT_FORMAT)

    helper.log_info("hostname={}".format(opt_hostname))

    eventType = None
    if(opt_audit_event_format == "ocsf"):
        helper.log_info("Using Alta view OCSF audit message format.")
        eventType = 0
    else:
        helper.log_info("Using Alta View Native audit format.")
        eventType = 1
    
    header = {
        'Accept': '{}'.format( ALTA_OCSF_HEADER if eventType == 0 else ALTA_NATIVE_HEADER),
        'Authorization': 'Bearer ' + opt_api_key
    }

    limit = 100
    offset = 0
    key = opt_hostname + UNDERSCORE + ALTA + UNDERSCORE + opt_audit_event_format
    lastFetchedTimeStamp = helper.get_check_point(key)
    helper.log_info("Current State: {}".format(lastFetchedTimeStamp))

    firstCall = False
    if lastFetchedTimeStamp is None:
        firstCall = True
        helper.log_info("This is the first call to the server, No events will be added")

    url = get_formatted_url(opt_hostname, limit, offset, lastFetchedTimeStamp)
    helper.log_info("Initial URL: " + url)
    helper.log_info("---------------------------------Starting to retrive events from ALTA API---------------------------------")
    CurrentTimeStamp = None
    while True:
        try:
            response = helper.send_http_request(url, 'GET', parameters=None, headers=header,
                                                        cookies=None, verify=False, cert=None, timeout=None,
                                                        use_proxy=True)
            
            responseJson = response.json()

            if response.status_code != 200:
                helper.log_error("Failed to get response from the server. Status code: " + str(responseJson))
                return

            if(len(responseJson['data']) == 0):
                helper.log_info("No Events to fetch from ALTA API")
                helper.log_info("No Checkpoint saved as there are no events to fetch from ALTA API")
                helper.log_info("Exiting the script")
                return

            helper.log_info("Total Events fetched: " + str(len(responseJson['data'])))
            if response.status_code == 200:
                if eventType == 1:
                    CurrentTimeStamp = InsertAltaNativeEvent(helper, ew, responseJson, firstCall)
                else:
                    CurrentTimeStamp = InsertAltaOcsfEvent(helper, ew, responseJson, firstCall)
            
            if firstCall:
                break

            if eventType == 1:
                if responseJson['meta']['pagination']['hasNext'] is False:
                    helper.log_info("No more events to fetch from ALTA API")
                    break
            else:
                if responseJson['meta']['hasNext'] == "false":
                    helper.log_info("No more events to fetch from ALTA API")
                    break

            offset += limit
            url = get_formatted_url(opt_hostname, limit, offset, lastFetchedTimeStamp)
            helper.log_info("Next URL: " + url)

        except Exception as e:
            helper.log_error("Exception Occured: " + str(e))
            return
    helper.save_check_point(key, CurrentTimeStamp)
    helper.log_info("Checkpoint saved: " + CurrentTimeStamp)
    helper.log_info("Exiting the script")

def InsertAltaNativeEvent(helper, ew, responseJson, firstCall):
    helper.log_info("Inserting Native events to Splunk")
    for data in responseJson['data']:
        if not firstCall:
            event = helper.new_event(json.dumps(data), time=None,
                        host=helper.get_arg(HOSTNAME),
                        index=helper.get_arg(INDEX), source=None, sourcetype=None, done=True,
                        unbroken=True)
            ew.write_event(event)
        CurrentTimeStamp = data['attributes']['auditRaisedTime']
    return CurrentTimeStamp

def InsertAltaOcsfEvent(helper, ew, responseJson, firstCall):
    helper.log_info("Inserting OCSF events to Splunk")
    for data in responseJson['data']:
        if not firstCall:
            event = helper.new_event(json.dumps(data), time=None,
                        host=helper.get_arg(HOSTNAME),
                        index=helper.get_arg(INDEX), source=None, sourcetype=None, done=True,
                        unbroken=True)
            ew.write_event(event)
        CurrentTimeStamp = convert_epoch_to_iso(data['time'])
    return CurrentTimeStamp

def get_formatted_url(opt_hostname, limit, offset, lastFetchedTimeStamp):
    if lastFetchedTimeStamp is None:
        """
            Fetching the latest audit log from the server.
        """
        url = 'https://{}/api/eventlog/audit/events?page%5Blimit%5D=1'.format(
            opt_hostname)
    else:
        url = 'https://{}/api/eventlog/audit/events?filter=auditRaisedTime%20gt%20{}&page%5Boffset%5D={}&page%5Blimit%5D={}&sort=auditRaisedTime'.format(
            opt_hostname, lastFetchedTimeStamp, offset, limit)
    return url

def convert_epoch_to_iso(epoch):
    timestamp_s = epoch / 1000
    dt_object = datetime.datetime.fromtimestamp(timestamp_s, datetime.timezone.utc)
    iso_format = dt_object.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    return iso_format
