import logging
import sys
from lib.netbrain_ie import ModularAlert
from lib.netbrain_ie import Netbrain
from lib.log_event import printLog
import json
import requests
import urllib.parse
     
"""
If the script is being called directly from the command-line, then this is likely being executed by Splunk.
"""
def get_kvstore_setting(key, splunk_server_url, headers):
    url = f"{splunk_server_url}/servicesNS/nobody/netbrain_trigger/storage/collections/data/settings/{key}"
    r = requests.get(url, headers=headers, verify=False)
    if r.status_code == 200:
        data = r.json()
        return data.get('value')
    else:
        return None

def get_all_credentials(realm, splunk_server_url, headers):
    """
    Get all credentials for the given realm.
    Returns a list of tuples: [(username, password), ...]
    """
    url = f"{splunk_server_url}/servicesNS/nobody/netbrain_trigger/storage/passwords?output_mode=json"
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

def delete_credential(realm, username, splunk_server_url, headers):
    """
    Delete a credential from Splunk storage.
    Returns True if successful, False otherwise.
    """
    # Format: realm:username: (note the trailing colon)
    credential_path = f"{realm}:{username}:"
    encoded_path = urllib.parse.quote(credential_path, safe='')
    url = f"{splunk_server_url}/servicesNS/nobody/netbrain_trigger/storage/passwords/{encoded_path}"
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
    
    # Make sure this is a call to execute
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        
        try:
            #Read Configuration Payload
            PL = printLog()
            payload = json.loads(sys.stdin.read())
            trigger_params = payload["configuration"]
            alert_Name = payload["search_name"]
            stub_name = trigger_params["stub_name"]
            # nb_endpoint = trigger_params["nb_endpoint"].replace("\/$","")
            # tenant_name = trigger_params["tenant_id"]
            # domain_name = trigger_params["domain_id"]
            # username = trigger_params["username"]
            # password = trigger_params["password"]

            #Construct the request body payload
            context_map_cisco_aci_device_para = {}
            if "apic" in trigger_params:
                context_map_cisco_aci_device_para["apic"] = trigger_params["apic"]
            else:
                PL.print_error_log("Context map body params None value: APIC value can NOT be Null.")
            if "device" in trigger_params:
                context_map_cisco_aci_device_para["device"] = trigger_params["device"]
            if "pod_id" in trigger_params:
                context_map_cisco_aci_device_para["pod_id"] = trigger_params["pod_id"]
            if "tenant_name" in trigger_params:
                context_map_cisco_aci_device_para["pod_tenant_nameid"] = trigger_params["tenant_name"]
                if "vrf_name" in trigger_params:
                    context_map_cisco_aci_device_para["vrf_name"] = trigger_params["vrf_name"]
                if "application_name" in trigger_params:
                    context_map_cisco_aci_device_para["application_name"] = trigger_params["application_name"]
            elif "tenant_name" not in trigger_params and ("vrf_name" in trigger_params or "application_name" in trigger_params):
                PL.print_error_log("Context map body params None value: if VRF Name or Application Name is provided, Tenant Name can NOT be Null.")
            incident_subject = trigger_params["incident_subject"]

            session_key = payload.get('session_key', '')
            splunk_server_url = payload.get('server_uri', '')
            headers = {'Authorization': 'Splunk ' + session_key}
            # KV Store
            nb_endpoint = get_kvstore_setting("ie_api_url", splunk_server_url, headers)
            nb_endpoint = nb_endpoint.strip('/')
            tenant_name = get_kvstore_setting("ie_tenant", splunk_server_url, headers)
            domain_name = get_kvstore_setting("ie_domain", splunk_server_url, headers)

            # Get all credentials for the realm
            all_credentials = get_all_credentials("netbrain_trigger", splunk_server_url, headers)

            if not all_credentials:
                log = "No credentials found for netbrain_trigger realm"
                PL.print_error_log(log)
                sys.exit(1)

            username = None
            password = None

            # If only one credential, use it directly without validation
            if len(all_credentials) == 1:
                username, password = all_credentials[0]
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
                        delete_credential("netbrain_trigger", invalid_username, splunk_server_url, headers)

            netbrain = Netbrain(nb_endpoint,username,password,tenant_name,domain_name)
            response = netbrain.trigger_context_map(stub_name, incident_subject, context_map_cisco_aci_device_para)
            PL.print_log("Context map response: " + json.dumps(response))
            mapURl = nb_endpoint + '/' + response['mapUrl']
            log = " Search Name ----- " + alert_Name + " ----- Map URL ----- Context ----- " + mapURl
            PL.print_log(log)

            sys.exit(0)
        except Exception as e:
            PL.print_error_log("Unhandled exception was caught, this may be due to a defect in the script:" + str(e))
            raise
        
    else:
        PL.print_error_log("Unsupported execution mode (expected --execute flag)")
        sys.exit(1)