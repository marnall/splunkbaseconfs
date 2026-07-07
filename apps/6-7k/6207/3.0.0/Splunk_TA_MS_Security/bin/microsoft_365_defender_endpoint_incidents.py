##
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

import datetime
import json
import sys
import traceback
from typing import Optional, Any

import import_declare_test  # isort: skip
import splunk_ta_ms_security_constants  # isort: skip

from solnlib import conf_manager, log
from splunklib import modularinput as smi

from Splunk_TA_MS_Security.api_specific_content import ApiSpecificContent
from Splunk_TA_MS_Security.environment_specific_urls import EnvironmentSpecificUrls
from ms_security_utils import (
    get_access_token,
    get_account_details,
    process_incidents_chunked,
    get_current_addon_version,
    use_log_level_from_config,
    get_start_date,
    required,
)
from ta_execution_exception import TaExecutionException

LOG_FILE_NAME = splunk_ta_ms_security_constants.INCIDENTS_LOG_FILE_NAME
APP_NAME = import_declare_test.ta_name
SETTINGS_CONF_NAME = splunk_ta_ms_security_constants.SETTINGS_CONF_NAME


class MICROSOFT_365_DEFENDER_ENDPOINT_INCIDENTS(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self) -> Optional[smi.Scheme]:
        """
        Method overloads method from parent class. @see splunklib.modularinput.script.get_schema
        """
        scheme = smi.Scheme("microsoft_365_defender_endpoint_incidents")
        scheme.description = "Microsoft 365 Defender Incidents"
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
                title="Azure App Account",
                description="",
                required_on_create=True,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "tenant_id",
                title="Tenant ID",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "start_date",
                title="Start Date (optional)",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "request_timeout",
                title="Request Timeout (optional)",
                required_on_create=False,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "lookback",
                title="Lookback (optional)",
                required_on_create=False,
                required_on_edit=False,
            )
        )

        return scheme

    def validate_input(self, definition: Any) -> None:
        """
        Method overloads method from parent class. @see splunklib.modularinput.script.validate_input
        """
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
            check_point_key = f"m365_incident_lastUpdateTime_{input_name}"
            global_account = get_account_details(
                logger, session_key, input_item["azure_app_account"]
            )
            query_date = get_start_date(
                logger, session_key, check_point_key, input_item, input_stanza_name
            )
            # setting a higher precedence of tenant_id fetched from inputs over accounts
            input_item["tenant_id"] = input_item.get("tenant_id") or global_account.get(
                "tenant_id"
            )
            environment = required(
                input_item.get("environment"),
                "Required input parameter 'environment' missing",
            )
            tenant_id = required(
                input_item.get("tenant_id"),
                "Required input parameter 'tenant_id' missing",
            )
            urls = EnvironmentSpecificUrls.get_urls_by_environment(
                environment, tenant_id
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
                logger.error(
                    f"Failed to get access token, reason={traceback.format_exc()}"
                )

            try:
                logger.debug("Trying to get current addon version")
                current_version = get_current_addon_version(logger, session_key)
                logger.info(
                    splunk_ta_ms_security_constants.CURRENT_TA_VERSION.format(
                        version=current_version
                    )
                )
                # FIXME get_current_addon_version never throws so either get rid of catch or throw something
            except Exception:
                logger.error("Failed to get current addon version")
            lookback = int(input_item.get("lookback", 0))
            if access_token:
                logger.info(splunk_ta_ms_security_constants.TOKEN_SUCCESS_PROCEED)
                filter_criteria = ApiSpecificContent.get_incidents_filter(
                    urls.api,
                    query_date,
                    lookback,
                )
                incident_url = urls.incidents + filter_criteria
                logger.debug(f"Incident filter={incident_url}")

                # Use chunked processing for incidents with nested alerts
                try:
                    (
                        incident_ingested,
                        incident_alerts_ingested,
                    ) = process_incidents_chunked(
                        logger=logger,
                        session_key=session_key,
                        access_token=access_token,
                        url=incident_url,
                        input_item=input_item,
                        input_stanza_name=input_stanza_name,
                        check_point_key=check_point_key,
                        event_writer=event_writer,
                        user_agent=f"M365DPartner-Splunk-MicrosoftSecurityAddOn/{current_version}",
                        request_timeout=int(input_item.get("request_timeout", 60)),
                    )

                    logger.info(
                        f"Incidents ingested using chunked processing - incident_count={incident_ingested}"
                    )
                    logger.info(
                        f"Incident Alerts ingested using chunked processing - inc_alert_count={incident_alerts_ingested}"
                    )
                except Exception as e:
                    logger.error(f"Chunked processing failed: {e}")
                    raise e

                # Note: Checkpoint handling is now done incrementally within process_incidents_chunked

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
# stdout and log entries on stderr (????).
if __name__ == "__main__":
    exit_code = MICROSOFT_365_DEFENDER_ENDPOINT_INCIDENTS().run(sys.argv)
    sys.exit(exit_code)
