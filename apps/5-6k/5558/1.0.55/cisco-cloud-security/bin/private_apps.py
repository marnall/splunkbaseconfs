# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath

sys.path.append(dirname(abspath(__file__)))

from datetime import datetime
import time
import json
import splunklib.client as client
import splunk.rest as rest
from splunklib.modularinput import *
from validator import cummulative_validator
from logger import Logger
from exceptions import PrivateResourcesAPIClientException
from service.app_kvstore_service import KVStoreService
from typing import List, Dict


class MyScript(Script):
    def __init__(self):
        super().__init__()
        self.org_id = None


    def get_scheme(self):
        scheme = Scheme("Private Apps")
        scheme.description = "Private Apps Details"
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        argument = Argument(
            "Log_Level", description="Setting the Log Level", required_on_create=True
        )
        scheme.add_argument(argument)
        argument = Argument(
            "org_id", description="Organization ID", required_on_create=True
        )
        scheme.add_argument(argument)
        return scheme

    def validate_input(self, validation_definition):
        Log_level = validation_definition.parameters["Log_Level"]
        if not cummulative_validator(Log_level):
            raise Exception("Enter Valid Modular Input Argument")
        if not Log_level:
            raise ValueError("Log Level must not be null.")

        org_id = validation_definition.parameters["org_id"]
        if not cummulative_validator(org_id):
            raise Exception("Enter Valid Modular Input Argument")
        if not org_id:
            raise ValueError("org_id must not be null.")

    def filter_event(self, timestamp: str, data: List[Dict]):
        if not data:
            return ""
        content = ''
        for item in data:
            result = ",".join(map(lambda value: f'"{value}"', item.values()))
            content += f'"{timestamp}",{result},"{self.org_id}"\n' # append org_id
        return content

    def event_writer(self, ew, session_token, input_name, interval):
        endpoint = self._get_http_request_endpoint(interval)
        page = 1
        lines_processed = 0
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        while True:
            try:
                private_app_data = self._send_request(
                    endpoint=endpoint.format(page=page), session_token=session_token
                )
                if not private_app_data:
                    break
                filtered_data = self.filter_event(timestamp, private_app_data)
                event = Event(
                    source="cloud_security_privateapps",
                    sourcetype="cisco:cloud_security:privateapps",
                    stanza=input_name,
                    data=filtered_data,
                )
                ew.write_event(event)
                lines_processed += filtered_data.count("\n")
                time.sleep(2)
                page += 1
            except Exception as e:
                break
        Logger().info(f"MI: Private_apps: lines_processed: {lines_processed}")

    def stream_events(self, inputs, ew):
        try:
            session_token = inputs.metadata["session_key"]
            index = list(inputs.inputs.items())[0][1]["index"]
            interval = int(list(inputs.inputs.items())[0][1]["interval"])
            self.org_id = list(inputs.inputs.items())[0][1]["org_id"]
            if not self._is_index_configured(index):
                raise PrivateResourcesAPIClientException(
                    error_code=400,
                    error_msg="Please configure the index for Private Applications.",
                )
            if index not in self._get_existing_indexes(session_token):
                raise PrivateResourcesAPIClientException(
                    error_code=400, error_msg="Configured index not Found."
                )
            self._update_kvstore_index(index, session_token)
            input_name = list(inputs.inputs.items())[0][0]
            if not cummulative_validator(input_name):
                raise Exception("input_name validation failed")
            self.event_writer(ew, session_token, input_name, interval)
        except PrivateResourcesAPIClientException as e:
            Logger().error(f"MI: Private_apps, Exception: {e.error_msg}")
        except Exception as e:
            Logger().error("MI: Private_apps, Exception: {0}".format(str(e)))

    def _send_request(self, endpoint: str, session_token: str):
        request_url = f"/servicesNS/nobody/cisco-cloud-security/{endpoint}"
        _, content = rest.simpleRequest(
            request_url, sessionKey=session_token, method="GET", raiseAllErrors=True
        )
        return json.loads(content)

    def _get_http_request_endpoint(self, interval: int) -> str:
        to_timestamp = int(time.time() * 1000)
        from_timestamp = to_timestamp - (interval * 1000)
        endpoint = f"private_resources?request_for=table&query=getTableData&from={str(from_timestamp)}&to={str(to_timestamp)}&orgId={self.org_id}&limit=100&page={{page}}"
        return endpoint

    def _is_index_configured(self, index: str) -> bool:
        return index != "default"

    def _get_existing_indexes(self, session_token: str) -> bool:
        splunkservice = client.connect(host="localhost", token=session_token)
        indexes = splunkservice.indexes
        return [ele.name for ele in indexes]

    def _update_kvstore_index(self, index: str, session_token: str) -> None:
        privateapp_index = KVStoreService("privateapp_index", session_token)
        privateapp_index_pre_value = json.loads(
            privateapp_index.query_items("privateapp_index", session_token)
        )
        if len(privateapp_index_pre_value) != 0:
            privateapp_index_pre_record = privateapp_index_pre_value[-1]
            key = privateapp_index_pre_record["_key"]
            privateapp_index.update_item_by_key(
                "privateapp_index", key, session_token, {"index": index, "orgId": self.org_id}
            )
        else:
            privateapp_index.insert_record(
                "privateapp_index", session_token, {"index": index, "orgId": self.org_id}
            )


if __name__ == "__main__":
    Logger().info("MI: Private_apps: execution started")
    sys.exit(MyScript().run(sys.argv))
    Logger().info("MI: Private_apps: execution completed")
