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

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # report_url = definition.parameters.get('report_url', None)
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

def validate_timestamp(helper, timestamp):
    checkpoint_format = "%Y-%m-%dT%H:%M:%SZ"
    helper.log_debug("Time format checker")
    helper.log_debug("Time stamp : "+str(timestamp))
    if isinstance(timestamp, str):
        helper.log_debug("Timestamp is string.")
        return timestamp
    return timestamp.strftime(checkpoint_format)
    
def event_writer(helper, wday, subset_events, input_source, index, sourcetype, ew):
    # Write new for signons
    for each in subset_events:
        event = helper.new_event(
            source=input_source,
            index=index,
            sourcetype=sourcetype,
            data=json.dumps(each)
        )
        ew.write_event(event)



def save_get_checkpoint(helper, input_name, timestamp):
    checkpointer = validate_timestamp(helper, timestamp)
    helper.save_check_point(input_name, checkpointer)

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_report_url = helper.get_arg('report_url')
    # In single instance mode, to get arguments of a particular input, use
    opt_report_url = helper.get_arg('report_url', stanza_name)

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
        helper.log_debug("Input type - "+str(input_type))
        input_name = helper.get_arg("name")
        helper.log_debug("Input name - "+str(input_name))
        
        # include_target_details = helper.get_arg("include_target_details")
        sourcetype = helper.get_arg("sourcetype")
        index = helper.get_arg("index")

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

    if input_type == "signon_activity":

        # Only pull up to 2 minutes in the past to allow time for events to be available in the report
        checkpoint_format = "%Y-%m-%dT%H:%M:%SZ"
        to_moment = datetime.datetime.utcnow() - datetime.timedelta(minutes=2)
        
        # Get From moment
        input_from_moment = helper.get_arg("from_moment")
        
        # From saved checkpoint
        checkpointer = helper.get_check_point(input_name)
        helper.log_debug("Checkpointer - "+str(checkpointer)+ " ; sourcetype - "+str(sourcetype))
        
        if checkpointer:
            from_moment = checkpointer
            helper.log_debug("Checkpoint. Starting data collection from :"+str(from_moment))
        elif input_from_moment:
            from_moment = datetime.datetime.strptime(input_from_moment, checkpoint_format)
            helper.log_debug("Input start date. Starting data collection from :"+str(from_moment.strftime(checkpoint_format)))
        else:
            from_moment = to_moment - datetime.timedelta(minutes=1440)
            helper.log_info("No timestamp checkpoint found for input \"{}\", starting from ({})".format(
                name,
                from_moment.strftime(checkpoint_format)
                ))
        
        # Validate timestamps
        from_moment = validate_timestamp(helper, from_moment)
        to_moment = validate_timestamp(helper, to_moment)

        helper.log_info("Starting input \"{}:{}\" for window ({}, {})".format(
            input_type,
            input_name,
            from_moment,
            to_moment
            ))
        
        try:
            input_start = time.time()
            event_total = 0
            
            # Construct Report URL
            report_uri = helper.get_arg("report_url")
            if '?' in report_uri:
                report_uri = report_uri.split('?')[0]

            report_url = report_uri + '?from_moment=' + str(from_moment) + '&to_moment=' + str(to_moment) + '&format=json'
            helper.log_debug("Constructed report URL - "+str(report_url))

            # Get Report entries
            report = wday.get(report_url, headers={"Content-Type":"application/json"})
            input_source = input_type + ':' + input_name
            if report.status_code == 200:
                report_entries = report.json().get('Report_Entry', None)
                if report_entries:
                    event_total = len(report_entries)
                    event_writer(helper, wday, report_entries, input_source, index, sourcetype, ew)
                    
                    # Save timestamp
                    helper.log_debug("Timestamp to save: "+str(to_moment))
                    save_get_checkpoint(helper, input_name, to_moment)                    
                else:
                    helper.log_error("No data found for the given time range : Start : {}, End : {}".format(
                        str(from_moment),
                        str(to_moment)
                    ))
                    helper.log_error("Exiting..")
                    sys.exit(1)
            else:
                helper.log_error("Could not fetch event count for the given time.")
                helper.log_error("Time range - Start : {}, End : {}. Reason : {}, Exiting with code : {}".format(
                    str(from_moment),
                    str(to_moment),
                    str(report.reason),
                    str(report.status_code)
                ))


            # Log event runtime
            input_runtime = time.time() - input_start
            helper.log_info("Finished input \"{}:{}\" for window ({}, {}) in {} seconds, {} events written".format(
                input_type,
                input_name,
                from_moment,
                to_moment,
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
