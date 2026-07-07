# XSOAR Incident pulling Class

import requests
import sys
import os
from utils import get_app_specific_coniguration, prepare_csv_value
from constants import HOST, PORT, SYSTEM_TOKEN_CONF_DETAILS, CORTEX_XSOAR_ANALYTICS_CONF_DETAILS

lib_path = os.path.abspath('./aob_py3')
if lib_path not in sys.path:
    sys.path.append(lib_path)

import splunklib.client as client

class XSOAR(object):
    def __init__(self):
        self.get_api_credentials()
        self.verify_ssl = get_app_specific_coniguration(CORTEX_XSOAR_ANALYTICS_CONF_DETAILS)

    def get_api_credentials(self):
        try:
            service = client.connect(
                host=HOST,
                port=PORT,
                splunkToken=get_app_specific_coniguration(SYSTEM_TOKEN_CONF_DETAILS)
                )
        except Exception as e:
            print("Error Message")
            error_text = prepare_csv_value("An error occurred: "  + str(e))
            print(error_text)
            
        passwords = service.storage_passwords.list()
        for password in passwords:
            if password.username == 'url':
                self.api_url = password.clear_password
            elif password.username == 'api_key':
                self.api_key = password.clear_password
            else:
                pass   
    
    def payload_generation(self, 
                           widget_config = None, 
                           date_range_by_to = 'days', 
                           date_range_by_from = 'days',
                           date_range_to_value = 0, 
                           date_range_from_value = 10000,
                           query = ''):
        payload = widget_config
        payload['dateRange']['period']['byTo'] = date_range_by_to
        payload['dateRange']['period']['byFrom'] = date_range_by_from
        payload['dateRange']['period']['toValue'] = date_range_to_value
        payload['dateRange']['period']['fromValue'] = date_range_from_value
        payload['query'] = query
        self.payload = payload

    def pull_incidents(self, endpoint):
        method = 'POST'
        headers = {
            'authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        url = f'{self.api_url}/{endpoint}'
        
        response = requests.request(method, url, headers=headers, json=self.payload, verify=self.verify_ssl)

        if response.status_code == 200:
            return response.json()
        else:
            print("Error Message")
            print(f"{response.raise_for_status()}")
            sys.exit()
