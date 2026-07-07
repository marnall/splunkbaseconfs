# Copyright (c) 2024 Veritas Technologies LLC. All rights reserved
# encoding = utf-8
import time
import json
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
# CONSTANTS - do not change
NB_HEADER_VERSION = "application/vnd.netbackup+json;version="
NB_HEADER_VERSION_OCSF = "application/vnd.netbackup+ocsf+json;version="
NB_API_VERSION_FIELD_NAME = "X-NetBackup-API-Version"

def get_nbu_server_api_version(helper,ew,hostname):
    ping_url = 'https://{}/netbackup/ping'.format(hostname)
    try:
        response = requests.get(ping_url, headers={}, data={}, verify=False)
        if response.status_code == 200:
            VERSION = response.headers[NB_API_VERSION_FIELD_NAME]
        if int(VERSION.split('.')[0] ) < 11 and helper.get_arg('audit_event_format') == "ocsf":
            helper.log_error("Selected format is not supported by the NetBackup server.")
            event = helper.new_event(json.dumps({"error": "Selected format is not supported by the NetBackup server. Please select the correct format in the input configuration."}))
            ew.write_event(event)
            raise Exception("Selected format is not supported by the NetBackup server")
        return VERSION
    except requests.exceptions.RequestException as e:
        helper.log_error("Exception Occured :" + str(e))
        raise e
    except Exception as e:
        helper.log_error("Exception Occured :" + str(e))
        raise e

def get_nbu_version(helper,ew,hostname):
    serverInfoUrl = 'https://{}/netbackup/security/serverinfo'.format(hostname)
    try:
        response = requests.get(serverInfoUrl, headers={}, data={}, verify=False)
        responseJson = response.json()
        if response.status_code == 200:
            NetbackupVersion = responseJson['nbuVersion']
    except requests.exceptions.RequestException as e:
        helper.log_error("Exception Occured while fetching NetBackup version :" + str(e))
        raise e

    return NetbackupVersion

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # hostname = definition.parameters.get('hostname', None)
    # api_key = definition.parameters.get('api_key', None)
    # audit_event_format = definition.parameters.get('audit_event_format', None)
    pass

def collect_events(helper, ew):
    opt_hostname = helper.get_arg('hostname')
    opt_api_key = helper.get_arg('api_key')
    opt_audit_event_format = helper.get_arg('audit_event_format')
    version  = get_nbu_server_api_version(helper,ew,opt_hostname)
    helper.log_info("hostname={}".format(opt_hostname))
    eventType = None
    if(opt_audit_event_format == "ocsf"):
        helper.log_info("Using OCSF audit message format.")
        eventType = 0
    elif(opt_audit_event_format == "native"):
        helper.log_info("Using Netbackup Native audit format.")
        eventType = 1
    else:
        helper.log_info("Using Netbackup event notification.")
        eventType = 2

    """ Check if the script is running for the first time or the NetBackup version has changed
        If the NetBackup version has changed, then fetch the events from the beginning
        If the script is running for the first time, then fetch the events from the beginning
        If the script is running on the same day, then fetch the events from the last saved checkpoint
        only for eventType 2 (Notifications) as they reset their ID after upgrade
    """
    if eventType == 2:
        current_date = time.strftime("%Y-%m-%d")
        last_run_date = helper.get_check_point(opt_hostname + '_last_run_date')
        helper.log_info("Last Run Date: {}".format(last_run_date))
        if last_run_date is None or last_run_date != current_date:
            NbuVersion = get_nbu_version(helper, ew, opt_hostname)
            key = opt_hostname + '_nbu_version'
            helper.log_info("NetBackup Version: {}".format(NbuVersion))
            if helper.get_check_point(key) is None:
                helper.save_check_point(key, NbuVersion)
            elif helper.get_check_point(key) != NbuVersion:
                helper.save_check_point(key, NbuVersion)
                helper.log_info("NetBackup version has changed. Fetching Notifications from the beginning.")
                
                # deleting lastfetchedID checkpoint
                helper.delete_check_point(opt_hostname + opt_audit_event_format)
            helper.save_check_point('last_run_date', current_date)
            helper.log_info("Last Run Date saved: {}".format(current_date))

    headers = {
        'Accept': '{}{}'.format(NB_HEADER_VERSION_OCSF if eventType == 0 else NB_HEADER_VERSION, version),
        'Authorization': opt_api_key
    }

    limit =  100
    offset = 0
    key = opt_hostname + opt_audit_event_format
    lastFetchedId = helper.get_check_point(key)
    helper.log_info("Current State: {}".format(lastFetchedId))

    """ 
    Firstcall is only to Fetch the latest event from the server.
    and store its ID in the checkpoint. No events less than this ID will be fetched.
    """
    firstCall = False
    if lastFetchedId is None:
        firstCall = True
        helper.log_info("This is the first call to the server, No events will be added")
    url = get_formated_url(opt_hostname, limit, offset, lastFetchedId, eventType)
    helper.log_info("Initial URL: " + url)
    helper.log_info("---------------------------------Starting to get events from NetBackup API---------------------------------")
    while True:
        try:
            response = helper.send_http_request(url, 'GET', parameters=None, headers=headers,
                                                    cookies=None, verify=False, cert=None, timeout=None,
                                                    use_proxy=True)
            responsejson = response.json()
            if (response_count_zero(responsejson, helper)):
                helper.log_info("No Events to fetch from NetBackup API")
                helper.log_info("No Checkpoint saved as there are no events to fetch from NetBackup API")
                helper.log_info("Exiting the script")
                return
            if response.status_code == 200:
                if eventType == 0:
                    id = insertOcsfEventsToSplunkIndex(helper, ew, responsejson, firstCall)
                elif eventType == 1:
                    id = insertNativeEventsToSplunkIndex(helper, ew, responsejson, firstCall)
                else:
                    id = insertNotificationsToSplunkIndex(helper, ew, responsejson)
            else:
                helper.log_error("Error in getting response from NetBackup API: " + str(responsejson))
                return
            
            if firstCall:
                helper.log_info("First call to the server completed. Saving the last fetched ID: " + id)
                break

            if has_next(responsejson, eventType):
                 offset += limit
                 url = get_formated_url(opt_hostname, limit, offset, lastFetchedId, eventType)
                 helper.log_info("Next URL: " + url)
            else:
                helper.log_info("No more events to fetch from NetBackup API")
                break
        except Exception as e:
            helper.log_error("Error in getting response from NetBackup API: " + str(e))
            raise e
    helper.save_check_point(key, id)
    helper.log_info("Checkpoint saved: " + id)
    helper.log_info("Exiting the script")

