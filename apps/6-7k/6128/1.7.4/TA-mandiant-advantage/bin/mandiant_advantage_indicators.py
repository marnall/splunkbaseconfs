import import_declare_test

import json
import traceback
import sys
import pytz
import time
import dateutil.parser as dp

from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib.modular_input import checkpointer

from common.proxy import transform_proxy_config
from common.utility import get_app_version
from datetime import datetime, timedelta
from mandiant_threatintel.threat_intel_client import ThreatIntelClient
from requests.exceptions import RequestException

import common.log as log

logger = log.get_logger(__file__)


class MANDIANT_ADVANTAGE_INDICATORS(smi.Script):
    def __init__(self):
        super(MANDIANT_ADVANTAGE_INDICATORS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('mandiant_advantage_indicators')
        scheme.description = 'Mandiant Threat Intelligence'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                'mandiant_advantage_account',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'days_back',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'm_score',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'include_osint',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'include_threat_rating',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def build_category_list(self, indicator) -> list:
        categories = []
        for source in indicator.sources or []:
            for category in source.get('category', []) or []:
                if category not in categories:
                    categories.append(category)
        return categories


    def build_attribution_list(self, indicator, attribution_type: str) -> list:
        attribution_list = []
        if "attributed_associations" not in indicator._api_response:
            return attribution_list

        for assoc in indicator._api_response.get('attributed_associations') or []:
            if assoc.get('type') == attribution_type:
                attribution_list.append(f"{assoc.get('id')}||{assoc.get('name')}")

        return attribution_list


    def build_campaign_list(self, indicator) -> list:
        campaigns = []
        if "campaigns" not in indicator._api_response:
            return campaigns

        for campaign in indicator.campaigns or []:
            campaigns.append(f"{campaign.id}||{campaign.name}")

        return campaigns


    def build_report_list(self, indicator) -> list:
        reports = []
        
        for report in indicator.reports or []:
            reports.append(report.report_id)
        
        return reports

    def get_credentials(self, account_name, session_key):
        """Provide credentials of the configured account.

        Args:
            session_key: current session session key
            logger: log object

        Returns:
            Dict: A Dictionary having account information.
        """
        try:
            cfm = conf_manager.ConfManager(
                session_key,
                "TA-mandiant-advantage",
                realm=f"__REST_CREDENTIAL__#TA-mandiant-advantage"
                "#configs/conf-ta_mandiant_advantage_account",
            )
            account_conf_file = cfm.get_conf(
                "ta_mandiant_advantage_account"
            )
            acc_creds = account_conf_file.get(account_name)
        except Exception:
            logger.error(f"Error in fetching account details. {traceback.format_exc()}")
            return None
        return acc_creds

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)

        start = time.time()

        # Get session key
        meta_configs = self._input_definition.metadata
        session_key = meta_configs.get("session_key")

        # Get App Version
        app_version = get_app_version(session_key)

        logger.info("Starting Mandiant Indicator data collection. "
                        f"App Version: {app_version}")

        # Set up counter for logging
        indicators_indexed = 0
        indicators_skipped = 0

        # Get Input Params
        account = input_items[1]['mandiant_advantage_account']
        ac_creds = self.get_credentials(account, session_key)
        api_key = ac_creds.get('client_id')
        api_secret = ac_creds.get('client_secret')
        index = input_items[1]["index"]
        # source = helper.get_input_type()
        sourcetype = "mandiant:advantage:indicators"
        gte_mscore = int(input_items[1]["m_score"])
        days_back = int(input_items[1]["days_back"])
        include_threat_rating = input_items[1]["include_threat_rating"]
        include_osint = input_items[1]["include_osint"]

        # Generate proxy settings
        proxy_config = {
            'proxy_enabled': ac_creds.get("proxy_enabled"),
            'proxy_username': ac_creds.get("proxy_username"),
            'proxy_port': ac_creds.get("proxy_port"),
            'proxy_type': ac_creds.get("proxy_type"),
            'proxy_password': ac_creds.get("proxy_password"),
            'proxy_url': ac_creds.get("proxy_url")
        }
        proxies = transform_proxy_config(proxy_config)

        # Get start date from checkpoint or calculate based on days_back
        checkpoint_key = "indicators_last_update"
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            "TA_mandiant_advantage_checkpointer", session_key, 'TA-mandiant-advantage'
        )
        checkpoint = checkpoint_collection.get(checkpoint_key)

        logger.info(f"Checkpoint value: {checkpoint}")
        if checkpoint:
            start_date = dp.parse(checkpoint)
            start_date = start_date.replace(tzinfo=pytz.UTC)
            gte_mscore = 0
            logger.debug("Checkpoint found, setting start date from checkpoint and gte_mscore to 0")
        else:
            start_date = datetime.utcnow() - timedelta(days=days_back)
        logger.info(f"Start date: {str(start_date)}")


        # Initialize mandiant_threatintel client
        try:
            mandiant = ThreatIntelClient(api_key, api_secret, request_timeout=60,
                                        client_name=f"MA-Splunk-{app_version}",
                                        proxy_config=proxies)

            # Set end date locally to use as checkpoint value assuming job completes
            end_date = datetime.utcnow()

            # Get Indicators from Mandiant
            logger.info("Collecting indicators from Mandiant")
            indicators = mandiant.Indicators.get_list(start_epoch=start_date,minimum_mscore=gte_mscore)

            # For each indicator from Mandiant write event to index and update
            # mandiant_master_lookup kv store
            for indicator in indicators:
                # Calculate a new last_seen field as Splunk seems to index the ealriest
                # last_seen value from anywhere in the obkect and soemtimes there can be
                # a date earlier than the actual date we want to be indexed in the sources key
                if indicator._api_response is not None:
                    event_data: dict = indicator._api_response
                    event_data['last_seen_index'] = event_data.get('last_seen')
                else:
                    event_data = {}
                    event_data['last_seen_index'] = None

                # Remove threat rating if customer not opted in
                if "threat_rating" in event_data and include_threat_rating != "1":
                    del event_data['threat_rating']

                # Filter osint depending on include_osint
                if include_osint != "1":
                    source_names = [source.get('source_name') for source in (indicator.sources or [])]
                    if 'Mandiant' not in source_names:
                        indicators_skipped += 1
                        continue

                # If type is md5 add sha1 and sha256
                if indicator.type == "md5":
                    indicator._api_response['sha1'] = indicator.sha1
                    indicator._api_response['sha256'] = indicator.sha256

                # Add category key
                event_data['category'] = self.build_category_list(indicator)

                # Add threat_actor key
                event_data['threat_actor'] = self.build_attribution_list(indicator, "threat-actor")

                # Add malware key
                event_data['malware'] = self.build_attribution_list(indicator, "malware")

                # Add campaign_list key
                event_data['campaigns_list'] = self.build_campaign_list(indicator)

                # Add reports_list key
                event_data['reports_list'] = self.build_report_list(indicator)

                # Build Splunk event
                event = smi.Event(
                    data=json.dumps(event_data),
                    sourcetype='mandiant:advantage:indicators',
                    index=index
                )
                # Ingest event
                ew.write_event(event)
                indicators_indexed += 1

            # Update Checkpoint with previously set end_date
            checkpoint_collection.update(checkpoint_key, str(end_date))
            logger.info(f"Saved checkpoint key: {checkpoint_key} with value: {str(end_date)}")
        except RequestException as ex:
            err = f"Unexpected error calling Mandiant API: {str(ex)}"
            logger.error(err)
        except BrokenPipeError:
            logger.error("Output pipe broken while ingesting event")
        except Exception as er:
            logger.error(f"Get error when collecting events.\n{traceback.format_exc()}")
            return

        # Log results
        logger.info(f"{indicators_indexed} indicators added to index, "
                        f"{indicators_skipped} indicators skipped")

        end = time.time()

        logger.info(f"Process complete in {end - start} seconds")


if __name__ == '__main__':
    exit_code = MANDIANT_ADVANTAGE_INDICATORS().run(sys.argv)
    sys.exit(exit_code)