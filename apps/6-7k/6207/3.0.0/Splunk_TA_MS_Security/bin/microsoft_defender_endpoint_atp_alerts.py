##
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

import import_declare_test  # isort: skip
import splunk_ta_ms_security_constants  # isort: skip
from typing import Any

import datetime
import sys
import traceback

from Splunk_TA_MS_Security.api_specific_content import ApiSpecificContent
from Splunk_TA_MS_Security.environment_specific_urls import EnvironmentSpecificUrls
from ms_security_utils import (
    get_access_token,
    get_account_details,
    process_events_chunked,
    get_current_addon_version,
    get_start_date,
    use_log_level_from_config,
)

from solnlib import conf_manager, log
from splunklib import modularinput as smi

LOG_FILE_NAME = splunk_ta_ms_security_constants.ALERTS_LOG_FILE_NAME
APP_NAME = import_declare_test.ta_name
SETTINGS_CONF_NAME = splunk_ta_ms_security_constants.SETTINGS_CONF_NAME


class MICROSOFT_DEFENDER_ENDPOINT_ATP_ALERTS(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("microsoft_defender_endpoint_atp_alerts")
        scheme.description = "Microsoft Defender for Endpoint Alerts"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )

        scheme.add_argument(
            smi.Argument(
                "azure_app_account",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "tenant_id",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "location",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "start_date",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "request_timeout",
                title="Request Timeout (optional)",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "lookback",
                title="Lookback (optional)",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition: Any) -> None:
        start_date = definition.parameters.get("start_date")
        today = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        if start_date:
            if start_date > today:
                raise ValueError(
                    f"Start date - {start_date} is a future date. It should be less than current time"
                )
            try:
                datetime.datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:  # noqa: F841
                raise ValueError(
                    f"Invalid date format specified for 'Start Date': {start_date}"
                )
            except Exception as e:
                raise Exception(f"Unknown exception occurred - {e}")

    def stream_events(
        self, inputs: smi.InputDefinition, event_writer: smi.EventWriter
    ) -> None:
        """
        Main entry point to start the data ingest for each modinput
        :param inputs: inputs configured via the UI in the inputs.conf
        :param event_writer: EventWriter object to ingest data to Splunk
        :return: None
        """
        access_token = None
        session_key = inputs.metadata["session_key"]

        for input_name, input_item in inputs.inputs.items():
            input_stanza_name = input_name
            input_name = input_name.split("//")[1]
            logger = log.Logs().get_logger(LOG_FILE_NAME + "_" + input_name)
            use_log_level_from_config(logger, session_key)
            input_item["name"] = input_name
            check_point_key = f"atp_lastUpdateTime_{input_name}"
            global_account = get_account_details(
                logger, session_key, input_item["azure_app_account"]
            )
            # setting a higher precedence of tenant_id fetched from inputs over accounts
            input_item["tenant_id"] = input_item.get("tenant_id") or global_account.get(
                "tenant_id"
            )

            # As per MS docs, we update the location before starting the data collection via "General" location.
            if input_item["location"] == "api.securitycenter.windows.com":
                input_item["location"] = "api.securitycenter.microsoft.com"

            urls = EnvironmentSpecificUrls.get_urls_by_location(
                input_item["location"], input_item["tenant_id"]
            )

            try:
                logger.debug(f"Trying to get access token for input={input_name}")
                access_token = get_access_token(
                    global_account["username"],
                    global_account["password"],
                    urls,
                    logger,
                    session_key,
                )
            except Exception:
                logger.error(f"Failed to get access token : {traceback.format_exc()}")

            try:
                logger.debug("Trying to get current addon version")
                current_version = get_current_addon_version(logger, session_key)
                logger.info(
                    splunk_ta_ms_security_constants.CURRENT_TA_VERSION.format(
                        version=current_version
                    )
                )
            except Exception:
                logger.error("Failed to get current addon version")
            lookback = int(input_item.get("lookback", 0))
            if access_token:
                logger.info(splunk_ta_ms_security_constants.TOKEN_SUCCESS_PROCEED)
                query_date = get_start_date(
                    logger, session_key, check_point_key, input_item, input_stanza_name
                )
                atp_url = urls.alerts + ApiSpecificContent.get_alerts_filter(
                    urls.api,
                    query_date,
                    lookback,
                )
                logger.debug(f"ATP URL : {atp_url}")

                try:
                    atp_alerts_ingested = process_events_chunked(
                        logger=logger,
                        session_key=session_key,
                        access_token=access_token,
                        url=atp_url,
                        input_item=input_item,
                        input_stanza_name=input_stanza_name,
                        check_point_key=check_point_key,
                        event_writer=event_writer,
                        source="microsoft_defender_endpoint_atp_alerts",
                        sourcetype="ms:defender:atp:alerts",
                        query_date=query_date,
                        user_agent=f"MdePartner-Splunk-MicrosoftSecurityAddOn/{current_version}",
                        date_field_names=["lastUpdateDateTime", "lastUpdateTime"],
                        request_timeout=int(input_item.get("request_timeout", 60)),
                    )

                    logger.info(
                        f"Total ATP Alerts ingested using chunked processing - atp_alert_count={atp_alerts_ingested}"
                    )
                except Exception as e:
                    logger.error(f"Chunked processing failed: {e}")
                    raise e

            else:
                e = RuntimeError(
                    "Unable to obtain access token. Please check the Application ID, Client Secret, and Tenant ID"
                )
                log.log_authentication_error(
                    logger,
                    e,
                    msg_before=splunk_ta_ms_security_constants.TOKEN_FAILURE_EXIT,
                )
                raise e


# This script is running as an input. Input definitions will be
# passed on stdin as XML, and the script will write events on
# stdout and log entries on stderr.
if __name__ == "__main__":
    exit_code = MICROSOFT_DEFENDER_ENDPOINT_ATP_ALERTS().run(sys.argv)
    sys.exit(exit_code)
