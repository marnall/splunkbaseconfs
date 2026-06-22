"""
censys_proactive_alert_enrichment_triage.py .

Python script to gather intention of IP address via Censys endpoint.

"""
import import_declare_test  # noqa: F401
import sys
import time
import json

from splunktaucclib.alert_actions_base import ModularAlertBase

from common.consts import APP_NAME, IndicatorTypes
from common.config_manager import get_api_key_and_org_id
from common.exceptions import CustomException
import common.log as log
from common.kvstore import CollectionManager
from censys_rest_helper import RestHelper
from utils import (
    get_enriched_host_fields,
    get_enriched_web_property_fields,
    get_enriched_certificate_fields,
)


logger = log.get_logger("censys_enrichment_auto")


class CensysProactiveAlertEnrichmentTriage(ModularAlertBase):
    """Alert Action."""

    def __init__(self, ta_name, alert_name):
        """Initialise Alert Action."""
        super(CensysProactiveAlertEnrichmentTriage, self).__init__(ta_name, alert_name)

    def validate_params(self):
        """Validate Params."""
        if not self.get_param("global_account"):
            logger.error(
                "Censys Account is a mandatory parameter, but its value is None."
            )
            return False
        if not self.get_param("indicator_type"):
            logger.error(
                "Indicator type is a mandatory parameter, but its value is None."
            )
            return False
        if not self.get_param("indicator_field"):
            logger.error(
                "Indicator field is a mandatory parameter, but its value is None."
            )
            return False
        return True

    def process_event(self, *args, **kwargs):
        """Process events."""
        start_time = time.time()
        account = self.get_param("global_account")
        indicator_type = self.get_param("indicator_type")
        indicator_field = self.get_param("indicator_field").strip()
        indicator_port_field = self.get_param("indicator_port_field").strip()

        try:
            if not self.validate_params():
                return 3

            acc_api_key, acc_org_id = get_api_key_and_org_id(
                account, logger, self.session_key
            )
            if not acc_api_key:
                msg = f"API key does not found for account {account}."
                logger.error(msg)
                raise CustomException(msg)

            elif not acc_org_id:
                msg = f"Organization ID does not found for account {account}."
                logger.error(msg)
                raise CustomException(msg)

            censys_config = {
                "session_key": self.session_key,
                "api_key": acc_api_key,
                "org_id": acc_org_id,
            }

            rest_helper_obj = RestHelper(censys_config, logger)

            all_event_list = []

            for event in self.get_events():
                indicator_fields = indicator_field.split(",")
                for indicator_field in indicator_fields:
                    indicator_field = indicator_field.strip()
                    if not indicator_field:
                        continue
                    try:
                        raw_event = json.loads(event.get("_raw", {}))
                        indicator_value = raw_event.get(indicator_field, "").strip()
                        if not indicator_value:
                            logger.error(
                                f'Error while auto enrichment. Value for field "{indicator_field}" is not present.'
                                f' Make sure the field is not nested and available on first level of event.'
                            )
                            continue
                    except Exception:
                        indicator_value = event.get(indicator_field, "")
                        indicator_value = indicator_value.strip()
                        if not indicator_value:
                            logger.error(
                                f'Error while auto enrichment. Value for field "{indicator_field}" is not present.'
                                f' Make sure the field is not nested and available on first level of event.'
                            )
                            continue

                    if indicator_type == IndicatorTypes.HOST.value:
                        response_data = rest_helper_obj.get_enriched_host(
                            indicator_value, acc_org_id
                        )
                        if not response_data:
                            continue

                        enriched_event = get_enriched_host_fields(
                            response_data, "automatic", event
                        )
                        all_event_list.append(enriched_event)

                    elif indicator_type == IndicatorTypes.WEB_PROPERTY.value:
                        port_fields = indicator_port_field.split(",")
                        for port_field in port_fields:
                            port_field = port_field.strip()
                            try:
                                raw_event = json.loads(event.get("_raw", {}))
                                port_value = raw_event.get(port_field, "").strip()
                                if not port_value:
                                    logger.error(
                                        f'Error while auto enrichment.'
                                        f' Value for Port field "{port_field}" is not present.'
                                        f" Make sure the field is not nested and available on first level of event."
                                    )
                                    continue
                            except Exception:
                                port_value = event.get(port_field, "").strip()
                                if not port_value:
                                    logger.error(
                                        f'Error while auto enrichment.'
                                        f' Value for Port field "{port_field}" is not present.'
                                        f" Make sure the field is not nested and available on first level of event."
                                    )
                                    continue
                            response_data = rest_helper_obj.get_enriched_web_property(
                                indicator_value, acc_org_id, port_value
                            )
                            if not response_data:
                                continue

                            enriched_event = get_enriched_web_property_fields(
                                response_data, "automatic", event
                            )
                            all_event_list.append(enriched_event)

                    elif indicator_type == IndicatorTypes.CERTIFICATE.value:
                        response_data = rest_helper_obj.get_enriched_certificate(
                            indicator_value, acc_org_id
                        )
                        if not response_data:
                            continue

                        enriched_event = get_enriched_certificate_fields(
                            response_data, "automatic", event
                        )
                        all_event_list.append(enriched_event)

                    else:
                        logger.error(
                            f"The field '{indicator_field}' does not contain the valid indicator types."
                            f" Valid indicator values are Host, Web Property and Certificate."
                        )
                        raise CustomException("Please provide valid indicator field.")

            kv_source_upsert_start_time = time.time()

            enriched_lookup = None
            if indicator_type == IndicatorTypes.HOST.value:
                enriched_lookup = CollectionManager(
                    "censys_host_enrichment_collection",
                    session_key=self.session_key,
                )
            elif indicator_type == IndicatorTypes.WEB_PROPERTY.value:
                enriched_lookup = CollectionManager(
                    "censys_web_property_enrichment_collection",
                    session_key=self.session_key,
                )
            elif indicator_type == IndicatorTypes.CERTIFICATE.value:
                enriched_lookup = CollectionManager(
                    "censys_certificate_enrichment_collection",
                    session_key=self.session_key,
                )

            enriched_lookup.upsert(all_event_list)
            end_time = time.time()
            logger.info(
                f"message=command_kv_write | Total {len(all_event_list)} events ingested in KV store"
                f" for Type: {indicator_type}"
                f" and time taken: elapsed_seconds={end_time - kv_source_upsert_start_time}."
                f" Total execution time: {end_time - start_time}."
            )

        except (AttributeError, TypeError) as ae:
            import traceback

            logger.error("Error: {}.".format(str(ae)))
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                logger.error(msg.format(str(e)))
            else:
                import traceback

                logger.error(msg.format(traceback.format_exc()))
            return 5


if __name__ == "__main__":
    exitcode = CensysProactiveAlertEnrichmentTriage(
        APP_NAME, "censys_proactive_alert_enrichment_triage"
    ).run(sys.argv)
    sys.exit(exitcode)
