
# encoding = utf-8

import os
import sys
import time
import datetime
from datetime import timedelta
import json

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
    #fidelisip = definition.parameters.get('fidelisip', None)
    #username = definition.parameters.get('username', None)
    #password = definition.parameters.get('password', None)
    
    
    
    pass

def collect_events(helper, ew):
    
    
    starterDate = "1970-01-01T00:00:00.000Z"
    nvdbBaseURL = "https://cve.mitre.org/cgi-bin/cvename.cgi?name="
    
    fidelisip = helper.get_arg('fidelis_ip_address')
    username = helper.get_arg('username')
    password = helper.get_arg('password')
    #sourceType = helper.get_arg('source_type')
    sourceType = "FidelisEndpointAlerts"
    ignoreCVE = helper.get_arg('ignore_cve_alerts')
    enrichData = helper.get_arg('enrich_alert_data')
    
    stateName = helper.get_check_point("stateName")
    
    #####################################################
    #Check our stateName and start date
    #####################################################
    if not stateName:
        helper.log_info("First time run, using a marker name of \"start_date_{0}\" for future calls".format(stateName))
        now = datetime.datetime.now()
        stateName = now.strftime("%Y%m%d%H%M")
        helper.save_check_point("stateName", stateName)
        stateName = helper.get_check_point("stateName")
    
    startDate = helper.get_check_point("start_date_{0}".format(stateName))
    
    if not startDate:
        helper.save_check_point("start_date_{0}".format(stateName), starterDate)
        startDate = helper.get_check_point("start_date_{0}".format(stateName))
    
    
    #####################################################
    #Option for testing in script editing ONLY
    #####################################################
    #helper.delete_check_point("start_date_{0}".format(stateName))
    #helper.delete_check_point("stateName")
    #exit(0)
    #####################################################
    
   
    
    ##########################################################
    #Get the authentication token
    ##########################################################
    authURL = "https://{0}/endpoint/api/authenticate?username={1}&password={2}".format(fidelisip, username, password)
    helper.log_debug("Using \"{0}\" for authentication URL".format(authURL))
    
    r = helper.send_http_request(authURL, "GET", parameters=None, payload=None, headers=None, verify=False)
    if type(r.content) == bytes:
        helper.log_debug("Authentication response is UTF-8 encoded")
        rData = json.loads(r.content.decode("utf-8"))
    else:
        helper.log_debug("Authentication response is not UTF-8 encoded")
        rData = json.loads(r.content)
    if not rData["success"]:
        helper.log_error("Could not obtain authorisation token")
        exit(-1)
    helper.log_info("Successfully connected to {0}".format(fidelisip))
    authToken = rData["data"]["token"]
    headers = {"Content-Type": "application/json;charset=UTF-8", "Authorization": "bearer {0}".format(authToken)}
    ##########################################################
    
    
    ##########################################################
    #Get the product info
    ##########################################################
    productInfoURL = "https://{0}/endpoint/api/product-info".format(fidelisip)
    helper.log_debug("Using \"{0}\" for product info URL".format(productInfoURL))
    infoRaw = helper.send_http_request(productInfoURL, "GET", parameters=None, payload=None, headers=headers, verify=False)
    info = infoRaw.json()
    
    if not info:
        helper.log_error("Could not obtain version number")
        exit(-1)
    vendor_product = "Fidelis Endpoint {0}".format(info["data"]["version"])
    fidelisVersion = (info["data"]["version"]).split(".")
    helper.log_debug("Found Fidelis Endpoint version {0}".format(fidelisVersion))
    ##########################################################
    
    
    #Create an alert array
    alerts = []

    
    ##########################################################
    #Fidelis Endpoint 9.2.1 and above
    ##########################################################
    if fidelisVersion[0] >= 9 and fidelisVersion[1] >= 2 and fidelisVersion[2] >= 1:
        urlStartDate = "{0}.999Z".format(startDate.split(".")[0])
        #now = datetime.datetime.now()
        #urlEndDate = now.strftime("%Y-%")
        test = "2019-04-18T00:00:00.000Z"
        url = "https://{0}/endpoint/api/alerts/getalerts?startDate={1}&sort=createDate+Ascending".format(fidelisip, urlStartDate)
        r = helper.send_http_request(url, "GET", parameters=None, payload=None, headers=headers, verify=False)
        alerts = r.json()
        helper.log_debug("Found {0} alerts".format(alerts["data"]["totalCount"]))
    
    ##########################################################
    
    
    
    
    ##########################################################
    #Parse all alerts
    ##########################################################
    #Output our events
    if alerts and alerts["data"]["totalCount"] > 0:
        for alert in alerts["data"]["entities"]:
            
            #Shorten any lengthy descriptions
            if len(alert["description"]) > 3000:
                alert["description"] = alert["description"][:3000] + '..'
            
            #If we are ignoring CVE alerts, then ignore them
            if ignoreCVE and "Installed Software CVE" in alert["source"]:
                continue
            
            #If we have a CVE type alert then populate some CVE / software related fields
            if alert["sourceType"] == 19 and alert["intelSource"] is not None:
                alert["software_cve"] = alert["intelSource"]
                if "\n" in alert["description"]:
                    alert["software_title"] = alert["description"].split("\n")[0]
                alert["software_url"] = "{0}{1}".format(nvdbBaseURL, alert["software_cve"])
                
            #########################
            #Enrich Data
            #########################
            #If we are enriching data, then perform the event lookup
            if enrichData and "Installed Software CVE" not in alert["source"]:
                
                #Get the host agent ID
                #Setup the endpoint URL lookup
                #endpointSearchCriteria = {"searchFields":[{"fieldName":"HostName","values":[{"value":alert["target"],"operator":7}]}]}
                endpointSearchCriteria = {"searchAny":[{"value":alert["target"],"operator":7}]}
                endpointURL = "https://{0}/Endpoint/api/endpoints/v2/0/100/hostname%20Ascending?accessType=3&search={1}".format(fidelisip, json.dumps(endpointSearchCriteria))
                r = helper.send_http_request(endpointURL, "GET", headers=headers, verify=False)
                rData = r.json()
                endpoints = rData["data"]["entities"]
                thisEndpoint = {}
                for endpoint in endpoints:
                    if alert["alertTargetId"].lower() == endpoint["id"].lower():
                        thisEndpoint = endpoint
                        break
                if not thisEndpoint:
                    continue
                
                #Populate some Endpoint fields
                endpointFields = {"endpoint_agentTag":"agentTag", "endpoint_version":"agentVersion", "endpoint_avEnabled":"aV_enabled","endpoint_aREnabled":"aR_enabled", "endpoint_avSignature":"avSigVersion","endpoint_advMalwareVersion": "advMalwareVersion","endpoint_ipAddress":"ipAddress","endpoint_MACAddress":"macAddress", "endpoint_OS":"os","endpoint_agentId":"agentId","endpoint_groups":"groups"}
                for key,val in endpointFields.items():
                    try:
                        alert[key] = endpoint[val]
                    except:
                        pass
                
                #Setup the events URL
                eventURL = "https://{0}/endpoint/api/v2/events?pageSize=10".format(fidelisip)
                
                #Detect the long date type
                if "." in alert["eventTime"]:
                    eventStart = datetime.datetime.strptime(alert["eventTime"], '%Y-%m-%dT%H:%M:%S.%fZ') - timedelta(seconds=1)
                    eventEnd = datetime.datetime.strptime(alert["eventTime"], '%Y-%m-%dT%H:%M:%S.%fZ') + timedelta(seconds=1)
                    eventStart = datetime.datetime.strftime(eventStart, "%Y-%m-%dT%H:%M:%SZ")
                    eventEnd = datetime.datetime.strftime(eventEnd, "%Y-%m-%dT%H:%M:%SZ")
                
                #Detect the short date type
                else:
                    eventStart = datetime.datetime.strptime(alert["eventTime"], '%Y-%m-%dT%H:%M:%SZ') - timedelta(seconds=1)
                    eventEnd = datetime.datetime.strptime(alert["eventTime"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(seconds=1)
                    eventStart = datetime.datetime.strftime(eventStart, "%Y-%m-%dT%H:%M:%SZ")
                    eventEnd = datetime.datetime.strftime(eventEnd, "%Y-%m-%dT%H:%M:%SZ")
                
                searchCriteria = {}
                searchCriteria["resultFields"] = []
                searchCriteria["dateRange"] = {"start": eventStart, "end": eventEnd}
                searchCriteria["criteria"] = {}
                searchCriteria["criteria"]["criteria"] = []
                
                #Populate the endpoint ID in the search
                searchCriteria["criteria"]["criteria"].append({"field": "endpointName", "operator": "cn", "value": alert["target"].lower()})
                
                et = "event"
                processFields = {}
                #If this is process based
                if alert["eventType"] == 0:
                    searchCriteria["criteria"]["entityType"] = "process"
                    et = "event_process"
                    processFields = {"entropy": "entropy","certificateIssuerName": "certificateIssuerName","certificatePublisher": "certificatePublisher","certificateSubjectName": "certificateSubjectName","fileExtension": "fileExtension","fileVersion": "fileVersion","hashMD5": "hash","hashSHA1": "hashSHA1","hashSHA256": "hashSHA256","name": "name","parameters": "parameters","parentCertificateIssuerName": "parentCertificateIssuerName","parentCertificatePublisher": "parentCertificatePublisher","parentCertificateSubjectName": "parentCertificateSubjectName","parentHashMD5": "parentHash","parentHashSHA1": "parentHashSHA1","parentName": "parentName","parentPath": "parentPath","path": "path","pid": "pid","ppid": "ppid","remotePID": "remotePID","remoteTID": "remoteTID","size": "size"}
    
                #If this is file based
                if alert["eventType"] > 3  and alert["eventType"] < 9:
                    searchCriteria["criteria"]["entityType"] = "file"
                    et = "event_file"
                    processFields = {"entropy":"entropy","fileExtension":"fileExtension","fileVersion":"fileVersion","hashMD5":"hash","hashSHA1":"hashSHA1","hashSHA256":"hashSHA256","name":"name","parameters":"parameters","parentCertificateIssuerName":"parentCertificateIssuerName","parentCertificatePublisher":"parentCertificatePublisher","parentCertificateSubjectName":"parentCertificateSubjectName","parentHashMD5":"parentHash","parentHashSHA1":"parentHashSHA1","parentName":"parentName","parentPath":"parentPath","path":"path","ppid":"ppid","remotePID":"remotePID","remoteTID": "remoteTID","size":"size"}
    
                #If this is network based
                if alert["eventType"] == 3:
                    searchCriteria["criteria"]["entityType"] = "network"
                    et = "event_network"
                    processFields = {"entropy":"entropy","fileExtension":"fileExtension","fileVersion":"fileVersion","localIP":"localIP","localPort":"localPort","networkDirection":"networkDirection","parameters":"parameters","parentCertificateIssuerName":"parentCertificateIssuerName","parentCertificatePublisher":"parentCertificatePublisher","parentCertificateSubjectName":"parentCertificateSubjectName","parentHashMD5":"parentHash","parentHashSHA1":"parentHashSHA1","parentName":"parentName","parentPath":"parentPath","ppid":"ppid","protocol":"protocol","remoteIP":"remoteIP","remotePID":"remotePID","remotePort":"remotePort","remoteTID": "remoteTID","size":"size"}

                #If this is DNS based
                if alert["eventType"] == 17:
                    searchCriteria["criteria"]["entityType"] = "dns"
                    et = "event_dns"
                    processFields = {"dnsAnswer": "dnsAnswer","dnsQuestion": "dnsQuestion","entropy": "entropy","fileExtension": "fileExtension","fileVersion": "fileVersion","localIP": "localIP","localPort": "localPort","networkDirection": "networkDirection","parameters": "parameters","parentCertificateIssuerName": "parentCertificateIssuerName","parentCertificatePublisher": "parentCertificatePublisher","parentCertificateSubjectName": "parentCertificateSubjectName","parentHashMD5": "parentHash","parentHashSHA1": "parentHashSHA1","parentName": "parentName","parentPath": "parentPath","ppid": "ppid","remoteIP": "remoteIP","remotePID": "remotePID","remotePort": "remotePort","remoteTID": "remoteTID","size": "size"}
                    
    
                #If this is registry based
                if alert["eventType"] > 9 and alert["eventType"] < 13:
                    searchCriteria["criteria"]["entityType"] = "registry"
                    et = "event_registry"
                    processFields = {"entropy":"entropy","fileExtension":"fileExtension","fileVersion":"fileVersion","hive":"hive","name":"name","data":"value","parameters":"parameters","parentCertificateIssuerName":"parentCertificateIssuerName","parentCertificatePublisher":"parentCertificatePublisher","parentCertificateSubjectName":"parentCertificateSubjectName","parentHashMD5":"parentHash","parentHashSHA1":"parentHashSHA1","parentName":"parentName","parentPath":"parentPath","key":"path","ppid":"ppid","remotePID":"remotePID","remoteTID": "remoteTID","size":"size"}
    
                #If this is USB based
                if alert["eventType"] > 13 and alert["eventType"] < 17:
                    searchCriteria["criteria"]["entityType"] = "usb"
                    et = "event_usb"
                    processFields = {"entropy": "entropy","media": "media","model": "model","path": "path","remotePID": "remotePID","remoteTID": "remoteTID","usb": "usb"}
    
                #If this is WEV based
                if alert["eventType"] == 13:
                    searchCriteria["criteria"]["entityType"] = "windowsevent"
                    et = "event_wev"
                    processFields = {"category": "category","entropy": "entropy","message": "message","name": "name","remotePID": "remotePID","remoteTID": "remoteTID","source": "source","id":"winEventId","SID":"winSID"}
    
                #If this is Malware based
                if alert["eventType"] > 17 and alert["eventType"] < 30:
                    searchCriteria["criteria"]["entityType"] = "antiMalware"
                    et = "event_am"
                    processFields = {"entropy": "entropy","fileExtension": "fileExtension","message": "message","name": "name","parameters": "parameters","parentHashMD5": "parentHash","parentHashSHA1": "parentHashSHA1","parentName": "parentName","parentPath": "parentPath","path": "path","ppid": "ppid","remotePID": "remotePID","remoteTID": "remoteTID","scanType":"scanType","size": "size"}
                
                r = helper.send_http_request(eventURL, "POST", parameters=None, payload=json.dumps(searchCriteria), headers=headers, verify=False)
                if type(r.content) == bytes:
                    rData = json.loads(r.content.decode("UTF-8"))
                else:
                    rData = json.loads(r.content)
                
                #Find our event in the events (if it exists)
                events = []
                thisEvent = {}
                try:
                    events = rData["data"]["events"]
                except:
                    pass
                if events:
                    for event in events:
                        if alert["eventIndex"] == event["eventIndex"]:
                            thisEvent = event
                            break
                
                ######################################
                #Fill in the event information
                ######################################
                if thisEvent:
                    
                    #For each key value pair in the relative processFields, enter them into the alert data
                    for key,val in processFields.items():
                        try:
                            alert["{0}_{1}".format(et,key)] = thisEvent["{0}".format(val)]
                        except:
                            pass
                    try:
                        alert["user"] = thisEvent["user"]
                    except:
                        pass


            
                
            #########################
            #Modify source data
            #########################
            alert["alertSource"] = alert["source"]
            del alert["source"]
            
                            
                    
            
            #########################
            #Delete irrelevant data
            #########################
            del alert["eventId"]
            del alert["eventIndex"]
            del alert["parentEventId"]
            del alert["reportId"]
            del alert["respondedDate"]
            del alert["status"]
            del alert["viewed"]
            
            ##########################
            #Add some standard fields
            ##########################
            alert["vendor_product"] = vendor_product
            
            #########################
            #Log the alert
            #########################
            event = helper.new_event(json.dumps(alert), time=datetime.datetime.now(), host=fidelisip, index=None, source=None, sourcetype=sourceType, done=True, unbroken=True)
            ew.write_event(event)
            helper.log_debug("Creating event from Fidelis Endpoint Alert with ID \"{0}\"".format(alert["id"]))
            
            
            #Create a state marker for next round
            state = alert["createDate"]
            statesplit = state.split("Z")
            statesplitsplit = statesplit[0].split(".")
            tlen = len(statesplitsplit[1])
            statesplitsplit[1] = "{0}".format(str(int(statesplitsplit[1]) + 1))
            statesplitsplit[1] = statesplitsplit[1].zfill(tlen)
            statesplit = "."
            statesplit = statesplit.join(statesplitsplit)
            state = "{0}Z".format(statesplit)
            helper.save_check_point("start_date_{0}".format(stateName), state)
            helper.log_debug("Saving state with date of \"{0}\"".format(state))
            
    
    
    
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_fidelisip = helper.get_arg('fidelisip')
    opt_username = helper.get_arg('username')
    opt_password = helper.get_arg('password')
    # In single instance mode, to get arguments of a particular input, use
    opt_fidelisip = helper.get_arg('fidelisip', stanza_name)
    opt_username = helper.get_arg('username', stanza_name)
    opt_password = helper.get_arg('password', stanza_name)

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
    global_fidelisip = helper.get_global_setting("fidelisip")

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
