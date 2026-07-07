
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import re
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

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # cofense_triage_url_host = definition.parameters.get('cofense_triage_url_host', None)
    # cofense_triage_sourcetype = definition.parameters.get('cofense_triage_sourcetype', None)
    pass

def extract_id(json):
    try:
        return int(json['id'])
    except KeyError:
        return 0
    pass

def collect_events(helper, ew):
    global_account = helper.get_arg('global_account')
    username = global_account['username']
    token = global_account['password']

    #arg_endpoint = helper.get_arg('cofense_triage_api_endpoint')
    arg_endpoint = 'processed_reports'
    arg_sourcetype = helper.get_sourcetype()
    global_url_hosts = helper.get_arg('cofense_triage_url_host')
    arg_reingest = helper.get_arg('re_ingest')
    arg_end_date = helper.get_arg('end_time')
    api_url_processed_reports = global_url_hosts+'/api/public/v1/'+arg_endpoint
    helper.log_debug('Url for fetching reports: '+api_url_processed_reports)
    headers = {
        'Authorization': 'Token token=' + username + ':' + token
    }
    helper.log_debug('Headers passed in: '+json.dumps(headers))
    
    input_type = helper.get_input_type()
    
    regex = r"https:\/\/([\w\.]+)\.[\w]+\.com" 
    
    test_str = global_url_hosts

    matches = re.finditer(regex, test_str, re.MULTILINE)
    
    for matchNum, match in enumerate(matches, start=1):
         for groupNum in range(0, len(match.groups())):
             groupNum = groupNum +1 
             group = match.group(groupNum)
             collection = group.replace(".", "_")
             base_cp = collection
             
    check_point_value = collection+"_"+arg_endpoint
    
    if arg_reingest is True:
        helper.delete_check_point(check_point_value)
    
    checkpoint = helper.get_check_point(check_point_value)
    if checkpoint is None:
        checkpoint = 0
        arg_start_date = helper.get_arg('start_time')
    else:
        interval = int(helper.get_arg("interval")) + 1
        new_start_date = datetime.datetime.now() - datetime.timedelta(seconds=interval)
        arg_start_date = new_start_date.strftime("%Y-%m-%d %H:%M:%S")
    
    if arg_end_date is None:
        new_end_date = datetime.datetime.now()
        arg_end_date = new_end_date.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        reports = []
        api_call = api_url_processed_reports
        parameters = {'page': 1,
                      'per_page': 50,
                      'start_date': arg_start_date,
                      'end_date': arg_end_date}
        last_link = False
        
        helper.log_debug('Parameters passed in '+json.dumps(parameters))
        
        if not helper.get_proxy():
            use_proxy = False
        else:
            use_proxy = True
        
        while not last_link:
            reports_pull = helper.send_http_request(api_call, "GET", verify=False, headers=headers, parameters=parameters, use_proxy=use_proxy)
            if 'Link' in reports_pull.headers:
                if re.search('rel="last"', reports_pull.headers['Link']) is None:
                    last_link = True
            else:
                last_link = True
            parameters['page'] += 1
            if reports_pull.headers['Status'] == '429 Too Many Requests':
                print("Sleeping due to API Limit")
                time.sleep(200)
                reports_pull = helper.send_http_request(api_call, "GET", verify=False, headers=headers, parameters=parameters, use_proxy=use_proxy)
            reports_results = json.loads(reports_pull.content)
            for each_report in reports_results:
                reports.append(each_report)
                # print(each_report)
    except:  # Python 2
        helper.log_error('Unable to connect to '+api_call)
        exit(1)
        
    reports.sort(key=extract_id)
    
    reports_length = {"Reports" : len(reports)}
    
    if not len(reports):
        exit(0)
    
    helper.log_debug('Number of reports to be processed for '+ arg_endpoint + json.dumps(reports_length))

    for each_json in reports:
        if each_json['id'] > checkpoint:
            event_time = each_json['created_at']
            event_time_epoch = datetime.datetime.strptime(event_time, '%Y-%m-%dT%H:%M:%S.%fZ')
    
            event = helper.new_event(source=input_type, host=global_url_hosts, time=event_time_epoch.time(),
                                 index=helper.get_output_index('main'), sourcetype=arg_sourcetype,
                                 data=json.dumps(each_json))
            ew.write_event(event)
        
            helper.delete_check_point(check_point_value)    
            helper.save_check_point(check_point_value,each_json['id'])
        else:
            continue
    pass

        