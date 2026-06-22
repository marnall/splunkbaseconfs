import import_declare_test  # noqa: F401
import sys
import time
import json
import traceback

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

import common.log as log
from common.consts import IndicatorTypes
from common.config_manager import get_api_key_and_org_id
from common.exceptions import CustomException
from common.kvstore import CollectionManager
from censys_rest_helper import RestHelper
from utils import (
    get_enriched_host_fields,
    get_enriched_web_property_fields,
    get_enriched_certificate_fields,
)

logger = log.get_logger("censys_related_infrastructure")


@Configuration()
class CensysAlertEnrichmentRelatedInfra(GeneratingCommand):
    """Censys Alert Enrichment Related Infra custom command."""

    account_name = Option(name="account_name", require=True)
    indicator_type = Option(name="indicator_type", require=True)
    field = Option(name="field", require=True)
    value = Option(name="value", require=True)

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

        if self.field.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given field parameter is empty."
            )
            raise CustomException("Given field parameter is empty.")

        if self.value.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given value parameter is empty."
            )
            raise CustomException("Given value parameter is empty.")

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
                f' account_name: "{self.account_name}", field: "{self.field}", value: "{self.value}".'
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

            # Run Query
            whole_query = f"{self.field.strip()}:'{self.value.strip()}'"

            search_query_result = rest_helper_obj.run_search_query(
                acc_org_id, whole_query
            )

            if search_query_result and search_query_result.get("failed", False):
                msg = "message=command_error | Censys Error : Failed to run search query."
                censys_err_message = search_query_result.get("err_message", msg)
                logger.error(censys_err_message)
                raise CustomException(censys_err_message)

            if (
                not search_query_result
                or search_query_result.get("result", {}).get("total_hits", 0) <= 0
            ):
                msg = (
                    "message=command_warning | No search query result found"
                    f" for field {self.field}, query {whole_query}."
                )
                logger.warning(msg)
                return

            if search_query_result.get("result", {}).get("total_hits", 0) > 1000:
                msg = (
                    "There are more than 1,000 related assets based on the entered key-value pair."
                    " Further exploration should be conducted on the Censys platform."
                )
                logger.warning(msg)
                raise CustomException(msg)

            result_hits = search_query_result.get("result", {}).get("hits", [])
            if not result_hits:
                msg = f"message=command_warning | No hits found for field {self.field}."
                logger.warning(msg)
                return

            result_hits_values = []
            for event in result_hits:
                for event_value in event.values():
                    resulted_event = {"result": event_value}
                    result_hits_values.append(resulted_event)

            enriched_lookup = None
            if self.indicator_type == IndicatorTypes.HOST.value:
                enriched_lookup = CollectionManager(
                    "censys_host_enrichment_collection",
                    session_key=session_key,
                )
            elif self.indicator_type == IndicatorTypes.WEB_PROPERTY.value:
                enriched_lookup = CollectionManager(
                    "censys_web_property_enrichment_collection",
                    session_key=session_key,
                )
            elif self.indicator_type == IndicatorTypes.CERTIFICATE.value:
                enriched_lookup = CollectionManager(
                    "censys_certificate_enrichment_collection",
                    session_key=session_key,
                )
            else:
                logger.error(
                    f"message=command_error | Censys Error : Invalid indicator_type - {self.indicator_type}"
                )
                raise CustomException(f"Invalid indicator_type - {self.indicator_type}")

            enriched_events = []
            for result_hit_value in result_hits_values:
                enriched_event = {}
                if self.indicator_type == IndicatorTypes.HOST.value:
                    enriched_event = get_enriched_host_fields(
                        result_hit_value, "manual"
                    )
                elif self.indicator_type == IndicatorTypes.WEB_PROPERTY.value:
                    enriched_event = get_enriched_web_property_fields(
                        result_hit_value, "manual"
                    )
                elif self.indicator_type == IndicatorTypes.CERTIFICATE.value:
                    enriched_event = get_enriched_certificate_fields(
                        result_hit_value, "manual"
                    )
                enriched_events.append(enriched_event)

            logger.info("message=command_info | Censys Info : Json Data Retrived.")

            # Write to lookup
            if enriched_lookup and enriched_events:
                kv_source_upsert_start_time = time.time()
                enriched_lookup.upsert(enriched_events)
                logger.info(
                    f"message=command_kv_write | Total events ingested in KV store for Fields: {self.field}"
                    f" and time taken: elapsed_seconds={time.time() - kv_source_upsert_start_time:.3f}."
                )

            # Yield the raw data for search results
            for enriched_event in enriched_events:
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
                f"{e} Please see censys_related_infrastructure.log"
                " file for more information."
            )
            exit(0)
        finally:
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(CensysAlertEnrichmentRelatedInfra, sys.argv, sys.stdin, sys.stdout, __name__)
