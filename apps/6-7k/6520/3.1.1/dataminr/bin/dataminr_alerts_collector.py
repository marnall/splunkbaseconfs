import json
import traceback
import import_declare_test    # noqa: F401
from import_declare_test import ta_name
from solnlib.modular_input.checkpointer import KVStoreCheckpointer
from datetime import datetime
from splunklib.modularinput import Event
from dataminr_client import DataminrClient, DataminrClientV4
from dataminr_utils import get_watchlist_ids
from dataminr_constants import ALL_ALERT_TYPES
from log_helper import setup_logging


class DataminrAlertsCollector:
    """Fetch the alerts from Dataminr Pulse, parse and index them into splunk."""

    DATAMINR_ALERT_URL_KEYS = ["eventMapSmallURL", "eventMapLargeURL", "expandMapURL", "relatedTermsQueryURL"]
    DATAMINR_SOURCE_SEPARATOR = "via "

    def __init__(self, inputs, event_writer):
        """Initialize an object."""
        self.ew = event_writer
        self.session_key = inputs.metadata["session_key"]
        self.input_name = list(inputs.inputs.keys())[0]
        self.input_item = inputs.inputs[self.input_name]
        self.normalized_input_name = self.input_name.split("/")[-1]
        self.logger = setup_logging(f"dataminr_api_{self.normalized_input_name}")
        self.dataminr_account = self.input_item.get("dataminr_account")
        self.list_names = self.input_item.get("lists_names")
        self.alert_types = self.input_item.get("alert_type").split(",")
        if "All" in self.alert_types:
            self.alert_types = ALL_ALERT_TYPES
        self.dataminr_client = DataminrClient(self.session_key, self.dataminr_account)
        self.checkpoint = self.initialize_checkpoint()

    def initialize_checkpoint(self):
        """Initialize an checkpoint."""
        return KVStoreCheckpointer(
            collection_name=f"{ta_name}_checkpointer",
            session_key=self.session_key,
            app=ta_name
        )

    def collect_events(self):
        """Collect events from Dataminr API and ingest."""
        self.logger.info(f"{self.normalized_input_name}|Starting data collection.")
        try:
            self.logger.info(f"{self.normalized_input_name}|Fetching watchlist Ids of configured watchlist names.")
            all_watchlists = self.dataminr_client.get_all_watchlists()
            input_watchlist_ids = get_watchlist_ids(all_watchlists, self.list_names)
            self.logger.info(f"{self.normalized_input_name}|Successfully fetched watchlist Ids.")
            self.logger.debug(f"{self.normalized_input_name}|Configured watchlist Ids={str(input_watchlist_ids)}")
            self.logger.info(f"{self.normalized_input_name}|Fetching checkpoint value.")
            current_checkpoint = self.checkpoint.get(self.normalized_input_name)
            self.logger.info(f"{self.normalized_input_name}|Successfully fetched checkpoint value.")
            total_alerts_count = 0
            while True:
                alerts_count = 0
                self.logger.debug(f"{self.normalized_input_name}|Current checkpoint={current_checkpoint}")
                self.logger.info(f"{self.normalized_input_name}|API request to fetch alerts.")
                alerts_page = self.dataminr_client.get_alerts(input_watchlist_ids, from_cursor=current_checkpoint)
                alerts, new_checkpoint = alerts_page["data"]["alerts"], alerts_page["data"]["to"]
                if not len(alerts):
                    self.logger.info(f"{self.normalized_input_name}|No alerts found.")
                    break
                # check alert type in specified types
                alerts_count = self.ingest_alert(alerts, alerts_count)
                total_alerts_count += alerts_count

                self.logger.info(f"{self.normalized_input_name}|Updating checkpoint.")
                self.checkpoint.update(self.normalized_input_name, new_checkpoint)
                self.logger.info(f"{self.normalized_input_name}|Successfully updated checkpoint.")
                current_checkpoint = new_checkpoint
            self.logger.info(
                f"{self.normalized_input_name}|Completed data collection."
                f" Total Alerts Collected = {str(total_alerts_count)}."
            )
        except Exception as e:
            self.logger.info(
                f"{self.normalized_input_name}|Error occurred during data collection: {e}."
                f" {traceback.format_exc()}"
            )
        finally:
            self.logger.info(f"{self.normalized_input_name}|Exiting data collection.")

    def ingest_alert(self, alerts, alerts_count):
        """Ingest collected events."""
        for alert in alerts:
            if alert["alertType"]["id"] not in self.alert_types:
                continue
            alerts_count += 1
            self.ew.write_event(
                Event(
                    data=self.parse_alert(alert),
                    stanza=self.input_name
                )
            )
        return alerts_count

    @classmethod
    def parse_alert(self, alert):
        """Parse collected events."""
        alert_location_name = alert.get("eventLocation", {}).get("name", None)
        if alert_location_name:
            # can we change this to split by , and the remove trailing spaces etc ?
            alert["eventLocation"]["country"] = alert_location_name.split(", ")[-1]

        if "relatedTerms" in alert:
            alert["relatedTerms"] = [term["text"] for term in alert["relatedTerms"]]

        for url_key in self.DATAMINR_ALERT_URL_KEYS:
            alert.pop(url_key, None)

        caption = alert.get("caption", None)
        if caption and self.DATAMINR_SOURCE_SEPARATOR in caption.lower():
            start = caption.lower().index(self.DATAMINR_SOURCE_SEPARATOR) + len(self.DATAMINR_SOURCE_SEPARATOR)
            source = caption[start:].strip()
            if source.endswith("."):
                source = source[:-1].rstrip()
            alert['eventSource'] = source

        return json.dumps(alert, ensure_ascii=False)


