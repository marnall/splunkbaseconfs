import import_declare_test  # noqa: F401
import sys
import time
import json
import traceback

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

from censys_rest_helper import RestHelper
from common.consts import IndicatorTypes
from common.config_manager import get_api_key_and_org_id
from common.exceptions import CustomException
from common.kvstore import CollectionManager
import common.log as log
from utils import (
    get_enriched_host_fields,
    get_enriched_web_property_fields,
    get_enriched_certificate_fields,
)


logger = log.get_logger("censys_enrichment_manual")


@Configuration()
class CensysReactiveAlertEnrichmentTriage(GeneratingCommand):
    """Censys Reactive Alert Enrichment Triage custom command."""

    account_name = Option(name="account_name", require=True)
    indicator_type = Option(name="indicator_type", require=True)
    indicator_value = Option(name="indicator_value", require=True)
    indicator_port = Option(name="indicator_port", require=False)
    at_time = Option(name="at_time", require=False)

    def validate(self):
        """Validate method."""
        if self.account_name.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given account_name parameter is empty."
            )
            raise CustomException("Given account_name parameter is empty.")
        if self.indicator_type.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given indicator_type parameter is empty."
            )
            raise CustomException("Given indicator_type parameter is empty.")
        if self.indicator_value.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given indicator_value parameter is empty."
            )
            raise CustomException("Given indicator_value parameter is empty.")

    def write_to_lookup(self, enriched_lookup, enriched_events):
        """Write evetn to Lookup."""
        if enriched_lookup and enriched_events:
            kv_source_upsert_start_time = time.time()
            enriched_lookup.upsert(enriched_events)
            logger.info(
                f"message=command_kv_write | Total events ingested in KV store for Type:{self.indicator_type}"
                f" and time taken: elapsed_seconds={time.time() - kv_source_upsert_start_time:.3f}."
            )

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
                f" indicator_type: {self.indicator_type}, indicator_value: {self.indicator_value},"
                f" account_name: {self.account_name}."
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

            else:
                censys_config = {
                    "session_key": session_key,
                    "api_key": acc_api_key,
                    "org_id": acc_org_id,
                }

                rest_helper_obj = RestHelper(censys_config, logger)

                response_data = {}
                enriched_lookup = None
                enriched_event = {}
                all_enriched_event = []

                if self.indicator_type == IndicatorTypes.HOST.value:
                    response_data = rest_helper_obj.get_enriched_host(
                        self.indicator_value, acc_org_id, self.at_time
                    )
                    if response_data is None:
                        raise CustomException("Failed to get enriched host data")
                    if not response_data:
                        logger.warning(
                            "message=command_warning | No data found for host indicator."
                        )
                        return

                    enriched_lookup = CollectionManager(
                        "censys_host_enrichment_collection",
                        session_key=session_key,
                    )
                    enriched_event = get_enriched_host_fields(response_data, "manual")
                    all_enriched_event.append(enriched_event)
                    # Write to lookup
                    self.write_to_lookup(enriched_lookup, all_enriched_event)

                elif self.indicator_type == IndicatorTypes.WEB_PROPERTY.value:
                    if not self.indicator_port:
                        logger.warning(
                            "message=command_warning | No Port value found for web_property indicator."
                        )
                        return

                    all_ports = self.indicator_port.split(",")
                    enriched_lookup = CollectionManager(
                        "censys_web_property_enrichment_collection",
                        session_key=session_key,
                    )

                    for port in all_ports:
                        port = port.strip()
                        response_data = rest_helper_obj.get_enriched_web_property(
                            self.indicator_value,
                            acc_org_id,
                            port,
                            self.at_time,
                        )
                        if not response_data:
                            logger.warning(
                                "message=command_warning | No data found for web_property indicator."
                            )
                            continue

                        enriched_event = get_enriched_web_property_fields(
                            response_data, "manual"
                        )
                        all_enriched_event.append(enriched_event)

                    # Write to lookup
                    self.write_to_lookup(enriched_lookup, all_enriched_event)

                elif self.indicator_type == IndicatorTypes.CERTIFICATE.value:
                    response_data = rest_helper_obj.get_enriched_certificate(
                        self.indicator_value, acc_org_id
                    )
                    if response_data is None:
                        raise CustomException("Failed to get enriched certificate data")
                    if not response_data:
                        logger.warning(
                            "message=command_warning | No data found for certificate indicator."
                        )
                        return

                    enriched_lookup = CollectionManager(
                        "censys_certificate_enrichment_collection",
                        session_key=session_key,
                    )
                    enriched_event = get_enriched_certificate_fields(
                        response_data, "manual"
                    )
                    all_enriched_event.append(enriched_event)
                    # Write to lookup
                    self.write_to_lookup(enriched_lookup, all_enriched_event)

                logger.info("message=command_info | Censys Info : Json Data Retrived.")

                # Yield the enriched data for search results
                for enriched_event in all_enriched_event:
                    yield {
                        "_raw": json.dumps(enriched_event, ensure_ascii=False),
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
                " Please see censys_enrichment_manual.log file for more information."
            )
            exit(0)
        finally:
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(CensysReactiveAlertEnrichmentTriage, sys.argv, sys.stdin, sys.stdout, __name__)
