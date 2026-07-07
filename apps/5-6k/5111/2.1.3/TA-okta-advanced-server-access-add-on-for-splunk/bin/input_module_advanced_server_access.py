
# encoding = utf-8

import os
import re
import sys
import time
import json
import logging
from datetime import datetime, timedelta

def _write_Results(helper, ew, metric, results):
    instance_address = _getSetting(helper, 'instance_address')
    
    log_metric = "metric=" + metric + " | message="
    helper.log_debug(log_metric + "_write_oktaResults Invoked")
    
    eventSourcetype = "OktaASA"
    eventSource = "Okta:ASA"
    
    for item in results:
        data = json.dumps(item)
        data = re.sub(r'[\s\r\n]+'," ", data)
        event = helper.new_event \
        (
            source=eventSource,
            index=helper.get_output_index(),
            sourcetype=eventSourcetype,
            host=instance_address,
            data=data
        )
        ew.write_event(event)

def _getSetting(helper, setting):
    opt_metric = "OktaASA1"
    log_metric = "metric=" + opt_metric + " | message="
    helper.log_debug(log_metric + "_getSetting Invoked")
    myDefaults = {
        'instance_address': "app.scaleft.com",
        'page_size': 100,
        'allow_proxy': False,
        'http_request_timeout': 90,
        'write_appUser': True,
        'write_groupUser': True,
        'bypass_verify_ssl_certs': False,
        'custom_ca_cert_bundle_path': False
    }

    # early fail if the setting we've been asked for isn't something we know about
    if setting not in myDefaults:
        helper.log_error(log_metric + "_getSetting has no way of finding values for: " + str(setting))
        return None
    else:
        helper.log_debug(log_metric + "_getSetting is looking for values for: " + str(setting))

    try:
        myVal = helper.get_global_setting(setting)
        helper.log_debug(log_metric + "_getSetting has a configured " + setting + " value of: " + str(myVal))
    except:
        myVal = myDefaults[setting]
        helper.log_debug(log_metric + "_getSetting handling the coded default for " + setting + " value of: " + str(myVal))

    #test for nonetype
    if myVal is None:
        myVal = myDefaults[setting]
        helper.log_debug(log_metric + "_getSetting using the coded default for " + setting + " value of: " + str(myVal))

    return myVal
    
def _expandDetails(helper,Audit,RelatedOs):
    helper.log_debug("_expandDetails called")

    #Audit and RelatedOs are both dicts
    for key, value in iter(Audit['details'].items()):
        if type(Audit['details'][key]) is not list:
            if value in RelatedOs:
                #helper.log_debug("Replace " + str(key) + " with related object ref " + str(value))
                Audit['details'][key] = RelatedOs[value]['object']
        else:
            for value in Audit['details'][key]:
                i=0
                if value in RelatedOs:
                    # in theory this works but i don't have data that proves it
                    #helper.log_debug("Replace " + str(key) + "item #" + str(i) + " with related object ref " + str(value) )
                    Audit['details'][key][i] = RelatedOs[value]['object']
                i = i+1
                
    helper.log_debug("_expandDetails complete")

