
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
    arg_endpoint = 'reporters'
    arg_sourcetype = helper.get_sourcetype()
    global_url_hosts = helper.get_arg('cofense_triage_url_host')
    arg_reingest = helper.get_arg('re_ingest')
    api_url_processed_reports = global_url_hosts + '/api/public/v1/' + arg_endpoint
    helper.log_debug('Url for fetching reports: '+api_url_processed_reports)
    headers = {
        'Authorization': 'Token token=' + username + ':' + token
    }
    helper.log_debug('Headers passed in: '+json.dumps(headers))
    
    if not helper.get_proxy():
            use_proxy = False
    else:
        use_proxy = True
    
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
    
    try:
        results_json = []
        api_call = api_url_processed_reports
        parameters = {'page': 1,
                      'per_page': 50}
        last_link = False
        
        helper.log_debug('Parameters passed in '+json.dumps(parameters))
        
        while not last_link:
            results = helper.send_http_request(
                api_call, 
                "GET", 
                verify=False, 
                headers=headers, 
                parameters=parameters, 
                use_proxy=use_proxy
            )
            if 'Link' in results.headers:
                if re.search('rel="last"', results.headers['Link']) is None:
                    last_link = True
            else:
                last_link = True
            parameters['page'] += 1
            if results.headers['Status'] == '429 Too Many Requests':
                print("Sleeping due to API Limit")
                time.sleep(200)
                results = helper.send_http_request(
                    api_call, 
                    "GET", 
                    verify=False, 
                    headers=headers, 
                    parameters=parameters, 
                    use_proxy=use_proxy
                )
            reporters_results = json.loads(results.content)
            for each_report in reporters_results:
                results_json.append(each_report)
                # print(each_report)
    except: 
        helper.log_error('Unable to connect to '+api_call)
        exit(1)
    
    if not len(api_call):
        exit(0)
        
    results_json.sort(key=extract_id)    
    
    results_length = {"Results" : len(results_json)}
    
    helper.log_debug('Number of results to be processed for {arg_endpoint}' + json.dumps(results_length))

    
    for each_json in results_json:
        if each_json['id'] > checkpoint:
            event = helper.new_event(
                source=input_type, 
                host=global_url_hosts,
                index=helper.get_output_index('main'), 
                sourcetype=arg_sourcetype,
                data=json.dumps(each_json))
            ew.write_event(event)
        
            helper.delete_check_point(check_point_value)    
            helper.save_check_point(check_point_value,each_json['id'])
        else:
            continue
    pass

        