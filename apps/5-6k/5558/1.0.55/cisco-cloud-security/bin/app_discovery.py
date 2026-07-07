# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

from datetime import datetime
import time
import json
import splunklib.client as client
from splunklib.modularinput import *
from validator import cummulative_validator
from logger import Logger
from reporting_api_client import ReportingAPIClient
from enums import AppDiscoveryAPIEndpoints
from exceptions import AppDiscoveryException, ReportingAPIClientException
from service.app_kvstore_service import KVStoreService

session_key = ''
appdiscovery_index = None

class MyScript(Script):

    def __init__(self):
        super().__init__()
        self.org_id = None

    def get_scheme(self):
        scheme = Scheme("APP Discovery")
        scheme.description = "APP Discovery Details"
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        argument = Argument("Log_Level",
                            description="Setting the Log Level",
                            required_on_create=True)
        scheme.add_argument(argument)
        argument = Argument("org_id",
                            description="Organization ID",
                            required_on_create=True)
        scheme.add_argument(argument)
        return scheme

    def validate_input(self, validation_definition):
        Log_level = validation_definition.parameters["Log_Level"]
        if not cummulative_validator(Log_level):
            raise Exception('Enter Valid Modular Input Argument')
        if not Log_level:
            raise ValueError("Log Level must not be null.")

        org_id = validation_definition.parameters["org_id"]
        if not cummulative_validator(org_id):
            raise Exception('Enter Valid Modular Input Argument')
        if not org_id:
            raise ValueError("org_id must not be null.")

    def send_request(self, session_token, path):
        headers = {'Content-Type': 'application/json',
                   'Accept':'application/json',
                   'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
        api_client = ReportingAPIClient(session_token, org_id=self.org_id)
        try:
            endpoint_response = api_client.send_request(path=path, method='get', headers=headers)
        except ReportingAPIClientException as e:
            if 'Max retries exceeded' in str(e.error_msg):
                time.sleep(1)
                try:
                    endpoint_response = api_client.send_request(path=path, method='get', headers=headers)
                except ReportingAPIClientException as e:
                    raise AppDiscoveryException(error_code=e.error_code, error_msg=str(e.error_msg))
            else:
                raise AppDiscoveryException(error_code=e.error_code, error_msg=str(e.error_msg))
        except Exception as e :
            raise AppDiscoveryException(error_code=400, error_msg=str(e))
        return endpoint_response.json()

    def get_timezone(self, session_token):
        """This method is used to fetch the timezone from kv store"""

        tz = 'UTC'
        oauth_settings = KVStoreService('oauth_settings', session_token)
        oauth_settings = json.loads(
            oauth_settings.query_items(
                "oauth_settings",
                session_token,
                query_conditions={"status": "active", "orgId": self.org_id},
            )
        )
        if len(oauth_settings) == 0:
            Logger().error("timezone setting not found!")
        else:
            oauth_settings = oauth_settings[-1]
            tz = oauth_settings['timezone']
        return tz

    def filter_event(self, rsp):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sub_category_content_type = '"'
        data = '"{0}"'.format(str(timestamp))
        for key, value in rsp.items():
            if isinstance(value, list):
                for sources in value:
                    if isinstance(sources, str):
                        sub_category_content_type += sources + ','
                        continue
                    for source_key, source_value in sources.items():
                        if source_key != 'name':
                            data += ','+ '"{0}"'.format(str(source_value))
            elif key == 'firstDetected' or key == 'lastDetected':
                data += ','+ '"{0}"'.format(str(value.replace('T', ' ')))
            else:
                data += ','+ '"{0}"'.format(str(value))
            if key == "subcategory_content_types":
                data += ','+ sub_category_content_type.rstrip(',') + '"'
        # insert org_id
        data += ','+ '"{0}"'.format(str(self.org_id))
        return data

    def event_writer(self, ew, session_token, input_name):
        app_list_count = 0
        event_count = 0
        path = AppDiscoveryAPIEndpoints.TOTAL_COUNT.value
        app_list_count = self.send_request(session_token, path)['discovered_apps_count']
        Logger().info(f"MI: App_discovery: {app_list_count} apps found.")
        limit = 100
        offset = 0
        tz = self.get_timezone(session_token)
        while offset <= app_list_count:
            path = AppDiscoveryAPIEndpoints.LIST_APPLICATIONS.value.format(limit, offset, tz, 'firstDetected', 'asc')
            try:
                app_list_data = self.send_request(session_token, path)
            except AppDiscoveryException as e:
                raise AppDiscoveryException(error_code=e.error_code, error_msg=str(e.error_msg))
            if app_list_data['items']:
                for item in app_list_data['items']:
                    event = Event(source="cloud_security_appdiscovery",
                                  sourcetype="cisco:cloud_security:appdiscovery",
                                  stanza=input_name,
                                  data=self.filter_event(item))
                    try:
                        ew.write_event(event)
                        event_count += 1
                    except Exception as e:
                        Logger().error("MI: App_discovery, Exception : {0}".format(str(e)))
                        raise AppDiscoveryException(error_code=400, error_msg=str(e))
                offset += 100
        Logger().info(f"MI: App_discovery: {event_count} apps data is written to index.")

    def stream_events(self, inputs, ew):
        global session_key
        global appdiscovery_index
        try:
            session_token = inputs.metadata["session_key"]
            index = list(inputs.inputs.items())[0][1]['index']
            self.org_id = list(inputs.inputs.items())[0][1]['org_id']
            if index == 'default':
                raise AppDiscoveryException(error_code=400, error_msg="Please configure the index for App Discovery.")
            splunkservice = client.connect(host="localhost", token=session_token)
            indexes = splunkservice.indexes
            indexes = [ele.name for ele in indexes]
            if index not in indexes:
                raise AppDiscoveryException(error_code=400, error_msg="Configured index not Found.")

            if not appdiscovery_index:
                appdiscovery_index = KVStoreService('appdiscovery_index', session_token)
            #  store the index for appdiscovery in kv store.
            if index:
                appdiscovery_index_pre_value = json.loads(appdiscovery_index.query_items('appdiscovery_index', session_token))
                if len(appdiscovery_index_pre_value) != 0:
                    appdiscovery_index_pre_record = appdiscovery_index_pre_value[-1]
                    key = appdiscovery_index_pre_record["_key"]
                    appdiscovery_index.update_item_by_key('appdiscovery_index', key, session_token,
                                                            {'index': index, 'orgId': self.org_id})
                else:
                    appdiscovery_index.insert_record('appdiscovery_index', session_token,
                                                        {'index': index, 'orgId': self.org_id})

            header = inputs.metadata.get('server_host', [])
            host = header.lower() if header else "localhost"
            input_name = list(inputs.inputs.items())[0][0]
            if not cummulative_validator(input_name):
                raise Exception('input_name validation failed')
            self.event_writer(ew, session_token, input_name)

        except AppDiscoveryException as e:
            Logger().error(f"MI: App_discovery, Exception : {e.error_msg}")
        except Exception as e:
            Logger().error("MI: App_discovery, Exception : {0}".format(str(e)))


if __name__ == "__main__":
    Logger().info("MI: App_discovery : execution started")
    sys.exit(MyScript().run(sys.argv))
    Logger().info("MI: App_discovery : execution completed")
