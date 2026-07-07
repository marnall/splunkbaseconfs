import os
import sys
import json
import time
import datetime
import calendar
from datetime import timezone
import voUtils
#from future.moves.urllib.request import urlopen, Request, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener
#from future.moves.urllib.error import HTTPError

try:
    # For Python 3.0 and later
    from urllib.request import urlopen, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener, Request
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener, Request
try:
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import HTTPError


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
    # organization_id = definition.parameters.get('organization_id', None)
    # api_id = definition.parameters.get('api_id', None)
    # api_key = definition.parameters.get('api_key', None)
    pass

def get_check_point(helper, check_point_key):
    md5 = helper.get_check_point(check_point_key)
    if (md5 not in [None, '']):
        helper.log_info(
            "Valid MD5 found for {}. Its value is {}".format(check_point_key, md5))
        return md5
    else:
        helper.log_info(
            "No MD5 found for {}. Data has to be ingested.".format(check_point_key))
        return None

def getAlert(helper, headers, uuid):
    helper.log_info("getAlert() entry")
    try:
        #t = time.perf_counter()
        endpoint = "https://api.victorops.com/api-public/v1/alerts/" + uuid
        req = Request(endpoint, None, headers);
        res = urlopen(req);

        if res.status == 200:
            helper.log_info("Retrieved Alert")
            body = res.read()
            #helper.log_info(body)
            return json.loads(body)

    except HTTPError as e:
        #helper.log_error('Exception retrieving last alert: ' + str(e.code));
        ## RATE LIMITS
        #helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
        #time.sleep(t + 60 - time.perf_counter())
        helper.log_info("Rate Throttling - retry in 60 seconds")
        time.sleep(60)
        return getAlert(helper, headers, uuid)

def get_incidents(helper, headers):

    # Get web proxy configuration.
    proxyConfig = {}
    org_slug  = helper.get_arg('organization_id')
    try:
        proxy = voUtils.getWebProxyConfig(helper.context_meta['session_key']);
        #helper.log_info(proxy)

        if 'host' in proxy and proxy['host'] != '':
            helper.log_info('Using Web proxy for requests: ' + proxy['protocol'] + '://' + proxy['host'] + ':' + str(proxy['port']));
            proto = proxy['protocol'];
            proxyUrl = proto + '://' + proxy['host'] + ':' + proxy['port'] + '/';
            conf = {};

            # All calls to VictorOps API are https, setup proxy URL to reference
            # the proxy which could be http or https.
            conf['https'] = proxyUrl;
            conf['http'] = proxyUrl;
            helper.log_info('Proxy Configuration: ' + repr(conf));
            proxy_handler = ProxyHandler(conf);

            if 'user' in proxy and proxy['user'] != '' and 'pass' in proxy and proxy['pass'] != '':
                helper.log_info('Configuring proxy configuration to use authentication...');
                # Proxy https requests with auth.
                proxy_auth_handler = HTTPBasicAuthHandler();
                proxy_auth_handler.add_password(None, proxyUrl, proxy['user'], proxy['pass']);
                opener = build_opener(proxy_handler, proxy_auth_handler);
            else:
                # Auth not defined, proxy all https requests w/out auth.
                helper.log_info('Using http proxy w/out authentication...');
                opener = build_opener(proxy_handler);

            install_opener(opener);

        else:
            helper.log_info('Proxy IS NOT configured!');


    except Exception as e:
        helper.log_error('Exception retrieving webProxy config');
        helper.log_error(e);

    t = time.perf_counter()
    #helper.log_info("Time : {}".format(t))
    body = json.dumps({})
    endpoint = 'https://api.victorops.com/api-public/v1/incidents'
    req = Request(endpoint, None, headers);

    try:
        res = urlopen(req);

        # RATE LIMITS
        #while res.status == 403:
        #    # wait until minute has passed
        #    helper.log_info("Waiting {} seconds".format(t + 60 - time.perf_counter()))
        #    time.sleep(t + 60 - time.perf_counter())
        #    # reset timer to current time
        #    t = time.perf_counter()
        #    # retry
        #    res = urlopen(req);

        if res.status == 200:
            # IF SUCCESS, GET LAST ALERT RAW ALERT
            body = res.read()
            incidents = json.loads(body)
            #for i in incidents['incidents']:
            #    helper.log_info("processing incident")
            #    i['lastAlert'] = getAlert(helper, headers, i['lastAlertId'])
            for i in incidents['incidents']:
                i['org'] = org_slug
            return incidents
    
    except Exception as e:
        raise;


