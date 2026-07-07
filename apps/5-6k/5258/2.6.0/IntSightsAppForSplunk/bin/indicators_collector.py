
import time
import json
from datetime import datetime, timedelta
from base64 import b64encode

import intsights_utils as int_utils
import constants as const
from api_client import APIClient

IOC_SYS_MODULE_KEY = "IOC"
IOC_LIST_ENDPOINT = "/iocs"
SYNC_IOC_REPORT_ENDPOINT = "/public/v1/apps/splunk/iocs/sync/report"


class IndicatorsCollector(object):
    """The purpose of IndicatorsCollector is to fetch the Iocs from Intsights, and index them into splunk."""

    def __init__(self, helper, ew):
        """Initializing values."""
        self.helper = helper
        self.event_writer = ew
        self.session_key = self.helper.context_meta["session_key"]
        self.api_client = APIClient(self.session_key, self.helper.logger)
        self.proxies = int_utils.get_proxy_info(self.session_key)
        self.input_name = self.helper.get_input_stanza_names() + '_ioc'
        self.name_of_input = self.helper.get_input_stanza_names()
        self.encoded_cred = b64encode("{}:{}".format(self.api_client.account.get("account_id"),
                                                     self.api_client.account.get("api_key")).encode()).decode()
        self.header = {
            "Content-type": "application/json",
            "Accept": "application/json",
            "Authorization": "Basic {}".format(self.encoded_cred)}

    def _feed_ioc_report_to_server(
        self, end_time, total_indicators,
        severity_list, feed_ids, types
    ):
        """Sending iocs report to the server."""
        for index, severity_name in enumerate(severity_list):
            severity_list[index] = severity_name.lower()
        sync_json = {
            "lastSyncIocs": total_indicators,
            "lastSyncCompletedTime": end_time,
            "totalIocs": {"feedIds": feed_ids, "types": types},
            "lastSyncFilter": {
                "lastUpdated": end_time,
                "severity": severity_list,
                "types": ["ipAddresses", "urls", "domains", "hashes", "emails"],
                "limit": int(int_utils.LIMIT),
            },
            "syncId": self.api_client.sync_id,
        }
        int_utils.feed_report_to_server(
            self.helper, self.api_client.account, self.proxies,
            self.header, SYNC_IOC_REPORT_ENDPOINT, sync_json
        )

    def _get_payload_severity_list(self, start_time, end_time):
        """Build payload and severity_list for data collection logic.

        :param start_time (str): starting date and time from which to collect iocs
        :param end_time (str): ending date and time till which to collect iocs

        :return: Payload
        :return: severity_list
        """
        reporting_feeds = self.helper.get_arg('reporting_feeds')
        all_rf = "All" in reporting_feeds
        verify_cert = const.VERIFY_SSL
        ioc_severity = self.helper.get_arg('ioc_severity')
        all_severity = "All" in ioc_severity
        ioc_type = self.helper.get_arg('ioc_type')
        all_type = "All" in ioc_type
        ioc_status = self.helper.get_arg('ioc_status')
        all_status = "All" in ioc_status
        ioc_whitelisted = self.helper.get_arg("whitelisted")
        payload = {
            'syncId': self.api_client.sync_id, 'lastUpdatedFrom': start_time,
            'lastUpdatedTo': end_time, 'limit': int_utils.IOC_LIMIT
        }
        if ioc_whitelisted == "false":
            payload.update({'whitelisted': 'false'})
        if not all_rf:
            sources = []
            # Get list of sources info if reporting_feeds filter is not All.
            sorces_info = int_utils.get_ioc_sources(
                self.header, self.proxies, self.api_client.sync_id, self.encoded_cred,
                self.api_client.account.get("server_address"), verify_cert)
            if sorces_info:
                # Get list of source ids
                for source_key in sorces_info.keys():
                    source = [source_dict["_id"]
                              for source_dict in sorces_info[source_key] if source_dict["Name"] in reporting_feeds]
                    sources = sources + source
                payload.update({'sourceIds[]': sources})
        if not all_severity:
            payload.update({'severity[]': ioc_severity})
            severity_list = ioc_severity
        else:
            severity_list = ['High', 'Low', 'Medium', 'PendingEnrichment']
        if not all_type:
            payload.update({'type[]': ioc_type})
        if not all_status:
            payload.update({'status': ioc_status})

        return payload, severity_list

    def _get_iocs(self, start_time, end_time):
        """Fetch IOCs data and index to splunk.

        :param start_time (str): starting date and time from which to collect IOcs
        :param end_time (str): ending date and time till which to collect IOCs
        """
        payload, severity_list = self._get_payload_severity_list(start_time, end_time)
        feed_id_data = {
            "id": 0,
            "totals": {
                "ipAddresses": 0,
                "domains": 0,
                "emails": 0,
                "urls": 0,
                "hashes": 0
            }
        }
        types = {
            "ipAddresses": 0,
            "domains": 0,
            "emails": 0,
            "urls": 0,
            "hashes": 0
        }
        feed_ids = []
        total_indicators = 0
        offset = True
        try:
            while (offset):
                checkpoint = self.helper.get_check_point(self.input_name) or {}
                if checkpoint.get('offset'):
                    payload.update({'offset': checkpoint.get('offset')})
                response = self.api_client.get_input_response(IOC_LIST_ENDPOINT, payload, input_type="iocs")
                indicators = json.loads(response.content)
                for indicator in indicators.get("content"):
                    indicator['value'] = indicator['value'].strip()
                    event = self.helper.new_event(
                        source=self.helper.get_input_type(),
                        index=self.helper.get_output_index(),
                        sourcetype=self.helper.get_sourcetype(),
                        time=time.time(),
                        data=json.dumps(indicator, ensure_ascii=False),
                    )
                    self.event_writer.write_event(event)
                    sync_type = indicator['type'][0].lower() + indicator['type'][1:]
                    types[sync_type] = types[indicator['type'][0].lower() + indicator['type'][1:]] + 1
                    feed_id_list = []
                    for feed_source_id in indicator['reportedFeeds']:
                        feed_id_data['id'] = feed_source_id['id']
                        feed_id_list.append(feed_id_data)

                    for feed_id_list_data in feed_id_list:
                        count = 0
                        for feed_id in feed_ids:
                            if feed_id.get('id') == feed_id_list_data.get('id'):
                                feed_id['totals'][sync_type] = feed_id['totals'][sync_type] + 1
                                count = count + 1
                                break
                        if count == 0:
                            feed_id_list_data['totals'][sync_type] = feed_id_list_data['totals'][sync_type] + 1
                            feed_ids.append(feed_id_list_data)
                offset = indicators.get("nextOffset")
                checkpoint.update({'offset': offset})
                total_indicators = total_indicators + len(indicators.get("content"))
                self.helper.save_check_point(self.input_name, checkpoint)
                self.helper.log_info("input_name = {} | collected {} Iocs into Splunk"
                                     .format(self.name_of_input, len(indicators.get("content"))))
            checkpoint.update({'last_updated_time': end_time})
            checkpoint.pop('offset')
            self.helper.save_check_point(self.input_name, checkpoint)
            self._feed_ioc_report_to_server(end_time, total_indicators, severity_list, feed_ids, types)
            self.helper.log_info("input_name = {} | Total iocs collected : {}"
                                 .format(self.name_of_input, total_indicators))
            self.helper.log_info("input_name = {} | Data collection is over from {} to {}"
                                 .format(self.name_of_input, start_time, end_time))
        except Exception as e:
            self.helper.log_error("input_name = {} | Error occurred while collecting iocs: {}"
                                  .format(self.name_of_input, e))

    def collect_events(self):
        """Collect Indicators based on given filters."""
        self.helper.log_info("input_name = {} | Starting data collection......".format(self.name_of_input))
        start_date = self.helper.get_arg("start_date") or (
            datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.%f")
        start_date = start_date + "Z"
        end_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
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
        if self.helper.get_arg("whitelisted") == "false":
            self.helper.log_info("input_name = {} | Collecting only Non-whitelisted IOCs.".format(self.name_of_input))
        else:
            self.helper.log_info("input_name = {} | Collecting both Whitelisted and Non-whitelisted IOCs."
                                 .format(self.name_of_input))
        try:
            # Checking the IOCs is enabled on system-modules
            ioc_enable = int_utils.is_system_module_enable(
                self.helper, self.api_client.account,
                self.proxies, self.api_client.sync_id, self.encoded_cred, self.header, IOC_SYS_MODULE_KEY
            )
            if not ioc_enable:
                self.helper.log_warning("input_name = {} | IOCs is not enabled to collect data into Splunk"
                                        .format(self.name_of_input))
                return
            self.helper.log_info("input_name = {} | IOCs is enabled to collect data into Splunk"
                                 .format(self.name_of_input))
        except Exception as e:
            self.helper.log_error("input_name = {} | Error : {}".format(self.name_of_input, e))
            return
        start_date = int_utils.get_start_date(self.helper, start_date, "_ioc")
        self._get_iocs(start_date, end_time)