def _asa_client(helper, url, headers, method, body, params):
    #Makes actual calls to Okta, handles http level errs
    opt_metric = "OktaASA1"
    log_metric = "metric=" + opt_metric + " | message="
    if url.startswith("https://"):
        helper.log_info(log_metric + "_okta_client Invoked with a secure url of: " + url)
    else:
        #this will clear out the url = error will bubble up in http client call - not worried about it
        helper.log_error(log_metric + "_okta_client Invoked with an INSecure url of: " + url + ". Aborting!")
        url = ""
    userAgent = "Splunk-ASA-AddOn/2.1"
    team_name = helper.get_arg('team_name')
    
    try:
        reqTimeout = float(_getSetting(helper, 'http_request_timeout'))
    except:
        helper.log_debug(log_metric + "_asa_client using backup coded timeout value")
        reqTimeout = float(90)

    allow_proxy = bool(_getSetting(helper, 'allow_proxy'))
    bypass_verify_ssl_certs = bool(_getSetting(helper, 'bypass_verify_ssl_certs'))
    custom_ca_cert_bundle_path = _getSetting(helper, 'custom_ca_cert_bundle_path')

    if bypass_verify_ssl_certs:
        sslVerify = False
    else:
        sslVerify = True
        
    helper.log_debug(log_metric + "_asa_client Invoked with sslVerify set to: " + str(sslVerify))

    #Requests uses the same verify param to use a custom bundle, if a custom bundle is defined verification is implied.
    if (custom_ca_cert_bundle_path):
        helper.log_debug(log_metric + "_asa_client Invoked with custom_ca_cert_bundle_path set to: " + str(custom_ca_cert_bundle_path))
        #if it is set, is the path valid?
        if os.path.exists(custom_ca_cert_bundle_path):
            #ok, override whatever bool param was set with this.
            helper.log_debug(log_metric + "_asa_client custom_ca_cert_bundle_path path is valid, overriding sslVerify")
            sslVerify = custom_ca_cert_bundle_path
        else:
            helper.log_debug(log_metric + "_asa_client custom_ca_cert_bundle_path path is NOT valid, ignoring")

    #add UserAgent header
    headers.update( { 'User-Agent': userAgent })
    
    if allow_proxy:
        helper.log_info("Use of the proxy has been enabled through explicit definition of allow_proxy")
        response = helper.send_http_request \
           (
               url, method, parameters=params,
               payload=body, headers=headers,
               cookies=None, verify=sslVerify, cert=None,
               timeout=reqTimeout
            )
    else:
        helper.log_debug("Use of a proxy has been explicitly disabled")
        response = helper.send_http_request \
           (
               url, method, parameters=params,
               payload=body, headers=headers,
               cookies=None, verify=sslVerify, cert=None,
               timeout=reqTimeout, use_proxy=False
            )

    # get the response headers
    r_headers = response.headers
    requestid = r_headers.pop('Request-Id','None')

    #try catch except
    try:
        results = response.json()
    except:
        sendBack = { 'results': {}, 'n_val': False }
        return sendBack
    
    if response.status_code == 429:
        helper.log_error(log_metric + "_asa_client returned an error Request-Id=" + requestid)
        _rateLimitEnforce(helper, r_headers, response.status_code)
        # If we hit a 429 send back the current url as the n_val, we will pick up from there next time.
        sendBack = { 'results': {}, 'n_val': url }
        return sendBack
    
    helper.log_debug(log_metric + "_asa_client returned response to our request rid=" + requestid)

    response.raise_for_status()

    count = str(len(results))
    helper.log_debug(log_metric + "_asa_client Returned: " + count + " records")
    
    if 'next' in response.links:
        n_val = response.links['next']['url']
        helper.log_debug(log_metric + "_asa_client sees another page at this URL: " + n_val )
    else:
        n_val = False
        
    sendBack = { 'results': results, 'n_val': n_val }
    return sendBack

def _getASABearer(helper):
    #get and return a bearer, do NOT store it
    
    asa_account = helper.get_arg('asa_account')
    cp_prefix = asa_account['name']
    myTimeStamp = int(time.time())
    
    helper.log_debug("getting a bearer token")
    team_name = helper.get_arg('team_name')
    asa_account_key = asa_account['username']
    asa_account_secret = asa_account['password']
    instance_address = _getSetting(helper,'instance_address')
    
    headers = { 'Content-Type': 'application/json',
                'accept': '*/*' }
                
    body = '{ "key_id": "' + asa_account_key + '", "key_secret": "' + asa_account_secret + '" }'
    url = "https://" + instance_address + "/v1/teams/" + team_name + "/service_token"
    method = "Post"
    
    response = _asa_client(helper, url, headers, method, body, None)
    results = response.pop('results', {})
    bearer_token = results['bearer_token']

    return bearer_token

