import import_declare_test  # noqa: F401
import sys
import time
import json
from urllib.parse import quote
import traceback

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

import common.log as log
from common.config_manager import get_api_key_and_org_id
from common.exceptions import CustomException
from common.kvstore import CollectionManager
from censys_rest_helper import RestHelper
from utils import (
    construct_censys_host_event_history_link,
    get_enriched_host_event_history_fields,
    extract_resource_type_and_values,
)

logger = log.get_logger("censys_history")


@Configuration()
class CensysAlertEnrichmentHistory(GeneratingCommand):
    """Censys Alert Enrichment History custom command."""

    account_name = Option(name="account_name", require=True)
    host_ip = Option(name="host_ip", require=True)
    end_time = Option(name="start_time", require=True)
    start_time = Option(name="end_time", require=True)

    def validate(self):
        """Validate method."""
        if self.account_name.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given account_name parameter is empty."
            )
            raise CustomException("Given account_name parameter is empty.")
        if self.host_ip.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given host_ip parameter is empty."
            )
            raise CustomException("Given host_ip parameter is empty.")
        if self.end_time.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given end_time parameter is empty."
            )
            raise CustomException("Given end_time parameter is empty.")
        if self.start_time.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given start_time parameter is empty."
            )
            raise CustomException("Given start_time parameter is empty.")

    def generate(self):
        """Generate method."""
        try:
            logger.info(
                "message=command_start_execution | Censys Info : Started Custom Command Script Execution."
            )
            start_time = time.time()
            session_key = self._metadata.searchinfo.session_key
            logger.info(
                f"message=command_start_execution | Censys Info : Provided params are"
                f" account_name: {self.account_name}, host_ip: {self.host_ip},"
                f" end_time: {self.end_time}, start_time: {self.start_time}."
            )
            self.validate()

            acc_api_key, acc_org_id = get_api_key_and_org_id(
                self.account_name, logger, session_key
            )
            if not acc_api_key:
                msg = f"API key does not found for account {self.account_name}."
                logger.error(msg)
                raise CustomException(msg)

            elif not acc_org_id:
                msg = f"Organization ID does not found for account {self.account_name}."
                logger.error(msg)
                raise CustomException(msg)

            censys_config = {
                "session_key": session_key,
                "api_key": acc_api_key,
                "org_id": acc_org_id,
            }

            rest_helper_obj = RestHelper(censys_config, logger)

            response_data = {}
            enriched_lookup = None

            # Get Host Event History
            response_data = rest_helper_obj.get_host_event_history(
                self.host_ip.strip(),
                acc_org_id,
                self.start_time.strip(),
                self.end_time.strip(),
            )

            if response_data and response_data.get("failed", False):
                censys_err_message = response_data.get("err_message", "Failed to get host event history.")
                logger.error(censys_err_message)
                raise CustomException(censys_err_message)

            if not response_data:
                logger.warning(
                    "message=command_warning | No history data found for host indicator."
                )
                return
            all_events = response_data.get("result", {}).get("events", [])
            all_event_list = []

            if len(all_events) >= 1000:
                more_events_msg = (
                    "There are more than 1,000 host history records available for this host."
                    " The first 1,000 records are displayed."
                    " Further exploration should be conducted on the Censys platform."
                )
                self.write_warning(more_events_msg)

            for event in all_events:
                resource = event.get("resource", {})
                event_time = resource.get("event_time", "")
                encoded_event_time = quote(event_time)
                historical_host_link = construct_censys_host_event_history_link(
                    self.host_ip, encoded_event_time, acc_org_id
                )

                # Use the common function to extract resource_type and resource_key_values
                resource_type, resource_key_values = extract_resource_type_and_values(
                    resource
                )

                # Skip if resource type is not recognized
                if resource_type is None:
                    continue

                event_history_event = get_enriched_host_event_history_fields(
                    self.host_ip,
                    event_time,
                    historical_host_link,
                    resource_type,
                    resource_key_values,
                )
                all_event_list.append(event_history_event)

            enriched_lookup = CollectionManager(
                "censys_host_event_history_collection",
                session_key=session_key,
            )

            logger.info("message=command_info | Censys Info : Json Data Retrived.")

            # Write to lookup
            if enriched_lookup and all_event_list:
                kv_source_upsert_start_time = time.time()
                enriched_lookup.upsert(all_event_list)
                logger.info(
                    f"message=command_kv_write | Events ingested in KV store for Host: {self.host_ip}"
                    f" and time taken: elapsed_seconds={time.time() - kv_source_upsert_start_time:.3f}."
                )

            # Yield the raw data for search results
            for event in all_event_list:
                yield {
                    "_raw": json.dumps(event, ensure_ascii=False),
                    "_time": time.time(),
                }
        except Exception as e:
            logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self.write_error(
                f"{e} or unexpected error occurred."
                " Please see censys_history.log file for more information."
            )
            exit(0)
        finally:
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(CensysAlertEnrichmentHistory, sys.argv, sys.stdin, sys.stdout, __name__)
