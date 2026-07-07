
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import re
import requests
import time

'''
    Calls cmd=stats on the /accessv2 Kemp API Endpoint
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # kemp_server = definition.parameters.get('kemp_server', None)
    # api_key = definition.parameters.get('api_key', None)
    pass

def collect_events(helper, ew):
    
    kemp_server = helper.get_arg('kemp_server')
    api_key = helper.get_arg('api_key')
    # set the API endpoint and request body
    url = 'https://'+kemp_server+'/accessv2'
    data = "{\"apikey\":\""+api_key+"\",\n\"cmd\":\"stats\"}"
    #Set the source field
    sourceStr = helper.get_input_type()+"://"+helper.get_input_stanza_names()

    # make a POST request to the API endpoint with the specified request body
    helper.log_info("Making Stats API Call to: "+kemp_server)
    epoch=time.time()
    response = requests.post(url, data=data)
    helper.log_info("API Call Responded with: "+str(response.status_code))
    
    #Extract the Timestamp section from the response:
    ''' removed as the timestamp returned in 15 mins behind, using time of API call as set above
    tstamp_regex = re.compile(r"(\"Timestamp\":\s*\{.*?\})\,",re.MULTILINE | re.DOTALL)
    tstamp_stanza = "{"+(tstamp_regex.search(response.text).group(1))+"}"
    helper.log_debug(tstamp_stanza)
    tstamp_json=json.loads(tstamp_stanza)
    epoch = tstamp_json["Timestamp"]["Sec"]
    helper.log_info("Timestamp extracted: " + str(epoch))
    '''
    
    #Extract the CPU section from the response:
    cpu_regex = re.compile(r"\s+(\"CPU\":\s*\{.*?\})\,\s+\"Memory\"",re.MULTILINE | re.DOTALL)
    cpu_event_body = "{"+cpu_regex.search(response.text).group(1)+"}"
    cpu_event_json=json.dumps(json.loads(cpu_event_body))
    #Write the CPU event:
    cpu_event = helper.new_event(time=epoch,host=kemp_server,source=sourceStr, index=helper.get_output_index(), sourcetype=helper.get_sourcetype()+":cpu", data=cpu_event_json)
    ew.write_event(cpu_event)
    
    #Extract the Memory section from the response:
    memory_regex = re.compile(r"\s+(\"Memory\":\s*\{.*?\}),\s+\"Network\"",re.MULTILINE | re.DOTALL)
    memory_event_body = "{"+memory_regex.search(response.text).group(1)+"}"
    memory_event_json=json.dumps(json.loads(memory_event_body))
    #Write the Memory event:
    memory_event = helper.new_event(time=epoch,host=kemp_server,source=sourceStr, index=helper.get_output_index(), sourcetype=helper.get_sourcetype()+":memory", data=memory_event_json)
    ew.write_event(memory_event)
    
     #Extract the Network section from the response:
    network_regex = re.compile(r"\s+(\"Network\":\s*\{.*?\}),\s+\"DiskUsage\"",re.MULTILINE | re.DOTALL)
    network_event_body = "{"+network_regex.search(response.text).group(1)+"}"
    network_event_json=json.dumps(json.loads(network_event_body))
    #Write the Network event:
    network_event = helper.new_event(time=epoch,host=kemp_server,source=sourceStr, index=helper.get_output_index(), sourcetype=helper.get_sourcetype()+":network", data=network_event_json)
    ew.write_event(network_event)
    
    #Extract the Disk Usage section from the response:
    diskusage_regex = re.compile(r"\s+(\"DiskUsage\":\s*\{.*?\}),\s+\"ClientLimits\"",re.MULTILINE | re.DOTALL)
    diskusage_event_body = "{"+diskusage_regex.search(response.text).group(1)+"}"
    diskusage_event_json=json.dumps(json.loads(diskusage_event_body))
    #Write the Disk Usage event:
    diskusage_event = helper.new_event(time=epoch,host=kemp_server,source=sourceStr, index=helper.get_output_index(), sourcetype=helper.get_sourcetype()+":diskusage", data=diskusage_event_json)
    ew.write_event(diskusage_event)

    #Extract the Client Limits section from the response:
    clientlimits_regex = re.compile(r"\s+(\"ClientLimits\":\s*\{.*?\}),\s+\"CountryCounts\"",re.MULTILINE | re.DOTALL)
    clientlimits_event_body = "{"+clientlimits_regex.search(response.text).group(1)+"}"
    clientlimits_event_json=json.dumps(json.loads(clientlimits_event_body))
    #Write the Client Limits event:
    clientlimits_event = helper.new_event(time=epoch,host=kemp_server,source=sourceStr, index=helper.get_output_index(), sourcetype=helper.get_sourcetype()+":clientlimits", data=clientlimits_event_json)
    ew.write_event(clientlimits_event)
    
    #Extract the Country Counts section from the response - note try/except handling here as this stanza is problematic:
    try:
        countrycounts_regex = re.compile(r"\s+(\"CountryCounts\":\s*\{.*?\}),\s+\"VStotals\"",re.MULTILINE | re.DOTALL)
        countrycounts_event_body = "{"+countrycounts_regex.search(response.text).group(1)+"}"
        countrycounts_event_json=json.dumps(json.loads(countrycounts_event_body))
    except json.decoder.JSONDecodeError:
        helper.log_error("Error processing Country Counts stanza")
    else:
        #all good - write the event
        countrycounts_event = helper.new_event(time=epoch,host=kemp_server,source=sourceStr, index=helper.get_output_index(), sourcetype=helper.get_sourcetype()+":countrycounts", data=countrycounts_event_json)
        ew.write_event(countrycounts_event)
    
    #Extract the VSTotals section from the response:
    vstotals_regex = re.compile(r"\s+(\"VStotals\":\s*\{.*?\}),\s+\"Vs\"",re.MULTILINE | re.DOTALL)
    vstotals_event_body = "{"+vstotals_regex.search(response.text).group(1)+"}"
    vstotals_event_json=json.dumps(json.loads(vstotals_event_body))
    vstotals_event = helper.new_event(time=epoch,host=kemp_server,source=sourceStr, index=helper.get_output_index(), sourcetype=helper.get_sourcetype()+":vstotals", data=vstotals_event_json)
    ew.write_event(vstotals_event)
    
    #Extract the Vs section from the response:
    vs_regex = re.compile(r"\s+(\"Vs\":\s*\[.*?\])\s*,\s*\"TPS\"",re.MULTILINE | re.DOTALL)
    #print(vs_regex.search(response.text).group(1))
    virtualServices = json.loads("{"+vs_regex.search(response.text).group(1)+"}")
    #print(type(virtualServices))
    helper.log_info("Number of Virtual Services found: " + str(len(virtualServices["Vs"])))
    for vs in virtualServices["Vs"]:
        vs_event_json_str = json.dumps(vs)
        vs_event = helper.new_event(time=epoch,host=kemp_server,source=sourceStr, index=helper.get_output_index(), sourcetype=helper.get_sourcetype()+":vs", data=vs_event_json_str)
        ew.write_event(vs_event)
        
        
    #Extract the Rs section from the response:
    rs_regex = re.compile(r"\s+(\"Rs\":\s*\[.*?\])\s*,\s*\"Timestamp\"",re.MULTILINE | re.DOTALL)
    realServers = json.loads("{"+rs_regex.search(response.text).group(1)+"}")
    helper.log_info("Number of Real Servers found: " + str(len(realServers["Rs"])))
    for rs in realServers["Rs"]:
        rs_event_json_str = json.dumps(rs)
        helper.log_debug(rs_event_json_str)
        rs_event = helper.new_event(time=epoch,host=kemp_server,source=sourceStr, index=helper.get_output_index(), sourcetype=helper.get_sourcetype()+":rs", data=rs_event_json_str)
        ew.write_event(rs_event)
        
    
    