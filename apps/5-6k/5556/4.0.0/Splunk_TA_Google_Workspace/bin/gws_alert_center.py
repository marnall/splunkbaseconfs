#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import json
import os
import sys
import traceback

import import_declare_test  # noqa: 401
from googleapiclient.discovery import build
import google_auth_httplib2
import gws_utils
from gws_utils import (
    APP_NAME,
    logger_for_input,
    CouldNotRefreshCredentialsException,
    get_service_account_credentials,
    ALERT_CENTER_SCOPE,
)
from gws_checkpoint import str_to_seconds
from gws_runner import NUM_RETRIES

from solnlib import conf_manager, log
from solnlib.modular_input import KVStoreCheckpointer
from solnlib.utils import remove_http_proxy_env_vars
from splunklib import modularinput as smi
from splunklib.modularinput import event
from gws_checkpoint import get_query_intervals_for_alerts

remove_http_proxy_env_vars()

ALERT_CENTER_MAX_RESULTS = 500


class AlertCenter(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("gws_alert_center")
        scheme.description = "GWS Alert Center"
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

        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        """
        Main entry point to start the data ingest for each modinput
        :param inputs: inputs configured via the UI in the inputs.conf
        :param event_writer: EventWriter object to ingest data to Splunk
        :return: None
        """
        # inputs.inputs is a dict like:
        # {
        #   "gws_alert_center://<input_name>": {
        #     "account": "<account_name>",
        #     "alert_source": "<alert_source>",
        #     "disabled": "0",
        #     "host": "$decideOnStartup",
        #     "index": "<index_name>",
        #     "interval": "<interval_value>",
        #     "python.version": "python3",
        #   },
        # }
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
                logger.info("Started Google Workspace alerts ingestion")
                normalized_input_name = input_name.split("/")[-1]
                checkpoint_collection = (
                    f"splunk_ta_google_workspace_alerts_{normalized_input_name}"
                )
                checkpointer = KVStoreCheckpointer(
                    checkpoint_collection,
                    session_key,
                    APP_NAME,
                )
                checkpoint_name = "gws_alerts_modular_input"
                checkpoint = checkpointer.get(checkpoint_name)
                if checkpoint is not None:
                    checkpoint = checkpoint.get("checkpoint")
                if input_item["alert_source"] == "gmail_phishing":
                    delay = 4 * 60  # 4 hours in minutes
                    source = 'source="Gmail phishing"'
                elif input_item["alert_source"] == "everything_except_gmail_phishing":
                    delay = 10  # 10 minutes
                    source = 'source!="Gmail phishing"'
                else:
                    raise AssertionError("alert_source field has unexpected value")
                start_time, end_time = get_query_intervals_for_alerts(
                    checkpoint, delay, logger
                )
                account = input_item["account"]
                proxy_config = gws_utils.get_proxy_settings(logger, session_key)
                proxies = gws_utils.build_proxies_from_proxy_config(proxy_config)
                try:
                    num_retries = 5
                    service_account_credentials = get_service_account_credentials(
                        logger,
                        session_key,
                        account,
                        [ALERT_CENTER_SCOPE],
                        proxies,
                        num_retries,
                    )
                except CouldNotRefreshCredentialsException:
                    logger.error(
                        "Could not get access_token, will try next iteration, exiting..."
                    )
                    raise
                _http = gws_utils.build_http_connection(proxy_config)
                authorized_http = google_auth_httplib2.AuthorizedHttp(
                    service_account_credentials, http=_http
                )
                service = build(
                    "alertcenter", "v1beta1", credentials=service_account_credentials
                )
                if proxies is not None:
                    logger.info("Using HTTPS proxy")
                    os.environ["HTTPS_PROXY"] = proxies["https"]
                    os.environ["HTTP_PROXY"] = proxies["http"]
                    os.environ["https_proxy"] = proxies["https"]
                    os.environ["http_proxy"] = proxies["http"]
                results = (
                    service.alerts()
                    .list(
                        filter=f'createTime >= "{start_time}" AND createTime <= "{end_time}" AND {source}',
                        orderBy="createTime asc",
                        pageSize=ALERT_CENTER_MAX_RESULTS,
                    )
                    .execute(http=authorized_http, num_retries=NUM_RETRIES)
                )
                alerts = results.get("alerts", [])
                next_page_token = results.get("nextPageToken", "")
                while next_page_token:
                    results = (
                        service.alerts()
                        .list(
                            pageToken=next_page_token,
                            pageSize=ALERT_CENTER_MAX_RESULTS,
                        )
                        .execute(http=authorized_http, num_retries=NUM_RETRIES)
                    )
                    next_page_token = results.get("nextPageToken", "")
                    alerts.extend(results.get("alerts", []))
                if os.getenv("HTTPS_PROXY"):
                    del os.environ["HTTPS_PROXY"]
                    del os.environ["HTTP_PROXY"]
                    del os.environ["https_proxy"]
                    del os.environ["http_proxy"]
                for alert in alerts:
                    alert_create_time = str_to_seconds(alert.get("createTime"))
                    event_to_ingest = event.Event(
                        data=json.dumps(alert, ensure_ascii=False, default=str),
                        index=input_item["index"],
                        sourcetype="gws:alerts",
                    )
                    if alert_create_time is not None:
                        event_to_ingest.time = alert_create_time
                    event_writer.write_event(event_to_ingest)
                checkpointer.update(
                    checkpoint_name,
                    {"checkpoint": end_time},
                )
                logger.debug(f"Updated checkpoint to {end_time}")
                logger.info(f"Ingested {len(alerts)} events")
                log.events_ingested(
                    logger,
                    input_name,
                    "gws:alerts",
                    len(alerts),
                    input_item["index"],
                )
                logger.info("Finished Google Workspace alerts ingestion")
            except Exception as e:
                log.log_exception(
                    logger,
                    e,
                    "GWS Alert Center ERROR",
                    msg_before=f"Exception raised while ingesting data for alerts: {e}.",
                )


if __name__ == "__main__":
    exit_code = AlertCenter().run(sys.argv)
    sys.exit(exit_code)
