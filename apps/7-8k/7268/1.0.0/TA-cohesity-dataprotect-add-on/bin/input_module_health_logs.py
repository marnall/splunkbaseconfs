# encoding = utf-8
import requests
import json

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
    """Implement your own validation logic to validate the input configurations"""
    # This example accesses the modular input variable
    # cluster_ip_fqdn = definition.parameters.get('cluster_ip_fqdn', None)
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""

    token = ''
    # Get the input values
    cluster_ip = helper.get_arg('cluster_ip_fqdn')
    username = helper.get_arg('username')
    password = helper.get_arg('password')
    domain = helper.get_arg('domain')
    manage = helper.get_arg('manage')


    # Get authentication token
    authUrl = "https://%s/irisservices/api/v1/public/accessTokens"%(cluster_ip)
    payload = {
        'username': username,
        'password': password,
        'domain': domain
        }
    headers = {
        'Content-Type': 'application/json'
        }

    try:
        authResponse = helper.send_http_request(authUrl, 'POST', parameters=None, payload=payload, headers=headers, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)
        authJResp = authResponse.json()

        if authResponse.status_code == 201:
            token = authJResp['tokenType'] + ' ' + authJResp['accessToken']
            
            if (manage == 'alert_logs' or manage == 'both'):
                collect_alert_list(cluster_ip, token, helper, ew)
            if (manage == 'audit_logs' or manage == 'both'):
                collect_audit_logs(cluster_ip, token, helper, ew)
        

    except Exception as e:
            raise e

# Function to collect alert list from configured cohesity cluster
def collect_alert_list(cluster_ip, token, helper, ew):
    try:
        alertList = []
        authUrl = "https://%s/irisservices/api/v1/public/alerts"%(cluster_ip)
        headers = {
            'Authorization':token,
            'Content-Type': 'application/json'
        }

        alertResponse = helper.send_http_request(authUrl, 'Get', parameters=None, headers=headers, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)
        alertJResp = alertResponse.json()

        if alertResponse.status_code == 200:
            # Checkpoint
            for alert in alertJResp:
                state = helper.get_check_point(alert['id'])
                if state is None:
                    alertList.append(alert)
                    helper.save_check_point(alert['id'], 'indexed')
                # helper.delete_check_point(alert['id'])

        # To create a splunk event
        event = helper.new_event(json.dumps(alertList), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
        ew.write_event(event)

    except Exception as e:
            raise e

# Function to collect audit logs from configured cohesity cluster
def collect_audit_logs(cluster_ip, token, helper, ew):
    try:
        auditLogs = []
        auditLogUrl = "https://%s/v2/audit-logs"%(cluster_ip)
        headers = {
            'Authorization':token,
            'Content-Type': 'application/json'
        }

        auditLogResponse = helper.send_http_request(auditLogUrl, 'Get', parameters=None, headers=headers, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)
        auditLogJResp = auditLogResponse.json()

        if auditLogResponse.status_code == 200:
            # Checkpoint
            for auditLog in auditLogJResp['auditLogs']:
                keyValue = auditLog['ip'] + '-' + str(auditLog['timestampUsecs'])
                state = helper.get_check_point(keyValue)
                if state is None:
                    auditLogs.append(auditLog)
                    helper.save_check_point(keyValue, 'indexed')
                # helper.delete_check_point(keyValue)

        # To create a splunk event
        event = helper.new_event(json.dumps(auditLogs), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
        ew.write_event(event)

    except Exception as e:
            raise e