class DataminrAlertsCollectorPulse:
    """Fetch the alerts from Dataminr Pulse, parse and index them into splunk."""

    DATAMINR_SOURCE_SEPARATOR = "via "

    def __init__(self, inputs, event_writer):
        """Initialize an object."""
        self.ew = event_writer
        self.session_key = inputs.metadata["session_key"]
        self.input_name = list(inputs.inputs.keys())[0]
        self.input_item = inputs.inputs[self.input_name]
        self.normalized_input_name = self.input_name.split("/")[-1]
        self.logger = setup_logging(f"dataminr_api_{self.normalized_input_name}")
        self.dataminr_account = self.input_item.get("dataminr_account")
        self.list_names = self.input_item.get("lists_names")
        self.alert_types = self.input_item.get("alert_type").split(",")
        if "All" in self.alert_types:
            self.alert_types = ALL_ALERT_TYPES
        self.dataminr_client = DataminrClientV4(self.session_key, self.dataminr_account)
        self.checkpoint = self.initialize_checkpoint()

    def initialize_checkpoint(self):
        """Initialize an checkpoint."""
        return KVStoreCheckpointer(
            collection_name=f"{ta_name}_checkpointer",
            session_key=self.session_key,
            app=ta_name
        )

    def collect_events(self):
        """Collect events from Dataminr API and ingest."""
        self.logger.info(f"{self.normalized_input_name}|Starting data collection.")
        try:
            self.logger.info(f"{self.normalized_input_name}|Fetching watchlist Ids of configured watchlist names.")
            all_watchlists = self.dataminr_client.get_all_watchlists()
            input_watchlist_ids = get_watchlist_ids(all_watchlists, self.list_names)
            self.logger.info(f"{self.normalized_input_name}|Successfully fetched watchlist Ids.")
            self.logger.debug(f"{self.normalized_input_name}|Configured watchlist Ids={str(input_watchlist_ids)}")
            self.logger.info(f"{self.normalized_input_name}|Fetching checkpoint value.")
            current_checkpoint = self.checkpoint.get(self.normalized_input_name)
            self.logger.info(f"{self.normalized_input_name}|Successfully fetched checkpoint "
                             f"value: {current_checkpoint}.")
            total_alerts_count = 0
            while True:
                self.logger.debug(f"{self.normalized_input_name}|Current checkpoint={current_checkpoint}")
                self.logger.info(f"{self.normalized_input_name}|API request to fetch alerts.")
                if current_checkpoint:
                    alerts_page = self.dataminr_client.get_alerts(input_watchlist_ids, next_page=current_checkpoint)
                else:
                    alerts_page = self.dataminr_client.get_alerts(input_watchlist_ids)
                new_checkpoint = alerts_page.get("nextPage")
                if not alerts_page.get("alerts", []):
                    # No new data, but update checkpoint and break to try again later
                    self.logger.info(f"{self.normalized_input_name}|No alerts, updating checkpoint and exiting loop.")
                    self.checkpoint.update(self.normalized_input_name, new_checkpoint)
                    break

                total_alerts_count += self.ingest_alert(alerts_page, 0)
                current_checkpoint = new_checkpoint
                self.logger.info(f"{self.normalized_input_name}|Updating checkpoint.")
                self.checkpoint.update(self.normalized_input_name, new_checkpoint)
                self.logger.info(f"{self.normalized_input_name}|Successfully updated checkpoint.")
            self.logger.info(
                f"{self.normalized_input_name}|Completed data collection."
                f" Total Alerts Collected = {str(total_alerts_count)}."
            )
        except Exception as e:
            self.logger.error(
                f"{self.normalized_input_name}|Error occurred during data collection: {e}."
                f" {traceback.format_exc()}"
            )
        finally:
            self.logger.info(f"{self.normalized_input_name}|Exiting data collection.")

    def ingest_alert(self, alerts, alerts_count):
        """Ingest collected events."""
        for alert in alerts.get("alerts"):
            if alert.get("alertType", {}).get("name", "").lower() not in self.alert_types:
                continue
            headline = alert.get("headline", None)
            if headline and self.DATAMINR_SOURCE_SEPARATOR in headline.lower():
                idx = headline.lower().rindex(self.DATAMINR_SOURCE_SEPARATOR)
                source = headline[idx + len(self.DATAMINR_SOURCE_SEPARATOR):].strip()
                if source.endswith("."):
                    source = source[:-1].rstrip()
                alert['eventSource'] = source
            if alert.get("alertTimestamp"):
                dt = datetime.strptime(alert.get("alertTimestamp"), "%Y-%m-%dT%H:%M:%S.%fZ")
                epoch_ms = int(dt.timestamp() * 1000)
                alert["eventTime"] = epoch_ms
            self.ew.write_event(
                Event(
                    data=json.dumps(alert, ensure_ascii=False),
                    stanza=self.input_name
                )
            )
            alerts_count += 1
        return alerts_count
