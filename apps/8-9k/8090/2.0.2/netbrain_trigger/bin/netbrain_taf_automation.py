import logging
import sys
from lib.netbrain_ie import ModularAlert
from lib.netbrain_ie import Netbrain
from lib.log_event import printLog
import json
import requests
import os
import urllib.parse
    
"""
If the script is being called directly from the command-line, then this is likely being executed by Splunk.
TAF(Intent trigger) Support
"""

def get_kvstore_setting(key, splunk_server_url, headers, app_name):
    url = f"{splunk_server_url}/servicesNS/nobody/{app_name}/storage/collections/data/settings/{key}"
    r = requests.get(url, headers=headers, verify=False)
    if r.status_code == 200:
        data = r.json()
        return data.get('value')
    else:
        return None

def get_all_credentials(realm, splunk_server_url, headers, app_name):
    """
    Get all credentials for the given realm.
    Returns a list of tuples: [(username, password), ...]
    """
    url = f"{splunk_server_url}/servicesNS/nobody/{app_name}/storage/passwords?output_mode=json"
    r = requests.get(url, headers=headers, verify=False)
    if r.status_code != 200:
        return []
    data = r.json()
    credentials = []
    for entry in data.get('entry', []):
        if entry.get('content', {}).get('realm') == realm:
            username = entry['content'].get('username')
            password = entry['content'].get('clear_password')
            if username and password:
                credentials.append((username, password))
    return credentials

def delete_credential(realm, username, splunk_server_url, headers, app_name):
    """
    Delete a credential from Splunk storage.
    Returns True if successful, False otherwise.
    """
    # Format: realm:username: (note the trailing colon)
    credential_path = f"{realm}:{username}:"
    encoded_path = urllib.parse.quote(credential_path, safe='')
    url = f"{splunk_server_url}/servicesNS/nobody/{app_name}/storage/passwords/{encoded_path}"
    r = requests.delete(url, headers=headers, verify=False)
    return r.status_code in [200, 404]  # 404 means already deleted, which is fine

def validate_credential(nb_endpoint, username, password, tenant_name, domain_name):
    """
    Validate credentials by attempting to authenticate with Netbrain.
    Returns True if credentials are valid, False otherwise.
    Only validates the credential itself, not tenant/domain.
    """
    try:
        login_api_url = "/ServicesAPI/API/V1/Session"
        login_url = nb_endpoint + login_api_url
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        body_data = {
            "username": username,
            "password": password
        }
        response = requests.post(login_url, data=json.dumps(body_data), headers=headers, verify=False)
        # Status code 200 means authentication succeeded
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        return False



if __name__ == '__main__':
    PL = printLog()
    # Make sure this is a call to execute
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        
        try:
            #Read Configuration Payload
            payload = json.loads(sys.stdin.read())
            app_name = os.path.basename(os.path.dirname(os.path.dirname(__file__)))
            trigger_params = payload["configuration"]
            alert_Name = payload["search_name"]
            device_name = trigger_params.get("device", '')
            #nb_endpoint = trigger_params["ie_api_url"].replace("\/$","")
            catagory = trigger_params['catagory']
            source = trigger_params['source']
            # tenant_name = trigger_params["ie_tenant"]
            # domain_name = trigger_params["ie_domain"]
            # username = trigger_params["ie_username"]
            # password = trigger_params["ie_password"]
            incident_subject = trigger_params["incident_subject"]
            interface = trigger_params.get('interface', '')
            neighbor_ip = trigger_params.get('neighbor_ip', '')
            device_ip = trigger_params.get('device_ip', '')
            custom_data = trigger_params.get('custom_data', '')

            session_key = payload.get('session_key', '')
            splunk_server_url = payload.get('server_uri', '')
            headers = {'Authorization': 'Splunk ' + session_key}
            # KV Store
            nb_endpoint = get_kvstore_setting("ie_api_url", splunk_server_url, headers, app_name)
            nb_endpoint = nb_endpoint.strip('/')
            tenant_name = get_kvstore_setting("ie_tenant", splunk_server_url, headers, app_name)
            domain_name = get_kvstore_setting("ie_domain", splunk_server_url, headers, app_name)

            # Get all credentials for the realm
            all_credentials = get_all_credentials("netbrain_trigger", splunk_server_url, headers, app_name)

            if not all_credentials:
                log = "No credentials found for netbrain_trigger realm"
                PL.print_error_log(log)
                sys.exit(1)

            username = None
            password = None

            # If only one credential, use it directly without validation
            if len(all_credentials) == 1:
                username, password = all_credentials[0]
                PL.print_log("Single credential found, using username: {}".format(username))
            else:
                # Multiple credentials found - validate each one
                invalid_credentials = []
                valid_credential_found = False

                for cred_username, cred_password in all_credentials:
                    if validate_credential(nb_endpoint, cred_username, cred_password, tenant_name, domain_name):
                        username = cred_username
                        password = cred_password
                        valid_credential_found = True
                        break
                    else:
                        invalid_credentials.append((cred_username, cred_password))

                if not valid_credential_found:
                    log = "No valid credentials found. All credentials failed authentication."
                    PL.print_error_log(log)
                    sys.exit(1)

                # Delete all invalid credentials
                if invalid_credentials:
                    for invalid_username, _ in invalid_credentials:
                        delete_credential("netbrain_trigger", invalid_username, splunk_server_url, headers, app_name)

            netbrain = Netbrain(nb_endpoint, username, password, tenant_name, domain_name)
            if not device_name and device_ip:
                device_name = netbrain.ip_to_devname(device_ip)
                
            if not device_name:
                log = "Device Name is empty and cannot find the device name from the device IP"
                PL.print_log(log)

            specific_data = {
                'device_name': device_name,
                'device_ip': device_ip,
                'incident_subject': incident_subject,
                'interface': interface,
                'neighbor_ip': neighbor_ip,
                'custom_data': custom_data
            }

            response = netbrain.netbrain_taf_automation(specific_data, source, catagory)
            if isinstance(response, dict) and response.get('statusDescription', '') == 'Success.':
                incident_url = nb_endpoint + '/' + response['incidentUrl']
                incident_id = response['incidentId']
                log = "Search Name ----- {} ---- Incident {} created in Netbrain ---- NB Incident url {}".format(alert_Name, incident_id, incident_url)
                PL.print_log(log)
            else:
                log = "Search Name ----- {} ---- Something went wrong during Netbrain TAF ---- Netbrain response: {}".format(alert_Name, json.dumps(response))
                PL.print_log(log)
            sys.exit(0)
        except Exception as e:
            PL.print_error_log("Unhandled exception was caught, this may be due to a defect in the script:" + str(e))
            raise
        
    else:
        print("Unsupported execution mode (expected --execute flag)")
        # print >> sys.stderr, "Unsupported execution mode (expected --execute flag)"
        sys.exit(1)