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
    verify_ssl = helper.get_arg("verify_ssl")
    global_rubrik_node = helper.get_arg("rubrik_node")
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
    response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
    if response.status_code != 200:
        failed_http_call(helper, response)
    response = response.json()
    cluster_name = response['name']
    # get all nodes
    url = ('https://'+global_rubrik_node+'/api/internal/node')
    response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
    if response.status_code != 200:
        failed_http_call(helper, response)
    response = response.json()
    for node in response['data']:
        output={}
        output['clusterName'] = cluster_name
        output['nodeId'] = node['id']
        url = ('https://'+global_rubrik_node+'/api/internal/node/'+node['id']+'/stats')
        response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
        if response.status_code != 200:
            failed_http_call(helper, response)
        response = response.json()
        output['_time'] = response['iops']['readsPerSecond'][-1]['time']
        output['status'] = response['status']
        output['ipAddress'] = response['ipAddress']
        output['isTunnelEnabled'] = response['supportTunnel']['isTunnelEnabled']
        output['cpuStat'] = response['cpuStat'][-1]['stat']
        output['bytesReceived'] = response['networkStat']['bytesReceived'][-1]['stat']
        output['bytesTransmitted'] = response['networkStat']['bytesTransmitted'][-1]['stat']
        output['readsPerSecond'] = response['iops']['readsPerSecond'][-1]['stat']
        output['writesPerSecond'] = response['iops']['writesPerSecond'][-1]['stat']
        output['readBytePerSecond'] = response['ioThroughput']['readBytePerSecond'][-1]['stat']
        output['writeBytePerSecond'] = response['ioThroughput']['writeBytePerSecond'][-1]['stat']
        url = ('https://'+global_rubrik_node+'/api/internal/node/'+node['id'])
        response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
        if response.status_code != 200:
            failed_http_call(helper, response)
        response = response.json()
        output['cpuCores'] = response['cpuCores']
        output['ram'] = response['ram']
        output['networkSpeed'] = response['networkSpeed']
        hdd_active_count = 0
        hdd_inactive_count = 0
        ssd_active_count = 0
        ssd_inactive_count = 0
        for hdd in response['hdd']:
            if hdd['status'] == 'ACTIVE':
                hdd_active_count += 1
            else:
                hdd_inactive_count += 1
            output[hdd['id']+'_isDegraded'] = hdd['isDegraded']
            output[hdd['id']+'_path'] = hdd['path']
            output[hdd['id']+'_capacityBytes'] = hdd['capacityBytes']
            output[hdd['id']+'_unallocatedBytes'] = hdd['unallocatedBytes']
            output[hdd['id']+'_usableBytes'] = hdd['usableBytes']
            output[hdd['id']+'_diskType'] = hdd['diskType']
            output[hdd['id']+'_status'] = hdd['status']
        for ssd in response['ssd']:
            if ssd['status'] == 'ACTIVE':
                ssd_active_count += 1
            else:
                ssd_inactive_count += 1
            output[ssd['id']+'_isDegraded'] = ssd['isDegraded']
            output[ssd['id']+'_path'] = ssd['path']
            output[ssd['id']+'_capacityBytes'] = ssd['capacityBytes']
            output[ssd['id']+'_unallocatedBytes'] = ssd['unallocatedBytes']
            output[ssd['id']+'_usableBytes'] = ssd['usableBytes']
            output[ssd['id']+'_diskType'] = ssd['diskType']
            output[ssd['id']+'_status'] = ssd['status']
        output['hdd_active_count'] = hdd_active_count
        output['hdd_inactive_count'] = hdd_inactive_count
        output['ssd_active_count'] = ssd_active_count
        output['ssd_inactive_count'] = ssd_inactive_count
        out_json = json.dumps(output, sort_keys=True)
        event = helper.new_event(data=out_json)
        ew.write_event(event)
        event_count += 1
    helper.log_info('Finished processing data from '+global_rubrik_node+', wrote '+str(event_count)+' event(s).')
