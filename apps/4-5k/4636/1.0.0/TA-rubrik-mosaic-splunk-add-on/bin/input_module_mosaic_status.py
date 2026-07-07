# encoding = utf-8

import os
import sys
import time
import base64
import datetime
import json

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    global_account = helper.get_arg('global_account')
    username = global_account['username']
    password = global_account['password']
    global_cluster_name = helper.get_arg("cluster_name")
    global_cluster_ip = helper.get_arg("mosaic_cluster_ip")
    global_cluster_port = helper.get_arg("mosaic_cluster_port")
    global_validate_ssl = helper.get_arg("validate_ssl")
    base_url = ('https://'+global_cluster_ip+':'+global_cluster_port+'/datos/')
    # get token and set up header
    headers = {}
    body = {
        "username":username,
        "password":password
    }
    headers['Content-Type'] = 'application/json'
    parameters = {}
    url = base_url + 'login'
    response = helper.send_http_request(url, method='POST', payload=body, parameters=parameters, headers=headers, verify=global_validate_ssl, timeout=None, use_proxy=False)
    response = response.json()
    token = response['data']['token']
    headers['x-access-token'] = str(token)
    # get events
    url = base_url + 'datosstatus'
    response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=global_validate_ssl, timeout=None, use_proxy=False)
    response = response.json()
    # write out status as a new JSON
    output={}
    output['clusterStatus'] = response['data']['cluster_status']
    output['clusterStatusMsg'] = response['data']['cluster_status_msg']
    output['datosPrimaryIp'] = response['data']['datos_primary_ip']
    output['nodeCount'] = len(response['data']['nodes'])
    # get unhealthy node count
    unhealthy_node_count = 0
    for node in response['data']['nodes'].keys():
        if response['data']['nodes'][node]['status'] != 'HEALTHY':
            unhealthy_node_count += 1
    output['unhealthyNodeCount'] = unhealthy_node_count
    output['clusterName'] = global_cluster_name
    out_json = json.dumps(output)
    event = helper.new_event(data=out_json)
    ew.write_event(event)
