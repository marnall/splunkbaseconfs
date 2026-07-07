
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests
from workdaylib import Workday, VALID_INPUTS, VALID_PROXIES


MIN_INTERVAL = 120

USER_AGENT = "Workday Add-on for Splunk v2.2.2"

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
    # global_account = definition.parameters.get('global_account', None)
    # include_target_details = definition.parameters.get('include_target_details', None)
    # start_time = definition.parameters.get('start_time', None)
    pass

def validate_proxy(helper, proxy):
    errors = []
    if not proxy["proxy_url"]:
        errors.append("Proxy Host can not be empty")
    if not proxy["proxy_port"]:
        errors.append("Proxy Port can not be empty")
    if proxy["proxy_type"] not in VALID_PROXIES:
        errors.append("Invalid proxy type \"{}\", supported values are \"{}\"".format(proxy["proxy_type"],
                                                                                      "|".join(VALID_PROXIES)))
    if len(errors) > 0:
        for message in errors:
            helper.log_error(message)
        sys.exit(1)

def event_writer(helper, wday, subset_events, include_target_details, input_source, index, sourcetype, ew):
    for each in subset_events:
        each["tenantId"] = wday.tenant
        each["tenantHost"] = wday.host
        if not include_target_details and "target" in each:
            del each["target"]
        event = helper.new_event(
            source=input_source,
            index=index,
            sourcetype=sourcetype,
            data=json.dumps(each)
        )
        ew.write_event(event)

def validate_timestamp(helper, timestamp):
    checkpoint_format = "%Y-%m-%dT%H:%M:%SZ"
    helper.log_debug("Time format checker")
    helper.log_debug("Time stamp"+str(timestamp))
    if isinstance(timestamp, str):
        helper.log_debug("Timestamp is string. Proceed to save")
        return timestamp
    return timestamp.strftime(checkpoint_format)

