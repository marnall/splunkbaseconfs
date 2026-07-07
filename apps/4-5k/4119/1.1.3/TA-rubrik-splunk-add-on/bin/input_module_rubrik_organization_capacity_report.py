# encoding = utf-8

from future.standard_library import install_aliases
install_aliases()

import os
import sys
import time
import base64
import datetime
import json

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
    global_verify = helper.get_arg("verify_ssl_certificates")
    url = ('https://'+global_rubrik_node+'/api/v1/cluster/me')
    helper.log_info('Running query for '+global_rubrik_node)
    check_timeout_value(helper, helper.get_arg("timeout"))
    helper.log_debug('Using username '+username)
    helper.log_debug('Using timeout value '+str(timeout))
    # create headers
    headers = {}
    auth = get_auth_header(username,password)
    headers['Authorization'] = 'Basic {0}'.format(auth.decode("utf-8"))
    parameters = {}
    # get our cluster name first
    url = ('https://'+global_rubrik_node+'/api/v1/cluster/me')
    response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=global_verify, timeout=timeout, use_proxy=False)
    if response.status_code != 200:
        failed_http_call(helper, response)
    response = response.json()
    cluster_name = response['name']
    # get canned 'Capacity Over Time' report
    url = ('https://'+global_rubrik_node+'/api/internal/report?report_template=CapacityOverTime&report_type=Canned')
    response = helper.send_http_request(url, method='GET', headers=headers, verify=global_verify, timeout=timeout, use_proxy=False)
    if response.status_code != 200:
        failed_http_call(helper, response)
    response = response.json()
    report_id = response['data'][0]['id']
    url = ('https://'+global_rubrik_node+'/api/internal/report/'+report_id+'/table')
    body = {
        "limit": 100,
        "sortBy": "Month",
        "sortOrder": "desc"
    }
    response = helper.send_http_request(url, method='POST', headers=headers, verify=global_verify, timeout=timeout, use_proxy=False,payload=body)
    if response.status_code != 200:
        failed_http_call(helper, response)
    response = response.json()
    this_month = datetime.date.today().month
    if this_month < 10:
        this_month = '0' + str(this_month)
    else:
        this_month = str(this_month)
    this_year = str(datetime.date.today().year)
    current_month = this_year + '-' + this_month
    for data in response['dataGrid']:
        this_record = {}
        counter = 0
        for column in response['columns']:
            this_record[column] = data[counter]
            counter=counter+1
        this_record['cluster_name'] = cluster_name
        if this_record['Month'] == current_month:
            out_json = json.dumps(this_record)
            event = helper.new_event(data=out_json)
            ew.write_event(event)
            event_count += 1
    helper.log_info('Finished processing data from '+global_rubrik_node+', wrote '+str(event_count)+' event(s).')
