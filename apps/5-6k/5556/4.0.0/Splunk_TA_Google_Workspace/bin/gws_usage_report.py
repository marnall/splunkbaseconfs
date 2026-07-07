#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import sys
import json
import time
import datetime
import pytz
import import_declare_test
from gws_utils import (
    logger_for_input,
    APP_NAME,
    get_account_details,
    build_http_connection,
)
from solnlib.utils import remove_http_proxy_env_vars
from solnlib import log, conf_manager
from solnlib.modular_input import KVStoreCheckpointer
from gws_checkpoint import get_dates_for_usage_report, str_to_seconds
from google.oauth2.service_account import Credentials
import google_auth_httplib2
import gws_utils
import googleapiclient.discovery
import googleapiclient.errors
from gws_preprocess import split_events
from splunklib import modularinput as smi
from gws_runner import get_UsageReports


remove_http_proxy_env_vars()
NUM_RETRIES = 5


class UsageReport(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("usage_report")
        scheme.description = "Usage"
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
                "account",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "endpoint",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "start_date",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        """
        Main entry point to start the data ingest for each modinput
        :param inputs: inputs configured via the UI in the inputs.conf
        :param event_writer: EventWriter object to ingest data to Splunk
        :return: None
        """
        for input_name, input_item in inputs.inputs.items():
            logger = logger_for_input(input_name)
            try:
                session_key = self._input_definition.metadata["session_key"]

                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=APP_NAME,
                    conf_name="splunk_ta_google_workspace_settings",
                )
                logger.setLevel(log_level)

                logger.info("Starting ingestion pipeline")

                logger.debug("Getting proxy settings")

                proxy_config = gws_utils.get_proxy_settings(logger, session_key)
                proxies = gws_utils.build_proxies_from_proxy_config(proxy_config)

                logger.debug("Getting service account credentials")
                try:
                    num_retries = 5
                    service_account_credentials = (
                        gws_utils.get_service_account_credentials(
                            logger,
                            session_key,
                            input_item["account"],
                            [gws_utils.USAGE_REPORT_SCOPE],
                            proxies,
                            num_retries,
                        )
                    )
                except gws_utils.CouldNotRefreshCredentialsException:
                    logger.error(
                        "Could not get access_token, will try next iteration, exiting..."
                    )
                    raise

                normalized_input_name = input_name.split("/")[-1]
                checkpoint_collection = (
                    f"splunk_ta_google_workspace_usage_report_{normalized_input_name}"
                )

                checkpointer = KVStoreCheckpointer(
                    checkpoint_collection,
                    session_key,
                    APP_NAME,
                )
                checkpoint_name = "usage_report_modular_input"
                checkpoint = checkpointer.get(checkpoint_name)
                if checkpoint is not None:
                    checkpoint = checkpoint.get("checkpoint")

                dates_to_query = get_dates_for_usage_report(
                    checkpoint,
                    logger,
                    input_item["start_date"] if input_item.get("start_date") else None,
                )

                _http = gws_utils.build_http_connection(proxy_config)
                authorized_http = google_auth_httplib2.AuthorizedHttp(
                    service_account_credentials, http=_http
                )
                service = googleapiclient.discovery.build(
                    "admin",
                    "reports_v1",
                    credentials=service_account_credentials,
                )
                endpoint_of_reports = input_item["endpoint"]
                sourcetype = f"gws:usage_reports:{endpoint_of_reports}"
                count_events = 0
                for day_to_query in dates_to_query:
                    last_event_time_sec = None
                    logger.info(f"Getting data for: {day_to_query}")
                    usage_reports = get_UsageReports(
                        logger,
                        service,
                        authorized_http,
                        day_to_query,
                        applicationName=endpoint_of_reports,
                    )
                    for report in usage_reports:
                        event = smi.Event(
                            data=json.dumps(report, ensure_ascii=False, default=str),
                            sourcetype=sourcetype,
                        )
                        ew.write_event(event)
                        count_events += 1
                        event_time = report["date"]
                        last_event_time_sec = str_to_seconds(event_time)

                    if last_event_time_sec is not None:
                        checkpointer.update(
                            checkpoint_name,
                            {"checkpoint": last_event_time_sec},
                        )
                        logger.info(
                            f"Updated checkpoint with value: {last_event_time_sec}"
                        )
                logger.info(f"events ingested: {count_events}")
                log.events_ingested(
                    logger,
                    input_name,
                    sourcetype,
                    count_events,
                    input_item["index"],
                )

            except Exception as e:
                log.log_exception(
                    logger,
                    e,
                    "Usage Report Error",
                    msg_before=f"Exception raised while ingesting data for usage report: {e}.",
                )


if __name__ == "__main__":
    exit_code = UsageReport().run(sys.argv)
    sys.exit(exit_code)