def save_get_checkpoint(helper, input_name, timestamp):
    checkpointer = validate_timestamp(helper, timestamp)
    helper.save_check_point(input_name, checkpointer)

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_include_target_details = helper.get_arg('include_target_details')
    opt_start_time = helper.get_arg('start_time')
    # In single instance mode, to get arguments of a particular input, use
    opt_include_target_details = helper.get_arg('include_target_details', stanza_name)
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

    if helper.get_log_level() == "DEBUG":
        import traceback
        debug = True
    else:
        debug = False

    try:
        # Input Details

        stanza = helper.get_input_stanza_names()
        stanza_name = helper.get_arg("global_account",input_stanza_name=stanza)
        
        # Retrieve tenant details
        tenant_details = helper.get_arg('global_account')

        name = tenant_details['name']
        workday_rest_api_endpoint = tenant_details['workday_rest_api_endpoint']
        token_endpoint = tenant_details['token_endpoint']
        refresh_token = tenant_details['refresh_token']
        client_id = tenant_details['client_id']
        client_secret = tenant_details['client_secret']
        if '/api/v1/' in workday_rest_api_endpoint:
            index = workday_rest_api_endpoint.find('/api/')
            workday_rest_api_endpoint = workday_rest_api_endpoint[:index+4] + '/privacy' + workday_rest_api_endpoint[index+4:]
        
        # Retrieve input details
        input_type = helper.get_input_type()
        input_name = helper.get_arg("name")
        input_source = input_type + ':' + input_name
        
        include_target_details = helper.get_arg("include_target_details")
        sourcetype = helper.get_arg("sourcetype")
        index = helper.get_arg("index")
        # helper.log_debug("Rest api tenant:" + str(workday_rest_api_endpoint))

        #Check for empty inputs
        empty_fields = []
        if not workday_rest_api_endpoint:
            empty_fields.append("Workday REST API Endpoint")
        if not token_endpoint:
            empty_fields.append("Token Endpoint")
        if not client_id:
            empty_fields.append("Client ID")
        if not client_secret:
            empty_fields.append("Client Secret")
        if not refresh_token:
            empty_fields.append("Refresh Token")
        if len(empty_fields) > 0:
            raise ValueError("Empty fields in global configuration: {}".format(", ".join(empty_fields)))


        # Add Proxy server if enabled
        # Convert AoB proxy settings to `proxies` dictionary expected by requests
        proxies = {}
        proxy = helper.get_proxy()
        if proxy:
            validate_proxy(helper, proxy)

            if proxy["proxy_username"] and proxy["proxy_password"]:
                auth = proxy["proxy_username"] + ":" + proxy["proxy_password"] + "@"
                auth_logsafe = proxy["proxy_username"] + ":<redacted>@"
            else:
                auth = auth_logsafe = ""

            scheme = proxy["proxy_type"]
            if scheme == "https":
                if proxy["proxy_url"].startswith("https://"):
                    # Default to http for initial CONNECT to proxy server, but override if specified in the url
                    scheme = "https"
                    proxy["proxy_url"] = proxy["proxy_url"].lstrip("https://")
                else:
                    scheme = "http"

            url = "{scheme}://{auth}{uri}:{port}".format(
                scheme=scheme,
                auth=auth,
                uri=proxy["proxy_url"],
                port=proxy["proxy_port"]
            )

            url_logsafe = "{scheme}://{auth}{uri}:{port}".format(
                scheme=scheme,
                auth=auth_logsafe,
                uri=proxy["proxy_url"],
                port=proxy["proxy_port"]
            )

            proxies = {"http": url, "https": url}

            helper.log_debug("Using configured proxy for all requests: {}".format(url_logsafe))

        # Construct Workday client from the provided global config
        wday = Workday(workday_rest_api_endpoint, token_endpoint, client_id, client_secret, refresh_token,
                       http_user_agent=USER_AGENT, proxies=proxies, helper=helper)

    except ValueError as error:
        helper.log_error(str(error))
        if debug: helper.log_debug("".join(traceback.format_exc()))
        sys.exit(1)

    if input_type == "user_activity":
        api_endpoint = "/activityLogging"
        # Pull checkpoint value and setup query range for this run
        # Only pull up to 2 minutes in the past to allow time for events to be available in the report
        checkpoint_format = "%Y-%m-%dT%H:%M:%SZ"
        time_diff_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        end_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=2)
        
        # From inputs
        input_start_time = helper.get_arg("start_time")
        # From saved checkpoint
        checkpointer = helper.get_check_point(input_name)
        
        if checkpointer:
            start_time = checkpointer
            helper.log_debug("Checkpoint. Starting data collection from :"+str(start_time))
        elif input_start_time:
            start_time = datetime.datetime.strptime(input_start_time, checkpoint_format)
            helper.log_debug("Input start date. Starting data collection from :"+str(start_time.strftime(checkpoint_format)))
        else:
            start_time = end_time - datetime.timedelta(minutes=60)
            helper.log_info("No timestamp checkpoint found for input \"{}\", starting from now ({})".format(
                name,
                start_time.strftime(checkpoint_format)
                ))
        helper.log_debug("Timestamp to save: "+str(start_time))

        # Save current time now to preserve original start time in case of errors
        start_time = validate_timestamp(helper, start_time)
        save_get_checkpoint(helper, input_name, start_time)

        # Confirm that the checkpoint is in the correct format
        try:
            if '.' in start_time:
                start_time = start_time.split('.')[0] + 'Z'
                helper.log_debug('set_time='+str(start_time))
                start_time = datetime.datetime.strptime(start_time, checkpoint_format)
            helper.log_debug('start_time='+str(start_time))        
        except ValueError as error:
            helper.log_error("Invalid checkpoint value for input \"{}:{}\", aborting ({})".format(input_type, input_name, str(error)))
            sys.exit(1)
        start_time = validate_timestamp(helper, start_time)
        end_time = validate_timestamp(helper, end_time)

        helper.log_info("Starting input \"{}:{}\" for window ({}, {})".format(
            input_type,
            input_name,
            start_time,
            end_time
            ))
        try:
            input_start = time.time()
            batch_size = 1000
            api_start_time = start_time # wday.timestamp(start_time)
            api_end_time = end_time # wday.timestamp(end_time)
            event_count = wday.get(api_endpoint, headers={"Content-Type": "application/json"},
                                    params={"from": api_start_time, "to": api_end_time,
                                            "returnUserActivityEntryCount": "true", "type": "userActivity"})
            total_events = 0
            if event_count.status_code == 200:
                total_events_data = event_count.json().get('data', None)
                if total_events_data:
                    total_events = total_events_data[0].get('userActivityEntryCount', 0)
                    helper.log_info("Total events to be fetched - {}".format(
                        str(total_events)))
                else:
                    helper.log_error("No data found for the given time range : Start : {}, End : {}".format(
                        str(start_time),
                        str(end_time)
                    ))
                    helper.log_error("Exiting..")
                    sys.exit(1)
            else:   
                helper.log_error("Could not fetch event count for the given time.")
                helper.log_error("Time range - Start : {}, End : {}. Reason : {}, Exiting with code : {}".format(
                    str(start_time),
                    str(end_time),
                    str(event_count.reason),
                    str(event_count.status_code)
                ))
            # Pull all events if total is less than 10,000. Once completed, save the time checker
            # from the end time value
            if total_events < 10000:
                offset = 0
                event_total = 0
                results = []
                while total_events >= offset:
                    try:
                        helper.log_debug("Line: 368: api_start_time= "+str(api_start_time)+", type= "+str(type(api_start_time)))
                        helper.log_debug("Line: 369: api_end_time= "+str(api_end_time)+", type= "+str(type(api_end_time)))
                        events = wday.get(api_endpoint, headers={"Content-Type": "application/json"},
                                            params={"from": api_start_time, "to": api_end_time, "offset": offset,
                                                  "limit": batch_size,
                                                  "type": "userActivity", "instancesReturned": 1}
                                          )
                    except Exception as error:
                        helper.log_error(
                            "Exception occured retrieving data from Workday Tenant. Error Code: {}".format(error))
                    
                    if events.status_code != 200:
                        helper.log_error(
                            "Error retrieving data from Workday Tenant. Error Code: {}, Reason: {}".format(
                                events.status_code,
                                events.reason
                            ))
                        continue
                    else:
                        subset_events = json.loads(events.content).get('data', [])
                        event_total += len(subset_events)
                        results.extend(subset_events)
                    offset += batch_size
                # print all results at once

                event_writer(helper, wday, results, include_target_details, input_source, index, sourcetype,ew)
                helper.save_check_point(input_name, end_time)
            else:
                '''
                When events are more than 10k, it becomes necessary to incrementally query events and store that data.
                This is done iteratively where at after collection 9900 events, the timestamp of the last event
                is recorded as the start time for the next subsequent calls. Hence, when the 10K events are retrieved,
                it saves the timestamp of the last event and starts the next query until the end time
                '''
                event_total = 0
                batch_size = 1000
                offset = 0
                # Check number of events matching the total collected
                results = []
                while total_events > event_total:
                    try:
                        events = wday.get(api_endpoint, headers={"Content-Type": "application/json"},
                                          params={"from": api_start_time, "to": api_end_time, "offset": offset,
                                                  "limit": batch_size,
                                                  "type": "userActivity", "instancesReturned": 1}
                                          )
                    except Exception as error:
                        helper.log_error(
                            "Exception occurred retrieving data from Workday Tenant. Error Code: {}".format(error))
                    if events.status_code != 200:
                        helper.log_error(
                            "Error retrieving data from Workday Tenant. Error Code: {}, Reason: {}".format(
                                events.status_code,
                                events.reason
                            ))
                    else:
                        subset_events = json.loads(events.content).get('data', [])
                        # Add events to a list before printing
                        results.extend(subset_events)
                        # Set a hard limit of offset being 10,000 and only print and update offset if events exist
                        # else, set the offset to 0 and save the timestamp as the last event from previous call
                        if len(subset_events) > 0 and offset <= 9900:
                            event_total += len(subset_events)
                            offset += batch_size
                            # If only less than 100 events are left, 
                            if total_events - event_total < 100:
                                latest_event_timestamp = results[-1]['requestTime']
                                if '.' in latest_event_timestamp:
                                    split_time = latest_event_timestamp.split('.')[0] + 'Z'
                                    save_time = datetime.datetime.strptime(split_time, checkpoint_format)
                                    helper.save_check_point(input_name, save_time.strftime(checkpoint_format))
                                    helper.log_debug("new api start time: {}".format(str(latest_event_timestamp)))   
                                event_writer(helper, wday, results, include_target_details, input_source, index, sourcetype,ew)
                                results = []
                        else:                            
                            # Set the start time to the latest event for subsequent calls
                            if len(results) > 0:
                                latest_event_timestamp = results[-1]['requestTime']
                                if '.' in latest_event_timestamp:
                                    split_time = latest_event_timestamp.split('.')[0] + 'Z'
                                    save_time = datetime.datetime.strptime(split_time, checkpoint_format)
                                    helper.save_check_point(input_name, save_time.strftime(checkpoint_format))
                                event_writer(helper, wday, results, include_target_details, input_source, index, sourcetype,ew)
                            results = []
                            offset = 0
                            api_start_time = latest_event_timestamp
                # Save end time once all events expected are recovered
                # helper.save_check_point(input_name, api_end_time)
            # Log event runtime
            input_runtime = time.time() - input_start
            helper.log_info("Finished input \"{}:{}\" for window ({}, {}) in {} seconds, {} events written".format(
                input_type,
                input_name,
                start_time,
                api_end_time,
                round(input_runtime, 2),
                event_total
            ))

        except requests.exceptions.ProxyError as error:
            helper.log_error("Unable to connect to proxy host, Error: {}".format(str(error)))
            if debug: helper.log_debug("".join(traceback.format_exc()))

        except requests.exceptions.ConnectionError as error:
            helper.log_error("Unable to connect to host")
            if debug: helper.log_debug("".join(traceback.format_exc()))

        except requests.exceptions.Timeout as error:
            helper.log_error("Request timed out, retries exhausted")
            if debug: helper.log_debug("".join(traceback.format_exc()))

        except requests.exceptions.HTTPError as error:
            helper.log_error(
                "Request failed with error code ({}), retries exhausted".format(error.response.status_code))
            if debug: helper.log_debug("".join(traceback.format_exc()))

        except Exception as error:
            helper.log_error("Unknown exception occurred ({})".format(str(error)))
            if debug: helper.log_debug("".join(traceback.format_exc()))

    # End of script        
    else:
            helper.log_warning(
                "Invalid input \"{}:{}\", supported values are \"{}\"".format(input_type, input_name, "|".join(VALID_INPUTS)))

