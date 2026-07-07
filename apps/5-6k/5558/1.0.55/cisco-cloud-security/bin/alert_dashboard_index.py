# encoding = utf-8
"""
Alerts Modular Input - Fetches alerts from Cisco Secure Access API and indexes them in Splunk
"""

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

from datetime import datetime, timedelta
import time
import json
import urllib.parse
import splunklib.client as client
from splunklib.modularinput import *
from validator import cummulative_validator
from logger import Logger
from reporting_api_client import ReportingAPIClient
from enums import AlertingAPIEndpoints, ALERT_SEVERITY_LABEL_MAP, ALERT_STATUS_LABEL_MAP
from exceptions import AlertsException, ReportingAPIClientException
from service.app_kvstore_service import KVStoreService

alerts_index = None


class AlertDashboardIndexScript(Script):
    """Alerts Modular Input Script"""

    def __init__(self):
        super().__init__()
        self.org_id = None
        self._logger = Logger()

    def get_scheme(self):
        """Define the modular input scheme"""
        scheme = Scheme("Alert_Dashboard_Index")
        scheme.description = "Fetches alerts from Cisco Secure Access and indexes them in Splunk"
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
        
        argument = Argument("time_window",
                            description="Time window in hours (default: 4)",
                            required_on_create=False)
        scheme.add_argument(argument)
        
        return scheme

    def validate_input(self, validation_definition):
        """Validate modular input parameters"""
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
        """Send GET request to the Alerts API"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'
        }
        api_client = ReportingAPIClient(session_token, org_id=self.org_id)
        try:
            endpoint_response = api_client.send_request(path=path, method='get', headers=headers)
        except ReportingAPIClientException as e:
            if 'Max retries exceeded' in str(e.error_msg):
                time.sleep(1)
                try:
                    endpoint_response = api_client.send_request(path=path, method='get', headers=headers)
                except ReportingAPIClientException as e:
                    raise AlertsException(error_code=e.error_code, error_msg=str(e.error_msg))
            else:
                raise AlertsException(error_code=e.error_code, error_msg=str(e.error_msg))
        except Exception as e:
            raise AlertsException(error_code=400, error_msg=str(e))
        return endpoint_response.json()

    def calculate_from_date(self, time_window_hours):
        """Calculate the start date based on time window"""
        from_date = datetime.utcnow() - timedelta(hours=int(time_window_hours))
        return from_date.strftime("%Y-%m-%d %H:%M:%S")
    
    def calculate_to_date(self):
        """Calculate the end date (current time)"""
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    def build_modified_at_filter(self, from_date):
        """Build modified_at filter JSON for API - captures new alerts and status changes"""
        filters = {
            'modified_at': from_date
        }
        return urllib.parse.quote(json.dumps(filters))

    def get_severity_label(self, severity_code):
        """Map severity code to label"""
        return ALERT_SEVERITY_LABEL_MAP.get(severity_code, "Unknown")

    def get_status_label(self, status_code):
        """Map status code to label"""
        return ALERT_STATUS_LABEL_MAP.get(status_code, "Unknown")

    def filter_event_json(self, alert):
        """
        Transform alert data into JSON format for indexing
        Fields match actual API response from Cisco Alerting API v2
        Returns: JSON formatted string
        """
        event_data = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "alertId": alert.get('alertId', ''),
            "name": alert.get('name', ''),
            "severity": alert.get('severity', 0),
            "severityLabel": self.get_severity_label(alert.get('severity', 0)),
            "status": alert.get('status', 0),
            "statusLabel": self.get_status_label(alert.get('status', 0)),
            "createdAt": alert.get('created_at', ''),
            "modifiedAt": alert.get('modified_at', ''),
            "ruleId": alert.get('rule_id', ''),
            "ruleTypeId": alert.get('rule_type_id', ''),
            "description": alert.get('description', ''),
            "organizationId": alert.get('organization_id', self.org_id)
        }
        return json.dumps(event_data)

    def event_writer(self, ew, session_token, input_name, time_window, last_run_time=None):
        """Fetch alerts and write events to Splunk index"""
        limit = 100
        offset = 0
        total_indexed = 0
        
        # Use checkpoint if available, otherwise use time_window for first run
        if last_run_time:
            from_date = last_run_time
        else:
            from_date = self.calculate_from_date(time_window)        
        to_date = self.calculate_to_date()
        filters_param = self.build_modified_at_filter(from_date)
        
        while True:
            path = AlertingAPIEndpoints.LIST_ALERTS.value.format(self.org_id, limit, offset)
            path += f"&filters={filters_param}"
            
            response = self.send_request(session_token, path)
            
            alerts_list = response.get('alerts', response.get('items', []))
            
            if not alerts_list:
                break
            
            for alert in alerts_list:
                event_data = self.filter_event_json(alert)
                
                event = Event(
                    source="cloud_security_alerts",
                    sourcetype="cisco:cloud_security:alerts",
                    stanza=input_name,
                    data=event_data
                )
                
                try:
                    ew.write_event(event)
                    total_indexed += 1
                except Exception as e:
                    self._logger.error(f"MI: Alerts: Exception writing event: {str(e)}")
                    raise AlertsException(error_code=400, error_msg=str(e))
            
            if len(alerts_list) < limit:
                break
            
            offset += limit
        
        self._logger.info(f"MI: Alerts: Total alerts indexed: {total_indexed}")
        return to_date

    def stream_events(self, inputs, ew):
        """Main entry point for modular input execution"""
        global alerts_index
        
        try:
            session_token = inputs.metadata["session_key"]
            input_item = list(inputs.inputs.items())[0]
            input_name, input_config = input_item[0], input_item[1]
            
            index = input_config['index']
            self.org_id = input_config['org_id']
            time_window = input_config.get('time_window') or '4'
            
            if index == 'default':
                raise AlertsException(error_code=400, error_msg="Please configure the index for Alerts.")
            
            splunkservice = client.connect(host="localhost", token=session_token)
            indexes = splunkservice.indexes
            indexes = [ele.name for ele in indexes]
            if index not in indexes:
                raise AlertsException(error_code=400, error_msg="Configured index not Found.")

            if not alerts_index:
                alerts_index = KVStoreService('alerts_index', session_token)
            
            # Query existing records for this org to get last_run_time (if any)
            last_run_time = None
            if index:
                alerts_index_pre_value = json.loads(alerts_index.query_items(
                    'alerts_index', session_token, query_conditions={"orgId": self.org_id}
                ))
                if alerts_index_pre_value:
                    # Use first record's lastRunTime (should be only one per org)
                    last_run_time = alerts_index_pre_value[0].get("lastRunTime")

            if not cummulative_validator(input_name):
                raise Exception('input_name validation failed')
            
            current_run_time = self.event_writer(ew, session_token, input_name, time_window, last_run_time)

            # Upsert pattern: Delete all existing records for this org, then insert single new record
            # This prevents race condition where concurrent runs could create duplicate records
            existing_records = json.loads(alerts_index.query_items(
                'alerts_index', session_token, query_conditions={"orgId": self.org_id}
            ))
            for record in existing_records:
                alerts_index.delete_item_by_key('alerts_index', record["_key"], session_token)
            
            alerts_index.insert_record('alerts_index', session_token,
                                       {'index': index, 'orgId': self.org_id, 'lastRunTime': current_run_time})

        except AlertsException as e:
            self._logger.error(f"MI: Alerts: Exception: {e.error_msg}")
        except Exception as e:
            self._logger.error(f"MI: Alerts: Exception: {str(e)}")


if __name__ == "__main__":
    Logger().info("MI: Alerts: execution started")
    sys.exit(AlertDashboardIndexScript().run(sys.argv))
