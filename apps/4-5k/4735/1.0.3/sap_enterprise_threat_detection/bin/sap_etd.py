from __future__ import print_function
import copy
import sys
import json
import os
import requests
import sys
import adapter

pid = os.getpid()

def send_message(payload):
    # Passed in meta information related to alert
    configuration = payload.get('configuration')
    configuration_base_url = configuration.get('base_url').rstrip('/')
    configuration_username = configuration.get('username')
    sid = payload.get('sid')

    # Password retrieval
    password_storage_url = payload.get('server_uri') + '/servicesNS/nobody/sap_enterprise_threat_detection/storage/passwords/%3Asap_etd_user%3A'
    password_storage_headers = { 'Authorization': 'Splunk %s' % payload.get('session_key') }
    password_storage_params = {'output_mode': 'json'}

    print("INFO message='retrieve credentials from Splunk storage service'", file=sys.stderr)
    try:
        password_storage_request = requests.get(password_storage_url, headers=password_storage_headers, verify=False, params=password_storage_params)
    except Exception as e:
        print("ERROR message='failed retrieving credentials' error_message='%s' pid=%s" % (e, pid), file=sys.stderr)
        return False
    password_storage_payload = json.loads(password_storage_request.text)
    password_storage_clear_password = password_storage_payload['entry'][0]['content'].get('clear_password', '')

    # Data envelope definition that will be sent to SAP ETD
    data_envelope = copy.deepcopy(payload)
    # Remove session_key to avoid possible access compromise
    data_envelope.pop('session_key')
    # Remove configuration block and set explicitly to control leakage of information
    configuration = data_envelope.get('configuration', {})
    data_envelope['configuration'] = {
        'severity': configuration.get('severity')
    }
    # Set constant namespace
    data_envelope['__AGENT__'] = 'SPLUNK_SAP_ETD_ALERT_ACTION_V1.0.0'

    # Retrieve SAP access token
    print("INFO message='authenticate with SAP Enterprise Threat Detection' pid=%s" % (pid), file=sys.stderr)
    try:
        token = adapter.access_token(configuration_base_url, configuration_username, password_storage_clear_password)
    except Exception as e:
        print("ERROR message='failed authentication' error_message='%s' pid=%s" % (e, pid), file=sys.stderr)
        return False

    # Send SAP result/event
    print("INFO message='send event from Splunk job artifact to SAP Enterprise Threat Detection' sid='%s' pid=%s" % (sid, pid), file=sys.stderr)
    try:
        adapter.send_event(configuration_base_url, token, json.dumps(data_envelope))
    except Exception as e:
        print("ERROR message='failed sending event' error='%s' pid=%s" % (e, pid), file=sys.stderr)
        return False
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        # Passed in meta information related to alert
        payload = json.loads(sys.stdin.read())
        search_name = payload.get('search_name')
        configuration = payload.get('configuration')
        configuration_base_url = configuration.get('base_url')

        print("INFO message='transaction start' etd_host='%s' savedsearch='%s' pid=%s" % (configuration_base_url, search_name, pid), file=sys.stderr)
        if not send_message(payload):
            print("FATAL message='transaction end' status='fail' pid=%s" % pid, file=sys.stderr)
            sys.exit(2)
        else:
            print("INFO message='transaction end' status='success' pid=%s" % pid, file=sys.stderr)
    else:
        print("FATAL message='Unsupported execution mode (expected --execute flag)' pid=%s" % pid, file=sys.stderr)
        sys.exit(1)
