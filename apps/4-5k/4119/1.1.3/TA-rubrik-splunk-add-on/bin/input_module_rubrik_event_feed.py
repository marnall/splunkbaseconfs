# encoding = utf-8

from future.standard_library import install_aliases
install_aliases()

import os
import sys
import time
import base64
import datetime
import json
import urllib.parse

timeout = 60;

def validate_input(helper, definition):
    pass

def get_auth_header(username, password):
    if sys.version_info < (3,):
        return base64.b64encode(username+':'+password)
    else:
        return base64.b64encode(bytes(username+':'+password,'utf-8'))

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
    password= global_account['password']
    global_rubrik_node = helper.get_arg("rubrik_node")
    helper.log_info('Running query for '+global_rubrik_node)
    verify_ssl = helper.get_arg("verify_ssl")
    check_timeout_value(helper, helper.get_arg("timeout"))
    helper.log_debug('Using username '+username)
    helper.log_debug('Using timeout value '+str(timeout))
    # get our cluster name first
    url = ('https://'+global_rubrik_node+'/api/v1/cluster/me')
    # create headers
    headers = {}
    auth = get_auth_header(username,password)
    headers['Authorization'] = 'Basic {0}'.format(auth.decode("utf-8"))
    parameters = {}
    response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
    if response.status_code != 200:
        failed_http_call(helper, response)
    response = response.json()
    cluster_name = response['name']
    # get cluster version
    url = ('https://'+global_rubrik_node+'/api/v1/cluster/me/version')
    response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
    if response.status_code != 200:
        failed_http_call(helper, response)
    response = response.json()
    cluster_version = response['version']
    major_version = int(str(cluster_version).split('.')[0])
    minor_version = int(str(cluster_version).split('.')[1])
    if ((major_version == 5 and minor_version < 2) or major_version < 5): # cluster version is pre 5.2
        url = ('https://'+global_rubrik_node+'/api/internal/event')
        helper.log_info('Getting events from '+global_rubrik_node)
        # get timestamp for 20 mins ago - format: 2018-01-16T00:00:00Z
        time = datetime.datetime.utcnow() - datetime.timedelta(minutes=20)
        time = str(time.isoformat())[:-7] + 'Z'
        parameters = {}
        parameters['limit'] = 9999
        parameters['after_date'] = time
        response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
        if response.status_code != 200:
            failed_http_call(helper, response)
        response = response.json()
        helper.log_info('Result set from '+global_rubrik_node+' is '+str(len(response['data']))+' records.')
        for event in response['data']:
            if (event['eventStatus'] in ['Failure','Warning','Success','Canceled']):
                this_record = {}
                this_record['_time'] = event['time']
                event_info = json.loads(event['eventInfo'])
                this_record['eventType'] = event['eventType']
                this_record['objectId'] = event['objectId']
                if ('objectName' in list(event.keys())):
                    this_record['objectName'] = event['objectName']
                this_record['objectType'] = event['objectType']
                this_record['eventStatus'] = event['eventStatus']
                this_record['id'] = event['id']
                this_record['message'] = event_info['message']
                this_record['clusterName'] = cluster_name
                if ('${locationName}' in list(event_info['params'].keys())):
                    this_record['locationName'] = event_info['params']['${locationName}']
                if ('${username}' in list(event_info['params'].keys())):
                    this_record['username'] = event_info['params']['${username}']
                if ('${orgName}' in list(event_info['params'].keys())):
                    this_record['orgName'] = event_info['params']['${orgName}']
                if ('${orgId}' in list(event_info['params'].keys())):
                    this_record['orgId'] = event_info['params']['${orgId}']
                if ('${hostname}' in list(event_info['params'].keys())):
                    this_record['hostname'] = event_info['params']['${hostname}']
                if this_record['eventType'] == 'Recovery':
                    event_series_id = event['eventSeriesId']
                    event_series_url = ('https://'+global_rubrik_node+'/api/internal/event_series/'+event_series_id)
                    event_series = helper.send_http_request(event_series_url, method='GET', headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
                    event_series = event_series.json()
                    if ('username' in list(event_series.keys())):
                        this_record['username'] = event_series['username']
                out_json = json.dumps(this_record, sort_keys=True)
                event = helper.new_event(data=out_json)
                ew.write_event(event)
                event_count += 1
        helper.log_info('Finished processing data from '+global_rubrik_node)
    else: # cluster version is 5.2 or newer
        url = ('https://'+global_rubrik_node+'/api/v1/event/latest')
        helper.log_info('Getting events from '+global_rubrik_node)
        # get timestamp for 20 mins ago - format: 2018-01-16T00:00:00Z
        time = datetime.datetime.utcnow() - datetime.timedelta(minutes=20)
        time = time.strftime("%A %B %d %Y %I:%M:%S")
        parameters = {}
        parameters['limit'] = 9999
        parameters['before_date'] = time # before_date is correct in 5.2, badly named parameter
        response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
        if response.status_code != 200:
            failed_http_call(helper, response)
        response = response.json()
        helper.log_info('Result set from '+global_rubrik_node+' is '+str(len(response['data']))+' records.')
        for event in response['data']:
            if (event['latestEvent']['eventStatus'] in ['Failure','Warning','Success','Canceled','TaskSuccess','Info']):
                this_record = {}
                this_record['_time'] = event['latestEvent']['time']
                event_info = json.loads(event['latestEvent']['eventInfo'])
                this_record['eventType'] = event['latestEvent']['eventType']
                this_record['objectId'] = event['latestEvent']['objectId']
                if ('objectName' in list(event['latestEvent'].keys())):
                    this_record['objectName'] = event['latestEvent']['objectName']
                this_record['objectType'] = event['latestEvent']['objectType']
                this_record['eventStatus'] = event['latestEvent']['eventStatus']
                this_record['id'] = event['latestEvent']['id']
                this_record['message'] = event_info['message']
                this_record['clusterName'] = cluster_name
                if ('${locationName}' in list(event_info['params'].keys())):
                    this_record['locationName'] = event_info['params']['${locationName}']
                if ('${username}' in list(event_info['params'].keys())):
                    this_record['username'] = event_info['params']['${username}']
                if ('${orgName}' in list(event_info['params'].keys())):
                    this_record['orgName'] = event_info['params']['${orgName}']
                if ('${orgId}' in list(event_info['params'].keys())):
                    this_record['orgId'] = event_info['params']['${orgId}']
                if ('${hostname}' in list(event_info['params'].keys())):
                    this_record['hostname'] = event_info['params']['${hostname}']
                if this_record['eventType'] == 'Recovery':
                    event_series_id = event['latestEvent']['eventSeriesId']
                    event_series_url = ('https://'+global_rubrik_node+'/api/v1/event_series/'+event_series_id)
                    event_series = helper.send_http_request(event_series_url, method='GET', headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
                    event_series = event_series.json()
                    if ('username' in list(event_series.keys())):
                        this_record['username'] = event_series['username']
                out_json = json.dumps(this_record, sort_keys=True)
                event = helper.new_event(data=out_json)
                ew.write_event(event)
                event_count += 1
        helper.log_info('Finished processing data from '+global_rubrik_node+', wrote '+str(event_count)+' event(s).')
