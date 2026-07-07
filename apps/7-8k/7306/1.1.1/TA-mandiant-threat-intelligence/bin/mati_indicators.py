import ta_mandiant_threat_intelligence_declare

import os
import sys
import time
import json
import traceback
import urllib.parse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from requests.exceptions import RequestException

from splunklib import modularinput as smi

from setup_logger import setup_logging
from mati_client import MatiApiClient
from mati_constants import APP_VERSION, MATI_UI_URL
from mati_util import read_conf_file, build_proxy_config, checkpoint_handler


bin_dir = os.path.basename(__file__)

logger = setup_logging("ta_mandiant_threat_intelligence_mati_indicators")


class ModInputmati_indicators(smi.Script):

    def __init__(self):
        self.global_checkbox_fields = None
        super(ModInputmati_indicators, self).__init__()

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = smi.Scheme('Indicators')
        scheme.description = ("Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        """
        scheme.add_argument(smi.Argument("global_account", title="Global Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("indicator_time_window_days_", title="Indicator Time Window (Days)",
                                         description="The number of days to go back in time from the current date. Used as a calculated start date filter on an indicators last seen date.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("include_osint", title="Include Open Source Indicators",
                                         description="",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        """Method to get App name."""
        return "TA-mandiant-threat-intelligence"

    def validate_input(self, definition):
        """validate the input stanza"""
        pass

    def get_account_fields(self):
        """Get account fields."""
        account_fields = []
        account_fields.append("global_account")
        return account_fields

    def get_checkbox_fields(self):
        """Get checkbox fields."""
        checkbox_fields = []
        checkbox_fields.append("include_osint")
        return checkbox_fields

    def get_global_checkbox_fields(self):
        """Get global checkbox fields."""
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                logger.error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields


    def build_attribution_list(self, i, attribution_type):
        attribution_list = []
        if "attributed_associations" not in i:
            return attribution_list

        for assoc in i.get('attributed_associations'):
            if assoc.get('type') == attribution_type:
                attribution_path = "actors" if attribution_type == "threat-actor" else "malware"
                attribution_name = assoc.get("name")
                attribution_id = assoc.get("id")
                mandiant_link = f"{MATI_UI_URL}/{attribution_path}/{attribution_id}"
                attribution_list.append({"name": attribution_name, "mandiant_link": mandiant_link})

        return attribution_list

    def build_campaign_links(self, i):
        if "campaigns" not in i:
            return i

        for campaign in i.get("campaigns"):
            campaign["mandiant_link"] = f"{MATI_UI_URL}/campaigns/{campaign.get('id')}"

        return i

    def build_report_links(self, i):
        if "reports" not in i:
            return i

        for report in i.get("reports"):
            report["mandiant_link"] = f"{MATI_UI_URL}/reports/{report.get('report_id')}"

        return i

    def get_file_hash_value(self, i, hash_type):
        hash_to_return = "n/a"
    
        for h in i.get("associated_hashes"):
            if h.get("type") == hash_type:
                hash_to_return = h.get("value")
        
        return hash_to_return

    def build_file_indicator(self, i, file_type):
        file_indicator = {}
        hash_value = self.get_file_hash_value(i, file_type)
        if hash_value != "n/a":
            file_indicator = deepcopy(i)
            file_indicator["type"] = file_type
            file_indicator["value"] = hash_value
        
        return file_indicator

    def build_indicator_link(self, i):
        indicator_type = i.get("type")
        # Double parse the value to make it browser safe
        indicator_value = urllib.parse.quote_plus(urllib.parse.quote_plus(i.get("value")))
        return f"{MATI_UI_URL}/indicator/{indicator_type}/{indicator_value}"

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        """Stream events."""
        try:
            started_at = int(time.time())
            logger.info(f"Indicator collection starting (version: {APP_VERSION})")

            for name, input_item in inputs.inputs.items():
                input_name = name.split('://')[1]

                meta_configs = self._input_definition.metadata
                self.session_key = meta_configs['session_key']

                # Get account and settings
                opt_global_account = input_item.get("global_account")

                splunk_rest_host_info = read_conf_file(
                    session_key=self.session_key,
                    conf_file="ta_mandiant_threat_intelligence_account",
                    stanza=opt_global_account
                )
                opt_key_id = splunk_rest_host_info.get('key_id')
                opt_key_secret = splunk_rest_host_info.get('key_secret')
                opt_indicator_time_window_days_ = int(input_item.get("indicator_time_window_days_"))
                opt_include_osint = True if input_item.get('include_osint') in ("1", "TRUE", "True", "T", "Y", "YES") else False 
                index = input_item.get("index")
                source = input_name
                sourcetype = input_item.get("sourcetype")
                checkpoint_key = "last_updated_at"
                logger.info(f"Settings: Include OSINT: {opt_include_osint}, Indicator Time Window: {opt_indicator_time_window_days_}, Index: {index}, Source: {source}, Sourcetype: {sourcetype}")

                # Proxy Settings
                proxy_config = None
                proxy_settings = read_conf_file(self.session_key, "ta_mandiant_threat_intelligence_settings", stanza="proxy")
                if proxy_settings is None:
                    logger.info("Proxy is not set!")
                if proxy_settings and proxy_settings.get("proxy_enabled") == "1":
                    proxy_config = build_proxy_config(proxy_settings)
                    logger.info(f"Using proxy server for outbound API requests: Proxy Type: {proxy_settings.get('proxy_type')}, Proxy URL: {repr(proxy_settings.get('proxy_url'))}, Proxy Port: {repr(proxy_settings.get('proxy_port'))}")
                else:
                    logger.info("Proxy is not enabled!")

                # Setup date times
                date_now = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
                date_now_ts = int(date_now.timestamp())
                earliest_ingest_date = date_now - timedelta(days=opt_indicator_time_window_days_)
                earliest_ingest_date_ts = date_now_ts - (86400 * opt_indicator_time_window_days_)

                # Get start date from checkpoint
                checkpoint_collection = checkpoint_handler(logger, self.session_key, meta_configs)
                start_date = checkpoint_collection.get(checkpoint_key)
                logger.debug(f"Checkpoint value: {start_date}")

                # If not checkpoint calcuate start date
                if not start_date:
                    logger.info(f"Start date not found, calculated start date: {str(earliest_ingest_date)} ({earliest_ingest_date_ts})")
                    start_date = earliest_ingest_date_ts

                # Get indicators and ingest
                ingested_count = 0
                osint_skipped_count = 0
                mati = MatiApiClient(opt_key_id, opt_key_secret, proxy_config)

                try:
                    logger.info("Collecting indicators...")
                    for i in mati.get_indicators(start_date, date_now_ts, logger):
                        # Add date to index by to avoid conflicts caused by duplicate field names
                        i['last_seen_index'] = i.get('last_seen')
                        
                        # Get sources
                        sources = [source.get('source_name').lower() for source in i.get("sources")]

                        # Skip if not include_osint
                        if not opt_include_osint and "mandiant" not in sources:
                            osint_skipped_count += 1
                            continue

                        # Enrich indicator with calculated fields
                        i["associated_threat_actors"] = self.build_attribution_list(i, "threat-actor")
                        i["associated_malware"] = self.build_attribution_list(i, "malware")
                        i = self.build_campaign_links(i)
                        i = self.build_report_links(i)
                        i["mandiant_link"] = self.build_indicator_link(i)

                        indicators_to_ingest = [i]

                        # If type is md5 also create sha1 and sha256 events
                        if i.get("type") == "md5" and "associated_hashes" in i:
                            indicators_to_ingest.append(self.build_file_indicator(i, "sha1"))
                            indicators_to_ingest.append(self.build_file_indicator(i, "sha256"))
                        
                        # Build events and ingest
                        for indicator in indicators_to_ingest:
                            try:
                                event = smi.Event(
                                    data=json.dumps(indicator),
                                    sourcetype=sourcetype,
                                    source="mati_indicators",
                                    index=index,
                                )
                                ew.write_event(event)
                                ingested_count += 1
                            except BrokenPipeError:
                                logger.error("Output pipe broken while ingesting event")

                    # Update Checkpoint
                    checkpoint_collection.update(checkpoint_key, date_now_ts)
                    logger.info(f"Saved checkpoint key: {checkpoint_key} with value: {date_now_ts}")
                
                except RequestException as ex:
                    logger.error(f"Unexpected error calling Mandiant API: {str(ex)}")
                except Exception as ex:
                    logger.error(f"Unexpected error in modular input: {str(ex)}")
                    logger.error(traceback.format_exc())

                ended_at = int(time.time())
                logger.info(f"Ingested {ingested_count} indicators in {ended_at - started_at} seconds")
                if not opt_include_osint:
                    logger.info(f"Skipped {osint_skipped_count} open source indicators")

        except Exception as e:
            logger.error(f"Error in stream_events: {str(e)}")
            logger.error(traceback.format_exc())
            return False


if __name__ == "__main__":
    exitcode = ModInputmati_indicators().run(sys.argv)
    sys.exit(exitcode)
