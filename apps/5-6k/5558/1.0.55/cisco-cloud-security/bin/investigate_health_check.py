# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

from datetime import datetime
import json
from splunklib.modularinput import *
from service.app_kvstore_service import KVStoreService
import validator
from reporting_api_client import ReportingAPIClient
from logger import Logger
from enums import InvestigateAPIS
from exceptions import InvestigateListHealthException

oauth_settings = None
kv_health_check_investigate = None

class MyScript(Script):
    def get_scheme(self):
        scheme = Scheme("Investigate Health Check Status")
        scheme.description = "Inspect Investigate Health Status"
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

    def getStatusAndInvocationDate(self, session_token):
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json',
                   'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
        api_client = ReportingAPIClient(session_token)
        path = InvestigateAPIS.TOP_MILLION.value
        endpoint_response = api_client.send_request(path=path, method='get', headers=headers)
        response_time = endpoint_response.elapsed.total_seconds()
        return (endpoint_response.status_code, datetime.now(), response_time)


    def stream_events(self, inputs, ew):
        date_investigate = None
        investigate_res = None
        diff_investigate = 0
        try:
            session_token = inputs.metadata["session_key"]
            header = inputs.metadata.get('server_host', [])
            host = header.lower() if header else "localhost"
            global oauth_settings
            if not oauth_settings:
                oauth_settings = KVStoreService('oauth_settings', session_token)
                oauth_settings = json.loads(oauth_settings.query_items('oauth_settings', session_token))
                if len(oauth_settings) == 0:
                    Logger().error("Message: oauth settings are not configured")
                    raise InvestigateListHealthException(error_code=400, error_msg="oauth settings are not configured.")
                for obj in oauth_settings:
                    if obj['status'] == 'active':
                        base_url = obj['baseURL']
                        break
            if not base_url:
                raise InvestigateListHealthException(error_code=400, error_msg="oauth settings are not configured.")
            
            invest_tup = self.getStatusAndInvocationDate(session_token)
            investigateURLStatus = invest_tup[0]
            invest_exec_date = invest_tup[1]
            investigate_api_response_time = invest_tup[2]

            global kv_health_check_investigate
            if not kv_health_check_investigate:
                kv_health_check_investigate = KVStoreService('investigate_health_check', session_token)
            investigate_res = json.loads(kv_health_check_investigate.query_items('investigate_health_check', session_token))

            if len(investigate_res)!=0:
                date_investigate = investigate_res[-1]["investigateLastInvocationDate"]
                formatted_date_investigate = datetime.strptime(date_investigate,"%Y-%m-%d %H:%M:%S.%f")
                diff_investigate = int((datetime.now() - formatted_date_investigate).days)
                if diff_investigate > 30:
                    del_investigate = kv_health_check_investigate.delete_all_items('investigate_health_check',session_token)
            insert_investigate = kv_health_check_investigate.insert_record('investigate_health_check',
                                                                           session_token,
                                                                           {'investigateURL': str(base_url),
                                                                            'investigateURLStatus': str(
                                                                                investigateURLStatus),
                                                                            'investigateLastInvocationDate': str(
                                                                                invest_exec_date),
                                                                            'investigateResponseTime':str(investigate_api_response_time)})
        except Exception as error:
            Logger().error("MI: investigate_health_check, Exception : {0}".format(str(error)))

if __name__ == "__main__":
    Logger().info("MI: investigate_health_check : execution started")
    sys.exit(MyScript().run(sys.argv))
   
