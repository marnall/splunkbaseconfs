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
    helper.log_info('Running query for '+global_rubrik_node)
    verify_ssl = helper.get_arg("verify_ssl")
    check_timeout_value(helper, helper.get_arg("timeout"))
    helper.log_debug('Using username '+username)
    helper.log_debug('Using timeout value '+str(timeout))
    url = ('https://'+global_rubrik_node+'/api/v1/cluster/me')
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
    # get archive locations
    url = ('https://'+global_rubrik_node+'/api/internal/archive/location')
    response = helper.send_http_request(url, method='GET', headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
    if response.status_code != 200:
        failed_http_call(helper, response)
    archive_locations = response.json()
    # get archive usage
    url = ('https://'+global_rubrik_node+'/api/internal/stats/data_location/usage')
    response = helper.send_http_request(url, method='GET', headers=headers, verify=verify_ssl, timeout=timeout, use_proxy=False)
    if response.status_code != 200:
        failed_http_call(helper, response)
    response = response.json()
    for location in response['data']:
        # format output
        this_record = {}
        this_record['locationId'] = location['locationId']
        for location_detail in archive_locations['data']:
            if location_detail['id'] == location['locationId']:
                this_record['locationName'] = location_detail['name']
        this_record['clusterName'] = cluster_name
        this_record['dataDownloaded'] = location['dataDownloaded']
        this_record['dataArchived'] = location['dataArchived']
        this_record['numVMsArchived'] = location['numVMsArchived']
        this_record['numFilesetsArchived'] = location['numFilesetsArchived']
        this_record['numLinuxFilesetsArchived'] = location['numLinuxFilesetsArchived']
        this_record['numShareFilesetsArchived'] = location['numShareFilesetsArchived']
        this_record['numShareFilesetsArchived'] = location['numShareFilesetsArchived']
        this_record['numMssqlDbsArchived'] = location['numMssqlDbsArchived']
        this_record['numHypervVmsArchived'] = location['numHypervVmsArchived']
        this_record['numNutanixVmsArchived'] = location['numNutanixVmsArchived']
        this_record['numManagedVolumesArchived'] = location['numManagedVolumesArchived']
        this_record['numStorageArrayVolumeGroupsArchived'] = location['numStorageArrayVolumeGroupsArchived']
        this_record['numWindowsVolumeGroupsArchived'] = location['numWindowsVolumeGroupsArchived']
        # return output
        out_json = json.dumps(this_record)
        event = helper.new_event(data=out_json)
        ew.write_event(event)
        event_count += 1
    helper.log_info('Finished processing data from '+global_rubrik_node+', wrote '+str(event_count)+' event(s).')
