# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

from datetime import datetime
import json
import requests
import validator
from splunklib.modularinput import *
from service.app_kvstore_service import KVStoreService
from logger import Logger
from token_service import TokenService

cloudlock_settings = None
kv_health_check_cloudlock = None

class MyScript(Script):
    def get_scheme(self):
        scheme = Scheme("CASB Health Check Status")
        scheme.description = "Cloudlock Inspect Health Status"
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        argument = Argument("Log_Level",
                            description="Setting the Log Level",
                            required_on_create=True)
        scheme.add_argument(argument)
        return scheme

    def validate_input(self, validation_definition):
        Log_level = validation_definition.parameters["Log_Level"]
        if not validator.cummulative_validator(Log_level):
            raise Exception('Enter Valid Modular Input Argument')
        if not Log_level:
            raise ValueError("Log Level must not be null.")

    def getStatusAndInvocationDate(self, url, token):
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token,
                    'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
        endpoint_response = requests.get(url + '/incidents?order=created_at&limit=1&count_total=false', headers=headers)
        response_time = endpoint_response.elapsed.total_seconds()
        return (endpoint_response.status_code, str(datetime.now()), response_time)

    # def pretty(self, response):
    #     reader = results.ResultsReader(response)
    #     for result in reader:
    #         return result

    def stream_events(self, inputs, ew):
        date_cloudlock = None
        cloudlock_res = None
        diff_cloudlock = 0
        cloudlocktoken = None
        cloudlockURL = None
        headers = None
        try:
            session_token = inputs.metadata["session_key"]
            header = inputs.metadata.get('server_host', [])
            host = header.lower() if header else "localhost"
            global cloudlock_settings
            if cloudlock_settings is None:
                cloudlock_settings = KVStoreService('cloudlock_settings', session_token)
            cloudlock_settings_data = json.loads(cloudlock_settings.query_items('cloudlock_settings', session_token))
            
            if len(cloudlock_settings_data)==0:
                raise Exception('Cloudlock settings are empty')

            payload = TokenService.get_token(session_token, 'cloudlock_settings', host=host)
            if payload['payload']:
                cloudlocktoken = payload['payload']['clear_token']
            else:
                raise Exception('Cloudlock settings are empty')
            for obj in cloudlock_settings_data:
                if obj['status'] == 'active':
                    cloudlockURL = obj['url']
                    headers = {'Authorization': 'Bearer ' + str(cloudlocktoken),
                               'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
                    break
                else:
                    continue
            
            if not cloudlocktoken and not cloudlockURL and not headers:
                raise Exception('Cloudlock Credentials not active')
            
            cld_tup = self.getStatusAndInvocationDate(cloudlockURL, cloudlocktoken)
            cloudlockURLStatus = cld_tup[0]
            cld_exec_date = cld_tup[1]
            cloudlock_api_response_time = cld_tup[2]
            
            global kv_health_check_cloudlock
            if kv_health_check_cloudlock is None:
                kv_health_check_cloudlock = KVStoreService('cloudlock_health_check', session_token)
            
            cloudlock_res = json.loads(kv_health_check_cloudlock.query_items('cloudlock_health_check', session_token))
            if len(cloudlock_res) != 0:
                date_cloudlock = cloudlock_res[-1]["cloudlockLastInvocationDate"]
                formatted_date_cloudlock = datetime.strptime(date_cloudlock, "%Y-%m-%d %H:%M:%S.%f")
                diff_cloudlock = int((datetime.now() - formatted_date_cloudlock).days)
                if diff_cloudlock > 30:
                    del_cloudlock = kv_health_check_cloudlock.delete_all_items('cloudlock_health_check', session_token)
            insert_cloudlock = kv_health_check_cloudlock.insert_record('cloudlock_health_check', session_token,
                                                                       {'cloudlockURL': str(cloudlockURL),
                                                                        'cloudlockURLStatus': str(cloudlockURLStatus),
                                                                        'cloudlockLastInvocationDate': str(cld_exec_date),
                                                                        'cloudlockResponseTime': str(
                                                                            cloudlock_api_response_time)})
        except Exception as e:
            Logger().error("MI: cloudlock_health_check, Exception : {0}".format(str(e)))


if __name__ == "__main__":
    Logger().info("MI: cloudlock_health_check : execution started")
    sys.exit(MyScript().run(sys.argv))
    Logger().info("MI: cloudlock_health_check : execution completed")