collection_in_progress = 0
def collect_events(helper, ew):
    global collection_in_progress
    helper.log_info("collect_events() entry ...")
    organization_id = helper.get_arg('organization_id')
    api_id = helper.get_arg('api_id')
    api_key = helper.get_arg('api_key')

    # Don't allow another collect_events start until current is finished
    if collection_in_progress == 1:
        helper.log_info("Attempt to start another collect_events aborted, prior start still in progress");
        return
    collection_in_progress = 1

    appVersion = voUtils.getAppVersion();
    splunkVersion = voUtils.getSplunkVersion()
    pythonVersion =  sys.version_info
    userAgent = "VictorOpsTA/" + appVersion + " Splunk/" + splunkVersion + " Python/" + str(pythonVersion)

    headers = {
        'Content-Type': 'application/json',
        'X-VO-Api-Id': api_id,
        'X-VO-Api-Key': api_key,
        'Accept': 'application/json',
        'User-Agent': userAgent
    }
    incidents = get_incidents(helper, headers)
    helper.log_info("Successfully Got Incidents - count="+str(len(incidents['incidents'])))
    for incident in incidents['incidents']:
        #helper.log_info("Processing Incident")
        check_point_key = "{}_{}_incidents".format(helper.get_input_stanza_names(), incident['incidentNumber'])
        md5 = get_check_point(helper, check_point_key)
        #helper.log_info(md5)
        #helper.log_info("JAM-HERE-1")
        #helper.log_info(incident)
        #incident['lastAlert']['raw'] = json.loads(incident['lastAlert']['raw'])
        #helper.log_info("json: " + json.dumps(incident, sort_keys=True))
        incident_json = json.dumps(incident, sort_keys=True)
        temp_incident_md5 = voUtils.md5_compat(incident_json)
        if temp_incident_md5 == md5:
            helper.log_info("Data about {} was ingested. So Skipping . . . ".format(incident['incidentNumber']))
            continue
        else:
            if temp_incident_md5 == None:
                helper.log_info("Fresh data index about {}".format(incident['incidentNumber']))
            else:
                helper.log_info("Something about {} has changed. Indexing the new event . . .".format(incident['incidentNumber']))

            # IMPORTANT: Splunk time picker filters on event timestamp (_time).
            # Older behavior expects "Last 24 hours" to mean incidents CREATED in last 24h,
            # so we stamp events using incident startTime (not lastAlertTime).
            #
            # Use UTC epoch seconds (avoid naive datetime being interpreted as local time).
            ts = incident.get("startTime") or incident.get("lastAlertTime")
            helper.log_info(ts)
            dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            event_time_epoch = calendar.timegm(dt.utctimetuple())
            # Prefer the legacy/json sourcetype so the shipped props.conf stanza
            # ([splunk:victorops:incidents:json]) applies consistently across Splunk versions.
            # In some Splunk versions the default sourcetype is the modular input name ("victorops_incidents"),
            # which causes props.conf not to match and can change time filtering behavior.
            st = helper.get_sourcetype()
            if not st or st == "victorops_incidents":
                st = "splunk:victorops:incidents:json"
            event = helper.new_event(
                source=helper.get_input_type(),
                time=event_time_epoch,
                index=helper.get_output_index(),
                sourcetype=st,
                data=json.dumps(incident),
            )
            ew.write_event(event)
            helper.save_check_point(check_point_key, temp_incident_md5)

    collection_in_progress = 0

    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_organization_id = helper.get_arg('organization_id')
    opt_api_id = helper.get_arg('api_id')
    opt_api_key = helper.get_arg('api_key')
    # In single instance mode, to get arguments of a particular input, use
    opt_organization_id = helper.get_arg('organization_id', stanza_name)
    opt_api_id = helper.get_arg('api_id', stanza_name)
    opt_api_key = helper.get_arg('api_key', stanza_name)

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