def insertOcsfEventsToSplunkIndex(helper, ew, res, firstCall):
    helper.log_info("Inserting OCSF events from NetBackup API")
    for auditlog in res['data']:
        id = auditlog['metadata']['labels'][2].split(':')[1]
        if not firstCall:
            event = helper.new_event(json.dumps(auditlog), time=None,
                                host=helper.get_arg('hostname'),
                                index=helper.get_arg('index'), source=None, sourcetype=None, done=True,
                                unbroken=True)
            ew.write_event(event)
    return id

def insertNativeEventsToSplunkIndex(helper, ew, res, firstCall):
    helper.log_info("Inserting Native events from NetBackup API")
    for auditlog in res['data']:
        id = auditlog['id']
        if not firstCall:
            event = helper.new_event(json.dumps(auditlog), time=None,
                                host=helper.get_arg('hostname'),
                                index=helper.get_arg('index'), source=None, sourcetype=None, done=True,
                                unbroken=True)
            ew.write_event(event)
    return id

def insertNotificationsToSplunkIndex(helper, ew, res):
    helper.log_info("Inserting Notification from NetBackup API")
    for auditlog in res['data']:
        id = auditlog['id']
        event = helper.new_event(json.dumps(auditlog), time=None,
                            host=helper.get_arg('hostname'),
                            index=helper.get_arg('index'), source=None, sourcetype=None, done=True,
                            unbroken=True)
        ew.write_event(event)
    return id

def get_formated_url(hostname, limit, offset, lastFetchedId, eventType):
    if eventType == 0 or eventType == 1:
        if lastFetchedId is None:
            """
            Fetching the latest audit log from the server.
            """
            url = 'https://{}/netbackup/security/auditlogs?page%5Blimit%5D=1'.format(
                        hostname
                        )
        else:
            url = 'https://{}/netbackup/security/auditlogs?sort=id&filter=id%20gt%20{}&page%5Blimit%5D={}&page%5Boffset%5D={}'.format(
                hostname, lastFetchedId,limit, offset
            )
    else:
        if lastFetchedId is None:
            url = 'https://{}/netbackup/eventlog/notifications?sort=id&page%5Blimit%5D={}&page%5Boffset%5D={}'.format(
                        hostname, limit, offset
                        )
        else:
            url = 'https://{}/netbackup/eventlog/notifications?sort=id&filter=id%20gt%20{}&page%5Blimit%5D={}&page%5Boffset%5D={}'.format(
                hostname, lastFetchedId,limit, offset
            )
    return url

def has_next(response,eventType):
    if eventType >= 1 and 'next' in response['meta']['pagination']:
        return True
    if eventType == 0 and response['meta']['pagination']['next'] == True:
        return True
    return False

def response_count_zero(response, helper):
    try:
        if response['meta']['pagination']['count'] == 0:
            return True
        return False
    except Exception as e:
        helper.log_error("Error in getting response count: " + str(e))
        return False
