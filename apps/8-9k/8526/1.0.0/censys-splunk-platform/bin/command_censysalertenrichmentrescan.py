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
    wait_for_scan_completion,
)

logger = log.get_logger("censys_rescan")


@Configuration()
class CensysAlertEnrichmentRescan(GeneratingCommand):
    """Censys Alert Enrichment Rescan custom command."""

    account_name = Option(name="account_name", require=True)
    indicator_type = Option(name="indicator_type", require=True)
    service_ip = Option(name="service_ip", require=False)
    service_port = Option(name="service_port", require=False)
    service_protocol = Option(name="service_protocol", require=False)
    service_transport_protocol = Option(
        name="service_transport_protocol", require=False
    )
    web_origin_port = Option(name="web_origin_port", require=False)
    web_origin_hostname = Option(name="web_origin_hostname", require=False)

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

    def validate_service_obj(self):
        """Validate method."""
        if self.service_ip.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given service_ip parameter is empty."
            )
            raise CustomException("Given service_ip parameter is empty.")
        if self.service_port.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given service_port parameter is empty."
            )
            raise CustomException("Given service_port parameter is empty.")
        if self.service_protocol.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given service_protocol parameter is empty."
            )
            raise CustomException("Given service_protocol parameter is empty.")
        if self.service_transport_protocol.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given service_transport_protocol parameter is empty."
            )
            raise CustomException("Given service_transport_protocol parameter is empty.")

    def validate_web_origin(self):
        """Validate method."""
        if self.web_origin_hostname.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given web_origin_hostname parameter is empty."
            )
            raise CustomException("Given web_origin_hostname parameter is empty.")
        if self.web_origin_port.strip() == "":
            logger.error(
                "message=command_error | Censys Error : Given web_origin_port parameter is empty."
            )
            raise CustomException("Given web_origin_port parameter is empty.")

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
                f" account_name: {self.account_name}, indicator_type: {self.indicator_type}."
            )
            self.validate()
            if self.indicator_type == IndicatorTypes.HOST.value:
                self.validate_service_obj()
            else:
                self.validate_web_origin()

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
            enriched_event = {}

            if self.indicator_type == IndicatorTypes.HOST.value:
                # Rescan host
                service_obj = {
                    "ip": self.service_ip,
                    "port": int(self.service_port),
                    "protocol": self.service_protocol,
                    "transport_protocol": self.service_transport_protocol,
                }
                rescan_data = rest_helper_obj.initiate_rescan(
                    acc_org_id, service_obj, None
                )
                if not rescan_data:
                    msg = f"Error while initiating rescan for host {self.service_ip}."
                    logger.error(msg)
                    raise CustomException(msg)
                if not rescan_data.get("result", {}).get("tracked_scan_id"):
                    msg = f"Tracked scan ID does not found for host {self.service_ip}."
                    logger.error(msg)
                    raise CustomException(msg)

                # Scan Status
                tracked_scan_id = rescan_data.get("result", {}).get("tracked_scan_id")
                resource_identifier = f"host {self.service_ip}:{self.service_port}/{self.service_protocol}"

                success, message = wait_for_scan_completion(
                    rest_helper_obj,
                    tracked_scan_id,
                    acc_org_id,
                    resource_identifier,
                    logger,
                )

                if not success:
                    logger.error(message)
                    raise CustomException(message)

                # Get_enriched_host
                response_data = rest_helper_obj.get_enriched_host(
                    self.service_ip, acc_org_id
                )
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

            elif self.indicator_type == IndicatorTypes.WEB_PROPERTY.value:
                # Rescan host
                web_property_obj = {
                    "hostname": self.web_origin_hostname,
                    "port": int(self.web_origin_port),
                }
                rescan_data = rest_helper_obj.initiate_rescan(
                    acc_org_id, None, web_property_obj
                )
                if not rescan_data:
                    msg = f"Error while initiating rescan for web property {self.web_origin_hostname}."
                    logger.error(msg)
                    raise CustomException(msg)
                if not rescan_data.get("result", {}).get("tracked_scan_id"):
                    msg = f"Tracked scan ID does not found for host {self.web_origin_hostname}."
                    logger.error(msg)
                    raise CustomException(msg)

                # Scan Status
                tracked_scan_id = rescan_data.get("result", {}).get("tracked_scan_id")
                resource_identifier = (
                    f"web property {self.web_origin_hostname}:{self.web_origin_port}"
                )

                success, message = wait_for_scan_completion(
                    rest_helper_obj,
                    tracked_scan_id,
                    acc_org_id,
                    resource_identifier,
                    logger,
                )

                if not success:
                    logger.error(message)
                    raise CustomException(message)

                # Get_enriched_host
                response_data = rest_helper_obj.get_enriched_web_property(
                    self.web_origin_hostname, acc_org_id, self.web_origin_port
                )
                if not response_data:
                    logger.warning(
                        "message=command_warning | No data found for web property indicator."
                    )
                    return

                enriched_lookup = CollectionManager(
                    "censys_web_property_enrichment_collection",
                    session_key=session_key,
                )
                enriched_event = get_enriched_web_property_fields(
                    response_data, "manual"
                )

            logger.info("message=command_info | Censys Info : Json Data Retrived.")

            # Write to lookup
            if enriched_lookup and enriched_event:
                kv_source_upsert_start_time = time.time()
                enriched_lookup.upsert([enriched_event])
                logger.info(
                    f"message=command_kv_write | Total events ingested in KV store for Type:{self.indicator_type}"
                    f" and time taken: elapsed_seconds={time.time() - kv_source_upsert_start_time:.3f}."
                )

            # Yield the raw data for search results
            if response_data:
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
                " Please see censys_rescan.log file for more information."
            )
            exit(0)
        finally:
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(CensysAlertEnrichmentRescan, sys.argv, sys.stdin, sys.stdout, __name__)
