#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import json
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta

import import_declare_test  # noqa: 401
from google.oauth2.service_account import Credentials

import gws_utils
from gws_checkpoint import get_query_intervals_for_gmail
from gws_utils import (
    APP_NAME,
    get_account_details,
    logger_for_input,
)
from solnlib import conf_manager, log
from solnlib.modular_input import KVStoreCheckpointer
from solnlib.utils import remove_http_proxy_env_vars
from splunklib import modularinput as smi
from splunklib.modularinput import event

remove_http_proxy_env_vars()

BIGQUERY_RESULT_PAGE_SIZE = 1000


class GmailLogsScript(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("gmail_logs")
        scheme.description = "Gmail Logs"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )

        return scheme

    def validate_input(self, definition):
        pass

    @staticmethod
    def get_table_suffix_range():
        today = datetime.now(timezone.utc)
        suffix_range = today - timedelta(days=3)
        return suffix_range.strftime("%Y%m%d")

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        from google.cloud import (
            bigquery,
        )  # noqa: PLC0415 — lazy to avoid grpcio load at --scheme time

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
                normalized_input_name = input_name.split("/")[-1]
                checkpoint_collection = (
                    f"splunk_ta_google_workspace_gmail_{normalized_input_name}"
                )
                checkpointer = KVStoreCheckpointer(
                    checkpoint_collection,
                    session_key,
                    APP_NAME,
                )
                checkpoint_name = "gmail_headers_modular_input"
                checkpoint = checkpointer.get(checkpoint_name)
                if checkpoint is not None:
                    checkpoint = checkpoint.get("checkpoint")
                start_time_usec, end_time_usec = get_query_intervals_for_gmail(
                    checkpoint, logger
                )
                account_information = get_account_details(
                    session_key, input_item["account"]
                )
                gcp_project_id = input_item["gcp_project_id"]
                dataset_name = input_item.get("dataset_name")
                dataset_location = input_item.get("dataset_location")
                if dataset_name is None:
                    logger.warning(
                        '`dataset_name` field is empty. Please go to your "Gmail Logs" '
                        'input and update `dataset_name` field. Setting to "gmail_logs_dataset" by default.'
                    )
                    dataset_name = "gmail_logs_dataset"
                if dataset_location is None:
                    logger.warning(
                        '`dataset_location` field is empty. Default location is "US".'
                    )
                    dataset_location = "US"
                certificate = account_information["certificate"]
                credentials = Credentials.from_service_account_info(
                    json.loads(certificate)
                )
                bigquery_client = bigquery.Client(gcp_project_id, credentials)
                table_suffix_range = self.get_table_suffix_range()
                query = (
                    f"SELECT * FROM `{gcp_project_id}.{dataset_name}.daily_*` "
                    f"WHERE event_info.timestamp_usec > {start_time_usec} "
                    f"AND event_info.timestamp_usec < {end_time_usec} "
                    f"AND _TABLE_SUFFIX >= '{table_suffix_range}'"
                    f"ORDER BY event_info.timestamp_usec ASC"
                )
                proxy_config = gws_utils.get_proxy_settings(logger, session_key)
                proxies = gws_utils.build_proxies_from_proxy_config(proxy_config)
                if proxies is not None:
                    logger.info("Using HTTPS proxy")
                    os.environ["HTTPS_PROXY"] = proxies["https"]
                    os.environ["HTTP_PROXY"] = proxies["http"]
                    os.environ["https_proxy"] = proxies["https"]
                    os.environ["http_proxy"] = proxies["http"]
                query_job = bigquery_client.query(query, location=dataset_location)
                if os.getenv("HTTPS_PROXY"):
                    del os.environ["HTTPS_PROXY"]
                    del os.environ["HTTP_PROXY"]
                    del os.environ["https_proxy"]
                    del os.environ["http_proxy"]
                logger.debug(f"Query: {query}")
                results = query_job.result(page_size=BIGQUERY_RESULT_PAGE_SIZE)
                count = 0
                for page in results.pages:
                    last_timestamp_usec = None
                    for row in page:
                        count += 1
                        data = {}
                        for column, value in zip(results.schema, row.values()):
                            if value is not None and value != []:
                                data[column.name] = value
                        event_timestamp_usec = data["event_info"]["timestamp_usec"]
                        event_time = event_timestamp_usec / 10**6
                        last_timestamp_usec = event_timestamp_usec
                        event_writer.write_event(
                            event.Event(
                                data=json.dumps(data),
                                time=event_time,
                                index=input_item["index"],
                                sourcetype="gws:gmail",
                            )
                        )
                    if last_timestamp_usec is not None:
                        checkpointer.update(
                            checkpoint_name,
                            {"checkpoint": last_timestamp_usec},
                        )
                        logger.debug(
                            f"Updated checkpoint to {last_timestamp_usec} "
                            f"({datetime.fromtimestamp(last_timestamp_usec / 10**6)})"
                        )
                logger.info(f"Ingested {count} events")
                log.events_ingested(
                    logger,
                    input_name,
                    "gws:gmail",
                    count,
                    input_item["index"],
                )
            except Exception as e:
                log.log_exception(
                    logger,
                    e,
                    "Gmail Error",
                    msg_before=f"Exception raised while ingesting data for gmail: {e}. "
                    f"Traceback: {traceback.format_exc()}",
                )


if __name__ == "__main__":
    exit_code = GmailLogsScript().run(sys.argv)
    sys.exit(exit_code)
