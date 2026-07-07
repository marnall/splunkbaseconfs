import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from SplunkLogging import setup_logging

# logger = setup_logging("splunk.log")

from Constants import app_name


class SplunkSettings:

    @staticmethod
    def get_app_settings(service):
        api_url = '<not found>'
        api_key = '<not found>'
        log_level = '<not found>'
        storage_passwords = service.storage_passwords
        for credential in storage_passwords:
            if credential.content.get('realm') == app_name and credential.content.get('username') == 'x_api_key':
                api_key = credential.content.get('clear_password')
        # api_key = 'vkey1_d1896cb74f514229aef0e9a64f89d933_Uj8rq45FlQRDqS3Etso0SOt2t2bl9YyjxN1upuxYX+I='
        # api_url = 'https://dev64db9.varonis-preprod.com/'
        log_level = 'DEBUG'
        for conf in service.confs['app'].list():
            if conf.name == 'varonis_saas_api':
                api_url = conf.content.get('api_url')
                log_level = conf.content.get('log_level')
                break
        return api_url, api_key, log_level
