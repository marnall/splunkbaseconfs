# encoding = utf-8

import os
import sys
import time
import base64
import datetime
import json

timeout = 60;

def validate_input(helper, definition):
    pass

def failed_http_call(helper, response):
    if response.status_code == 401:
        helper.log_error('HTTP status 401 received, likely credentials are incorrect, or account does not have permissions, please check Global Account')
        helper.log_error('Target URL: '+response.url)
        helper.log_error('HTTP response body: '+response.text)
        raise ValueError('HTTP status 401 received')
    else:
        helper.log_error('HTTP status '+str(response.status_code)+' received, see input log for more details')
        helper.log_error('Target URL: '+response.url)
        helper.log_error('HTTP response body: '+response.text)
        raise ValueError('HTTP status '+str(response.status_code)+' received, see input log for more details')

def check_timeout_value(helper, timeout):
    if not is_integer(timeout):
        helper.log_error('Passed timeout was not an integer, using default value of 60 seconds')
        timeout = 60
    if not 0 < int(timeout) <= 3600:
        helper.log_error('Passed timeout was not between 0 and 3600, using default value of 60 seconds')
        timeout = 60
    else:
        timeout = int(timeout)

def is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()

def collect_events(helper, ew):
    event_count = 0
    global_account = helper.get_arg('global_account')
    username = global_account['username']
    password = global_account['password']
    global_polaris_url = helper.get_arg("polaris_url")
    helper.log_info('Running query for '+global_polaris_url)
    check_timeout_value(helper, helper.get_arg("timeout"))
    helper.log_debug('Using username '+username)
    helper.log_debug('Using timeout value '+str(timeout))
    # get our token first
    uri = ('https://'+global_polaris_url+'/api/session')
    headers = {
        'Content-Type':'application/json',
        'Accept':'application/json'
        }
    payload = ('{"username":"'+username+'","password":"'+password+'"}')
    parameters = {}
    response = helper.send_http_request(uri, method='POST', payload=payload, parameters=parameters, headers=headers, verify=True, timeout=timeout, use_proxy=False)
    if response.status_code != 200:
        failed_http_call(helper, response)
    response = response.json()
    token = response["access_token"]
    token = "Bearer "+str(token)
    # Query for anomalies
    uri = 'https://' + global_polaris_url + '/api/graphql'
    headers = {
        'Content-Type':'application/json',
        'Accept':'application/json',
        'Authorization':token
        }
    timestamp = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
    timestamp = str(timestamp.isoformat())[:-7] + 'Z'
    payload = '{"operationName":"eventSeriesList","variables":{"filters":{"objectType":[],"lastActivityStatus":[],"lastActivityType":["Anomaly"],"severity":[],"cluster":{"id":[]},"lastUpdated_gt":"'+timestamp+'","objectName":""},"first":20},"query":"query eventSeriesList($after: String, $filters: ActivitySeriesFilterInput, $first: Int, $sortBy: ActivitySeriesSortByEnum, $sortOrder: SortOrderEnum) { activitySeriesConnection(after: $after, first: $first, filters: $filters, sortBy: $sortBy, sortOrder: $sortOrder) { edges { node {id activitySeriesId lastUpdated lastActivityType lastActivityStatus objectId objectName objectType cluster { id name __typename } severity progress activityConnection(first: 1) {   nodes {     message     __typename   }   __typename } __typename } __typename } pageInfo { endCursor hasNextPage hasPreviousPage __typename } __typename }}"}'
    response = helper.send_http_request(uri, method='POST', payload=payload, parameters=parameters, headers=headers, verify=True, timeout=timeout, use_proxy=False)
    if response.status_code != 200:
        failed_http_call(helper, response)
    response = response.json()
    # Process results
    events = response['data']['activitySeriesConnection']['edges']
    for event in events:
        this_event = {}
        this_event['id'] = event['node']['id']
        this_event['_time'] = event['node']['lastUpdated']
        this_event['objectId'] = event['node']['objectId']
        this_event['objectName'] = event['node']['objectName']
        this_event['objectType'] = event['node']['objectType']
        this_event['severity'] = event['node']['severity']
        this_event['clusterName'] = event['node']['cluster']['name']
        this_event['message'] = event['node']['activityConnection']['nodes'][0]['message']
        out_json = json.dumps(this_event,sort_keys=True)
        new_event = helper.new_event(data=out_json)
        ew.write_event(new_event)
        event_count += 1
    helper.log_info('Finished processing data from '+global_polaris_url+', wrote '+str(event_count)+' event(s).')
