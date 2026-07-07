import time
import json
from datetime import datetime, timedelta
from base64 import b64encode

import intsights_utils as int_utils
from api_client import APIClient


START_DATE_MAPPING = {
    "all_time": -1,
    "last_day": 1,
    "last_week": 7,
    "last_30_days": 30,
    "last_90_days": 90,
    "last_180_days": 180
}


CVE_SYS_MODULE_KEY = "Cve"
CVE_LIST_ENDPOINT = "/cves/get-cves-list"
SYNC_CVE_REPORT_ENDPOINT = "/public/v1/apps/splunk/cves/sync-report"


class VulnerabilitiesCollector(object):
    """The purpose of VulnerabilitiesCollecctor is to fetch the CVEs from Intsights, and index them into splunk."""

    def __init__(self, helper, ew):
        """Initializing values."""
        self.helper = helper
        self.event_writer = ew
        self.session_key = self.helper.context_meta["session_key"]
        self.api_client = APIClient(self.session_key, self.helper.logger)
        self.proxies = int_utils.get_proxy_info(self.session_key)
        self.input_name = self.helper.get_input_stanza_names() + '_vulnerabilities'
        self.name_of_input = self.helper.get_input_stanza_names()
        self.product_vendor_filter = self.helper.get_arg('product_vendor').strip()
        if "All" == self.product_vendor_filter:
            self.product_vendor_filter = []
        else:
            self.product_vendor_filter = int_utils.product_vendor_list_from_Filter(
                self.session_key, self.product_vendor_filter, self.helper
            )
        self.exploit_availability = self.helper.get_arg('exploit_availability')
        self.all_in_exploit_availability = False
        if self.exploit_availability == 'All':
            self.all_in_exploit_availability = True
        elif self.exploit_availability == "no":
            self.exploit_availability = False
        else:
            self.exploit_availability = True
        self.encoded_cred = b64encode("{}:{}".format(self.api_client.account.get("account_id"),
                                                     self.api_client.account.get("api_key")).encode()).decode()
        self.header = {
            "Content-type": "application/json",
            "Accept": "application/json",
            "Authorization": "Basic {}".format(self.encoded_cred)}

    def _feed_vulnerability_report_to_server(
        self, start_time, end_time,
        total_vulnerabilities, severity_list, publish_date
    ):
        """Sending vulnerabilities report to the server."""
        sync_json = {
            "syncId": self.api_client.sync_id,
            "lastSync": end_time,
            "lastSyncCompletedTime": end_time,
            "lastSyncCvesCount": total_vulnerabilities,
            "lastSyncFilter": {
                'publishDateFrom': publish_date,
                'updateDateFrom': start_time,
                'updateDateTo': end_time,
                'severity': severity_list,
            }
        }
        if not publish_date:
            del sync_json["lastSyncFilter"]['publishDateFrom']
        if not start_time:
            del sync_json["lastSyncFilter"]['updateDateFrom']
        int_utils.feed_report_to_server(
            self.helper, self.api_client.account, self.proxies,
            self.header, SYNC_CVE_REPORT_ENDPOINT, sync_json
        )

    def _get_payload_severity_list(self, publish_date, start_time, end_time):
        """Build payload and severity_list for data collection logic.

        :param start_time (str): starting date and time from which to collect Vulnerabilities
        :param end_time (str): ending date and time till which to collect vulnerabilities

        :return: Payload
        :return: severity_list
        """
        payload = {
            'syncId': self.api_client.sync_id, 'publishDateFrom': publish_date,
            'updateDateFrom': start_time, 'updateDateTo': end_time
        }
        if not publish_date:
            del payload['publishDateFrom']
        if not start_time:
            del payload['updateDateFrom']

        vulnerability_severity = self.helper.get_arg('vulnerability_severity')
        if "All" in vulnerability_severity:
            payload.update({'severity[]': ['High', 'Low', 'Medium', 'Critical']})
            severity_list = ['High', 'Low', 'Medium', 'Critical']
        else:
            payload.update({'severity[]': vulnerability_severity})
            severity_list = vulnerability_severity
        return payload, severity_list

    def _parse_vulnerability_list(self, vulnerabilities_list):
        """Parse vulnerability list into individual events to index into Splunk."""
        count = 0
        for vulnerability in vulnerabilities_list.get("content"):
            should_ingest = False  # Flag indicating if each event should or shouldn't be ingested to splunk
            # Checking
            # 1.exploit vulnerabilities is not set to all and the one in event matches the one selected by user
            # or
            # 2.exploit vulnerabilities is set to all
            if (((not self.all_in_exploit_availability)
                    and (self.exploit_availability == vulnerability["exploitAvailability"]))
                    or self.all_in_exploit_availability):
                vuln_prod_vendor_list = []
                for each in vulnerability['cpe']:
                    # creating list of product & vendor present in the event.
                    vuln_prod_vendor_list.append(each['VendorProduct'])
                if not self.product_vendor_filter:
                    should_ingest = True
                else:
                    # Checking if any one value from the user entered product and vendors is present in
                    # the product & vendor present list of the event. If so set the Flag to true
                    should_ingest = any(i in vuln_prod_vendor_list for i in self.product_vendor_filter)
            if should_ingest:
                event = self.helper.new_event(
                    source=self.helper.get_input_type(),
                    index=self.helper.get_output_index(),
                    sourcetype=self.helper.get_sourcetype(),
                    time=time.time(),
                    data=json.dumps(vulnerability, ensure_ascii=False),
                )
                self.event_writer.write_event(event)
                count = count + 1
        return count

    def _get_vulnerabilities(self, publish_date, start_time, end_time):
        """Fetch vulnerabilities data and index to splunk.

        :param publish_date (str): Publish date and time from which to collect vulnerabilities
        :param start_time (str): starting date and time from which to collect vulnerabilities
        :param end_time (str): ending date and time till which to collect vulnerabilities
        """
        payload, severity_list = self._get_payload_severity_list(publish_date, start_time, end_time)
        offset = True
        total_vulnerabilities = 0

        try:
            while (offset):
                checkpoint = self.helper.get_check_point(self.input_name) or {}
                if checkpoint.get('offset'):
                    payload.update({'offset': checkpoint.get('offset')})
                response = self.api_client.get_input_response(CVE_LIST_ENDPOINT, payload, input_type="vulnerabilities")
                vulnerabilities_list = json.loads(response.content)
                vulnerabilities_count = self._parse_vulnerability_list(vulnerabilities_list)
                total_vulnerabilities += vulnerabilities_count
                offset = vulnerabilities_list.get("nextOffset")
                checkpoint.update({'offset': offset})
                self.helper.save_check_point(self.input_name, checkpoint)
                self.helper.log_info("input_name = {} | collected {} vulnerabilities into Splunk"
                                     .format(self.name_of_input, vulnerabilities_count))

            checkpoint.update({'last_updated_time': end_time})
            checkpoint.pop('offset')
            self.helper.save_check_point(self.input_name, checkpoint)
            self._feed_vulnerability_report_to_server(start_time, end_time, total_vulnerabilities,
                                                      severity_list, publish_date)
            self.helper.log_info("input_name = {} | Total Vulnerabilities collected : {}"
                                 .format(self.name_of_input, total_vulnerabilities))
            if start_time:
                self.helper.log_info("input_name = {} | Data collection is over from {} to {}"
                                     .format(self.name_of_input, start_time, end_time))
            else:
                self.helper.log_info("input_name = {} | Data collection is over from Beginning to {}"
                                     .format(self.name_of_input, end_time))
        except Exception as e:
            self.helper.log_error("input_name = {} | Error occurred while collecting vulnerabilities: {}"
                                  .format(self.name_of_input, e))

    def collect_events(self):
        """Collect vulnerabilities based on given filters."""
        self.helper.log_info("input_name = {} | Starting data collection......".format(self.name_of_input))
        server_url = self.helper.get_global_setting("server_address")
        if not server_url:
            self.helper.log_error("input_name = {} | Server URL not found. Please check account configuration"
                                  .format(self.name_of_input))
            return
        try:
            # Verifying credentials
            int_utils.verify_authentication(self.api_client.account, self.proxies)
        except Exception as e:
            self.helper.log_error("input_name = {} | Error ocurred while authentication : {}"
                                  .format(self.name_of_input, e))
            return
        try:
            # Checking the CVE is enabled on system-modules
            cve = int_utils.is_system_module_enable(
                self.helper, self.api_client.account,
                self.proxies, self.api_client.sync_id, self.encoded_cred, self.header, CVE_SYS_MODULE_KEY
            )
            if not cve:
                self.helper.log_warning("input_name = {} | Cve is not enabled to collect vulnerabilities into Splunk"
                                        .format(self.name_of_input))
                return
            self.helper.log_info("input_name = {} | Cve is enabled to collect vulnerabilities into Splunk"
                                 .format(self.name_of_input))
        except Exception as e:
            self.helper.log_error("input_name = {} | Error : {}".format(self.name_of_input, e))
            return
        delta_days = START_DATE_MAPPING.get(self.helper.get_arg("report_date"))
        start_date = None
        publish_date = None
        if delta_days > 0:
            start_date = (datetime.utcnow() - timedelta(days=delta_days)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        end_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        checkpoint = self.helper.get_check_point(self.input_name) or {}
        if not checkpoint.get('publish_date') and delta_days > 0:
            checkpoint.update({'publish_date': start_date})
            self.helper.save_check_point(self.input_name, checkpoint)
            publish_date = checkpoint.get('publish_date')
        start_date = int_utils.get_start_date(self.helper, start_date, "_vulnerabilities")
        self._get_vulnerabilities(publish_date, start_date, end_time)
