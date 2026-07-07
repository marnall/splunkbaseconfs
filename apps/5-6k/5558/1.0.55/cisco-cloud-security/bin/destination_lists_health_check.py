# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

from datetime import datetime
import json
from splunklib.modularinput import *
from service.app_kvstore_service import KVStoreService
from validator import cummulative_validator
from logger import Logger
from reporting_api_client import ReportingAPIClient
from enums import DestinationListAPIEndpoints
from exceptions import DestinationListHealthException

oauth_settings = None
destination_lists_health_check = None

class MyScript(Script):
    def get_scheme(self):
        scheme = Scheme("Destination Lists Health Check Status")
        scheme.description = "Inspect Destination Lists Health Status"
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        argument = Argument("Log_Level",
                            description="Setting the Log Level",
                            required_on_create=True)
        scheme.add_argument(argument)
        return scheme

    def validate_input(self, validation_definition):
        Log_level = validation_definition.parameters["Log_Level"]
        if not cummulative_validator(Log_level):
            raise Exception('Enter Valid Modular Input Argument')
        if not Log_level:
            raise ValueError("Log Level must not be null.")

    def getStatusAndInvocationDate(self, session_token):
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json',
                   'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
        api_client = ReportingAPIClient(session_token)
        path = DestinationListAPIEndpoints.GET_DESTINATION_LISTS.value
        endpoint_response = api_client.send_request(path=path, method='get', headers=headers)
        response_time = endpoint_response.elapsed.total_seconds()
        return (endpoint_response.status_code, str(datetime.now()), response_time)

    def stream_events(self, inputs, ew):
        date_destination_lists = None
        diff_destination_lists = 0
        # destinationListsToken = None
        # destinationListsURL = None
        # destinationListsOrgId = None
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
                    raise DestinationListHealthException(error_code=400, error_msg="oauth settings are not configured.")
                for obj in oauth_settings:
                    if obj['status'] == 'active':
                        base_url = obj['baseURL']
                        break
            if not base_url:
                raise DestinationListHealthException(error_code=400, error_msg="oauth settings are not configured.")
                
            dest_tup = self.getStatusAndInvocationDate(session_token)
            destinationListsURLStatus = dest_tup[0]
            destinationLists_exec_date = dest_tup[1]
            destinationLists_api_response_time = dest_tup[2]

            global destination_lists_health_check
            if not destination_lists_health_check:
                destination_lists_health_check = KVStoreService('destination_lists_health_check', session_token)

            destination_lists_health_check_res = json.loads(destination_lists_health_check.query_items('destination_lists_health_check', session_token))

            if len(destination_lists_health_check_res) != 0:
                date_destination_lists = destination_lists_health_check_res[-1]["destinationListsLastInvocationDate"] 
                formatted_date_destination_lists = datetime.strptime(date_destination_lists, "%Y-%m-%d %H:%M:%S.%f")
                diff_destination_lists = int((datetime.now() - formatted_date_destination_lists).days)
                if diff_destination_lists > 30:
                    del_destination_lists = destination_lists_health_check.delete_all_items('destination_lists_health_check', session_token)
            insert_destination_lists = destination_lists_health_check.insert_record('destination_lists_health_check',
                                        session_token,
                                        {'destinationListsURL': str(base_url),
                                        'destinationListsURLStatus': str(destinationListsURLStatus),
                                        'destinationListsLastInvocationDate': str(destinationLists_exec_date),
                                        'destinationListsResponseTime': str(destinationLists_api_response_time)})
        except DestinationListHealthException as e:
            Logger().error(f"MI: destination_lists_health_check, Exception :{e.error_msg}")
        except Exception as e:
            Logger().error("MI: destination_lists_health_check, Exception : {0}".format(str(e)))

if __name__ == "__main__":
    Logger().info("MI: destination_lists_health_check : execution started")
    sys.exit(MyScript().run(sys.argv))
    Logger().info("MI: destination_lists_health_check : execution completed")
