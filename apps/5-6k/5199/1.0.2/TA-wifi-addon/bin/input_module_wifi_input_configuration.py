# encoding = utf-8
import os
import sys
import time
import datetime
import json
import requests
from requests import Request
import sys
import re
import splunk.version as ver

version = float(re.search("(\d+.\d+)", ver.__version__).group(1))

try:
    if version >= 6.4:
        from splunk.clilib.bundle_paths import make_splunkhome_path
    else:
        from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
except ImportError as e:
    sys.exit(3)


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
    helper.log_debug("In validate Input Func")
    # This example accesses the modular input variable
    # input_name = definition.parameters.get('input_name', None)
    # api_url = definition.parameters.get('api_url', None)
    # api_key = definition.parameters.get('api_key', None)
    # from_date = definition.parameters.get('from_date', None)
    # required_fields = definition.parameters.get('required_fields', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""
    
    helper.log_info("Started")
    helper.log_debug("In collect_events")
    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_api_url = helper.get_arg('api_url')
    opt_api_key = helper.get_arg('api_key')
    opt_from_date = helper.get_arg('from_date')
    opt_required_fields = helper.get_arg('required_fields')
    opt_interval = helper.get_arg('interval')
    helper.log_debug("API URL:"+opt_api_url)
    helper.log_debug("API KEY:"+opt_api_key)
    helper.log_debug("from Date:"+opt_from_date)
    helper.log_debug(opt_interval)
    helper.log_debug(opt_required_fields)

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()


    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(loglevel)


    endpoint = opt_api_url+"?query=%7BdeviceList(page%3AGET_PAGE_NUMBER%2CpageSize%3A300%2CfromDate%3A%22FROM_DATE%22%2CsortBy%3A%22macAddr%22)%7B%0A%20%20page%0A%20%20pageCount%0A%20%20devices%7B%0A%20%20%20%20macAddr%0A%20%20%20%20ipAddress%0A%20%20%20%20hostname%0A%20%20%20%20userName%0A%20%20%20%20isWireless%0A%20%20%20%20apName%0A%20%20%20%20apMacAddr%0A%20%20%20%20apName%0A%20%20%20%20apDwellTimeMs%0A%20%20%20%20accessPointHistory%7B%0A%20%20%20%20%20%20apMacAddr%0A%20%20%20%20%20%20lastSeen%0A%20%20%20%20%7D%0A%20%20%20%20%0A%20%20%7D%0A%7D%7D%0A&variables=null"

    current_page=1
    log_path = make_splunkhome_path(["etc", "apps","TA-wifi-addon","bin","fromdate.txt"])
    fromdate=""
    if(os.path.isfile(log_path)):
        f = open(log_path, "r")
        fromdate=f.readline()
        fromdate=fromdate.replace("\n", "")
        helper.log_debug(fromdate)

    if fromdate == None or fromdate=="":
        fromdate=opt_from_date
    helper.log_debug(fromdate)
    fromdate=fromdate.replace(":","%3A")
    endpoint = endpoint.replace("FROM_DATE",fromdate)
    current_endpoint=endpoint.replace("GET_PAGE_NUMBER",str(current_page))
    json_payload=request(current_endpoint,opt_api_key,helper)
    current_page,total_page = modify_json(json_payload,opt_required_fields,helper,ew)
    helper.log_debug(current_page)
    helper.log_debug(total_page)
    try:
        f = open(log_path, "w")
        f.write(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z')
        f.close()
    except Exception as e:
        helper.log_error(e)
    helper.log_debug(total_page)
    while(current_page<total_page):
        current_page=current_page+1
        helper.log_debug(current_page)
        
        current_endpoint=endpoint.replace("GET_PAGE_NUMBER",str(current_page))
        json_payload=request(current_endpoint,opt_api_key,helper)
        current_page,total_page = modify_json(json_payload,opt_required_fields,helper,ew)

    helper.log_info("Finished")
    
    
def request(endpoint,apikey,helper):
    """
    Request WiFi Data 
    """
    headers = {
        'content-type': "application/json",
        'api-token': apikey,
    }
    helper.log_debug(endpoint)
    req = Request("POST", endpoint, headers=headers)
    prepped_req = requests.session().prepare_request(req)
    response = requests.session().send(prepped_req)
    helper.log_debug(response.text)
    if response.status_code != 200:
        helper.log_warn("status code :"+str(response.status_code))
    return response.text


def modify_json(json_payload,list_of_fields,helper,ew):
    helper.log_debug("In modify_json")
    json_payload=json.loads(json_payload)
    current_page=json_payload["data"]["deviceList"]["page"]
    total_page=json_payload["data"]["deviceList"]["pageCount"]
    devices=json_payload["data"]["deviceList"]["devices"]
    current=0
    while current<len(devices):
        recur("",devices[current],list_of_fields,helper,ew)
        current=current+1 
    return current_page,total_page
    
    
def recur(str1,json_object,list_of_fields,helper,ew):
    if len(list_of_fields) == 0:
        data=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]+str1
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
        ew.write_event(event)
        return(0)
    field=list_of_fields[0]
    if "." in field:
        parent=field.split(".")[0]
        child=field.split(".")[1]
        parent_json=json_object.get(parent)
        if parent_json != None:
            if type(parent_json) is list:
                for i in parent_json:
                    if i.get(child)!= None:
                        temp=""
                        temp=str1+","+parent+"_"+child+"=\""+str(i.get(child))+"\""
                        recur(temp,json_object,list_of_fields[1:],helper,ew)
                    else:
                        temp=""
                        temp=str1+","+parent+"_"+child+"=\"\""
                        recur(temp,json_object,list_of_fields[1:],helper,ew)
        else:
            temp=""
            temp=str1+","+parent+"_"+child+"=\"\""
            recur(temp,json_object,list_of_fields[1:],helper,ew)
    else:
        if json_object.get(field)!= None:
            temp=""
            temp=str1+","+field+"=\""+str(json_object.get(field))+"\""
            recur(temp,json_object,list_of_fields[1:],helper,ew)
        else:
            temp=""
            temp=str1+","+field+"=\"\""
            recur(temp,json_object,list_of_fields[1:],helper,ew)