def _getandWriteAudits(helper, ew, bearer_token):
    log_metric = "OktaASA1"
    helper.log_debug("_getandWriteAudits invoked with a bearer token")
    asa_account = helper.get_arg('asa_account')
    cp_prefix = asa_account['name']
    team_name = helper.get_arg('team_name')
    instance_address = _getSetting(helper,'instance_address')

    method = "Get"
    headers = { 'Authorization': 'Bearer ' + bearer_token,
                'Content-Type': 'application/json',
                'accept': 'application/json' }
    page_size = int(_getSetting(helper,'page_size'))
    params = {"count": page_size}
    body = None

    offset = helper.get_check_point((cp_prefix + "offset"))
    
    #Are we picking up where we left off, or is this a cold start (log_history)
    if offset is None:
        helper.log_debug(log_metric + "_getandWriteAudits no offset found, looks like a cold start. Fetching latest event and then up from there")
        params.update({"descending": True})
        #params.update({"count": 1})
        followNext = False
    else:
        helper.log_debug(log_metric + "_getandWriteAudits found a valid offset, picking up from here: " + str(offset))
        params.update({"offset": offset})
        followNext = True

    
    getPages = True
    r_count = 0
    url = "https://" + instance_address + "/v1/teams/" + team_name + "/auditsV2"
    while(getPages):
        response = _asa_client(helper, url, headers, method, body, params)
        #clear out params, if there is a next link anything we sent will be present, don't want to duplicate args like offset cause that would be bad.
        params = {}
        results = response.pop('results', {})
        n_val = str(response.pop('n_val', False))
        i_count = int(len(results['list']))
        r_count = r_count + i_count
        helper.log_debug(log_metric + "_getandWriteAudits returned: " + str(i_count) + " this pass and: " + str(r_count) + " results so far")
        helper.log_debug(log_metric + "_getandWriteAudits Iteration Count: " + str(i_count))
        if n_val != "False":
            helper.log_debug(log_metric + "_getandWriteAudits n_val is: " + n_val)
            url = n_val
        else:
            helper.log_debug(log_metric + "_getandWriteAudits there is no more links to retrieve n_val is: " + n_val)
            getPages=False

        #If there is actually stuff to stuff stuff it
        if i_count > 0:
            AuditList = results['list']
            RelatedOs = results['related_objects']
            for Audit in AuditList:
                #helper.log_debug("Processing Audit ID: " + Audit['id'])
                _expandDetails(helper,Audit, RelatedOs)
            
            #_write_oktaResults(helper, ew, opt_metric , apps)
            _write_Results(helper, ew, "OktaASA", AuditList)
            if not followNext:
                getPages=False
                indexPos = 0
            else:
                indexPos = -1
            helper.log_debug(log_metric + "_getandWriteAudits store the offset incase we are interrupted between pages: " + results['list'][indexPos]['id'])
            helper.save_check_point((cp_prefix + "offset"), results['list'][indexPos]['id'])

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    
    #start the clock
    myJobStartTime = int(time.time())
    #a bearer token is good for 60 minutes
    ValidSeconds = int(3600)
    #get a bearer token
    bearer_token = _getASABearer(helper)
    #Inner interval (how long to sleep between loops)
    sleepTime = int(60)
    
    #we have a bearer_token now - lets start up a long running loop
    myKeepLooping = True
    myLoopCount = int(0)
    while (myKeepLooping):
        myLoopCount = myLoopCount +1
        myLoopStartTime = int(time.time())
        if myLoopStartTime < (myJobStartTime + ValidSeconds):
            helper.log_debug("calling _getandWriteAudits, loopCount is: " + str(myLoopCount))
            #get and write the audits we find
            _getandWriteAudits(helper, ew, bearer_token)
            time.sleep(sleepTime)
        else:
            helper.log_debug("After " + str(myLoopCount) + " Loops our bearer_token has or will soon expire, exiting normally" )
            myKeepLooping = False
