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
    url = base_url + 'listalerts'
    response = helper.send_http_request(url, method='GET', parameters=parameters, headers=headers, verify=global_validate_ssl, timeout=None, use_proxy=False)
    response = response.json()
    # write out each event as a new JSON
    for event in response:
        output={}
        output['category'] = event['category']
        output['eventType'] = event['event']
        output['policy'] = event['policy']
        output['schedule'] = event['schedule']
        output['sourceCluster'] = event['source']
        output['sourceMgmtObj'] = event['source_mgmt_obj']
        output['store'] = event['store']
        output['timestamp'] = datetime.datetime.fromtimestamp(event['timestamp']).strftime('%c')
        output['eventId'] = event['_id']
        output['message'] = event['msg']
        output['summary'] = event['title']
        output['clusterName'] = global_cluster_name
        out_json = json.dumps(output)
        event = helper.new_event(data=out_json)
        ew.write_event(event)
