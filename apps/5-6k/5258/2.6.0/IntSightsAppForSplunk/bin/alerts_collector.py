import time
import json
from datetime import datetime, timedelta
from base64 import b64encode

import intsights_utils as int_utils
from api_client import APIClient

START_DATE_MAPPING = {
    "last_day": 1,
    "last_week": 7,
    "last_30_days": 30,
    "last_90_days": 90,
    "last_180_days": 180
}


ALERT_SYS_MODULE_KEY = "Discovery"
ALERTS_LIST_ENDPOINT = "/alerts/list"
ALERT_DETAILS_ENDPOINT = "/alerts/complete-alert/{}"
ALERT_ASSIGNEE_DETAILS_LIST = "/account/users-details"
SYNC_ALERT_REPORT_ENDPOINT = "/public/v1/apps/splunk/alerts/sync-report"
SMALL_CHUNK = 500


class AlertsCollector(object):
    """The purpose of AlertsCollector is to fetch the alerts from Intsights, and index them into splunk."""

    def __init__(self, helper, ew):
        """Initializing values."""
        self.helper = helper
        self.event_writer = ew
        self.session_key = self.helper.context_meta["session_key"]
        self.api_client = APIClient(self.session_key, self.helper.logger)
        self.proxies = int_utils.get_proxy_info(self.session_key)
        self.input_name = self.helper.get_input_stanza_names() + '_alerts'
        self.name_of_input = self.helper.get_input_stanza_names()
        self.encoded_cred = b64encode("{}:{}".format(self.api_client.account.get("account_id"),
                                                     self.api_client.account.get("api_key")).encode()).decode()
        self.header = {
            "Content-type": "application/json",
            "Accept": "application/json",
            "Authorization": "Basic {}".format(self.encoded_cred)}

    def _feed_alert_report_to_server(self, start_time, end_time, total_alerts, count_by_severity, severity_list):
        """Sending alert report to the server."""
        count_by_severity = {k.lower(): v for k, v in count_by_severity.items()}
        sync_json = {
            "syncId": self.api_client.sync_id,
            "lastSyncCompletedTime": end_time,
            "lastSyncAlerts": total_alerts,
            "totalAlerts": count_by_severity,
            "lastSyncFilter": {
                "lastUpdated": {
                    "from": start_time,
                    "to": end_time
                },
                "severity": severity_list
            }
        }
        int_utils.feed_report_to_server(
            self.helper, self.api_client.account, self.proxies,
            self.header, SYNC_ALERT_REPORT_ENDPOINT, sync_json
        )

    def _get_payload_severity_list(self, start_time, end_time):
        """Build payload and severity_list for data collection logic.

        :param start_time (str): starting date and time from which to collect alerts
        :param end_time (str): ending date and time till which to collect alerts

        :return: Payload
        :return: severity_list
        """
        payload = {
            'syncId': self.api_client.sync_id, 'lastUpdatedFrom': start_time,
            'lastUpdatedTo': end_time, 'limit': int_utils.LIMIT
        }
        alert_severity = self.helper.get_arg('alert_severity')
        alert_type = self.helper.get_arg('alert_type')
        alert_status = self.helper.get_arg('alert_status')
        if "All" in alert_severity:
            payload.update({'severity[]': ['High', 'Low', 'Medium']})
            severity_list = ['High', 'Low', 'Medium']
        else:
            payload.update({'severity[]': alert_severity})
            severity_list = alert_severity
        if "All" in alert_type:
            payload.update({'alertType[]': ['AttackIndication', 'DataLeakage',
                            'Phishing', 'BrandSecurity', 'ExploitableData', 'vip']})
        else:
            payload.update({'alertType[]': alert_type})
        if alert_status == "close":
            payload.update({'isClosed': 'true'})
        else:
            payload.update({'isClosed': 'false'})
        return payload, severity_list

    def _get_alert_details(self, alerts_list, count_by_severity):
        """Fetch details of each alert and index into Splunk."""
        count = 0
        prev_alert_id = None
        prev_update_date = None
        payload = {'syncId': self.api_client.sync_id}
        for alert in alerts_list.get("content"):
            alert_id = alert['_id'].strip()
            try:
                # Get the alert details for given alert id
                response = self.api_client.get_input_response(ALERT_DETAILS_ENDPOINT.format(alert_id),
                                                              payload, input_type="alert details")
                alert_details = json.loads(response.content)
                alert_details = alert_details.get("content")
                assignee_list = []
                # Get the assignee name for each assignee id and add to event
                for assignee_id in alert_details.get('assignees'):
                    assignee_payload = {'syncId': self.api_client.sync_id, 'userId': assignee_id.strip()}
                    response = self.api_client.get_input_response(ALERT_ASSIGNEE_DETAILS_LIST,
                                                                  assignee_payload, input_type="assignee details")
                    assignee = json.loads(response.content)
                    assignee = assignee[0]
                    assignee_list.append({
                        'AssigneeId': assignee_id,
                        'AssigneeName': "{} {}".format(assignee.get('FirstName'), assignee.get('LastName'))
                    })
                alert_details['assignees'] = assignee_list
            except Exception as exp:
                # In case of some exception, the checkpoint value is saved and then break from loop.
                if (prev_alert_id and prev_update_date):
                    checkpoint = self.helper.get_check_point(self.input_name) or {}
                    checkpoint.update({'offset': '{}::{}'.format(prev_update_date, prev_alert_id)})
                    self.helper.save_check_point(self.input_name, checkpoint)
                self.helper.log_info("input_name = {} | collected {} alerts into Splunk"
                                     .format(self.name_of_input, count))
                raise exp
            prev_alert_id = alert_id
            prev_update_date = alert['updateDate'].strip()
            event = self.helper.new_event(
                source=self.helper.get_input_type(),
                index=self.helper.get_output_index(),
                sourcetype=self.helper.get_sourcetype(),
                time=time.time(),
                data=json.dumps(alert_details, ensure_ascii=False),
            )
            self.event_writer.write_event(event)
            count = count + 1
            if count % SMALL_CHUNK == 0:
                checkpoint = self.helper.get_check_point(self.input_name) or {}
                checkpoint.update({'offset': '{}::{}'.format(prev_update_date, prev_alert_id)})
                self.helper.save_check_point(self.input_name, checkpoint)
                self.helper.log_info("input_name = {} | collected {} alerts into Splunk"
                                     .format(self.name_of_input, SMALL_CHUNK))
            count_by_severity[alert_details["details"]["severity"]] += 1
        return count

    def _get_alerts(self, start_time, end_time):
        """Fetch alert data and index to splunk.

        :param start_time (str): starting date and time from which to cllect alerts
        :param end_time (str): ending date and time till which to cllect alerts
        """
        payload, severity_list = self._get_payload_severity_list(start_time, end_time)
        offset = True
        total_alerts = 0
        count_by_severity = {
            "High": 0,
            "Low": 0,
            "Medium": 0
        }

        try:
            while (offset):
                checkpoint = self.helper.get_check_point(self.input_name) or {}
                if checkpoint.get('offset'):
                    payload.update({'offset': checkpoint.get('offset')})
                # Get list of alert ids
                response = self.api_client.get_input_response(ALERTS_LIST_ENDPOINT, payload, input_type="alerts list")
                alerts_list = json.loads(response.content)
                total_alerts += self._get_alert_details(alerts_list, count_by_severity)
                offset = alerts_list.get("nextOffset")
                checkpoint.update({'offset': offset})
                self.helper.save_check_point(self.input_name, checkpoint)
                self.helper.log_info("input_name = {} | collected {} alerts into Splunk"
                                     .format(self.name_of_input, len(alerts_list.get("content"))))
            checkpoint.update({'last_updated_time': end_time})
            checkpoint.pop('offset')
            self.helper.save_check_point(self.input_name, checkpoint)
            self._feed_alert_report_to_server(start_time, end_time, total_alerts, count_by_severity, severity_list)
            self.helper.log_info("input_name = {} | Total Alerts collected : {}"
                                 .format(self.name_of_input, total_alerts))
            self.helper.log_info("input_name = {} | Data collection is over from {} to {}"
                                 .format(self.name_of_input, start_time, end_time))
        except Exception as e:
            self.helper.log_error("input_name = {} | Error occurred while collecting alerts: {}"
                                  .format(self.name_of_input, e))

    def collect_events(self):
        """Collect alerts based on given filters."""
        self.helper.log_info("input_name = {} | Starting data collection......".format(self.name_of_input))
        try:
            # Verifying credentials
            int_utils.verify_authentication(self.api_client.account, self.proxies)
        except Exception as e:
            self.helper.log_error("input_name = {} | Error ocurred while authentication : {}"
                                  .format(self.name_of_input, e))
            return
        try:
            # Checking the Alerts enable is on system-modules
            discovery = int_utils.is_system_module_enable(
                self.helper, self.api_client.account,
                self.proxies, self.api_client.sync_id, self.encoded_cred, self.header, ALERT_SYS_MODULE_KEY
            )
            if not discovery:
                self.helper.log_warning("input_name = {} | Discovery is not enabled to collect Alerts into Splunk"
                                        .format(self.name_of_input))
                return
            self.helper.log_info("input_name = {} | Discovery is enabled to collect Alerts into Splunk"
                                 .format(self.name_of_input))
        except Exception as e:
            self.helper.log_error("input_name = {} | Error : {}".format(self.name_of_input, e))
            return
        delta_days = START_DATE_MAPPING.get(self.helper.get_arg("report_date"))
        start_date = (datetime.utcnow() - timedelta(days=delta_days)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        end_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        checkpoint = self.helper.get_check_point(self.input_name) or {}
        if not checkpoint.get('last_updated_time'):
            checkpoint.update({'last_updated_time': start_date})
            self.helper.save_check_point(self.input_name, checkpoint)
        start_date = checkpoint.get('last_updated_time')
        start_date = int_utils.get_start_date(self.helper, start_date, "_alerts")
        self._get_alerts(start_date, end_time)
