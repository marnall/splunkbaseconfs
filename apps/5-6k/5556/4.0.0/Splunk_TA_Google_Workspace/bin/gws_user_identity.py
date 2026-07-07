#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import json
import os
import sys
import time
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
    DIRECTORY_USER_SCOPE,
)
from gws_runner import NUM_RETRIES

from solnlib import conf_manager, log
from solnlib.modular_input import KVStoreCheckpointer
from solnlib.utils import remove_http_proxy_env_vars
from splunklib import modularinput as smi
from splunklib.modularinput import event

remove_http_proxy_env_vars()

USER_DIRECTORY_MAX_RESULTS = 500


class UserIdentity(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("gws_user_identity")
        scheme.description = "GWS User Identity List"
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
                "gws_customer_id",
                required_on_create=True,
            )
        )

        scheme.add_argument(smi.Argument("gws_view_type", required_on_create=True))

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
        #   "gws_user_identity://<input_name>": {
        #     "account": "<account_name>",
        #     "gws_customer_id": "customer id",
        #     "gws_view_type": "domain_public",
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
                logger.info("Started Google Workspace users ingestion")
                normalized_input_name = input_name.split("/")[-1]
                checkpointer = KVStoreCheckpointer(
                    f"splunk_ta_google_workspace_user_identity_{normalized_input_name}",
                    session_key,
                    APP_NAME,
                )
                account = input_item["account"]
                customer_id = input_item.get("gws_customer_id")
                view_type = input_item.get("gws_view_type", "domain_public")
                proxy_config = gws_utils.get_proxy_settings(logger, session_key)
                proxies = gws_utils.build_proxies_from_proxy_config(proxy_config)
                try:
                    num_retries = 5
                    service_account_credentials = get_service_account_credentials(
                        logger,
                        session_key,
                        account,
                        [DIRECTORY_USER_SCOPE],
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
                    "admin", "directory_v1", credentials=service_account_credentials
                )
                if proxies is not None:
                    logger.info("Using HTTPS proxy")
                    os.environ["HTTPS_PROXY"] = proxies["https"]
                    os.environ["HTTP_PROXY"] = proxies["http"]
                    os.environ["https_proxy"] = proxies["https"]
                    os.environ["http_proxy"] = proxies["http"]
                results = (
                    service.users()
                    .list(
                        customer=customer_id,
                        orderBy="email",
                        maxResults=USER_DIRECTORY_MAX_RESULTS,
                        viewType=view_type,
                    )
                    .execute(http=authorized_http, num_retries=NUM_RETRIES)
                )
                users = results.get("users", [])
                next_page_token = results.get("nextPageToken", "")
                while next_page_token:
                    results = (
                        service.users()
                        .list(
                            customer=customer_id,
                            orderBy="email",
                            maxResults=USER_DIRECTORY_MAX_RESULTS,
                            viewType=view_type,
                            pageToken=next_page_token,
                        )
                        .execute(http=authorized_http, num_retries=NUM_RETRIES)
                    )
                    next_page_token = results.get("nextPageToken", "")
                    users.extend(results.get("users", []))
                if os.getenv("HTTPS_PROXY"):
                    del os.environ["HTTPS_PROXY"]
                    del os.environ["HTTP_PROXY"]
                    del os.environ["https_proxy"]
                    del os.environ["http_proxy"]
                count = 0
                for user in users:
                    count += 1
                    event_writer.write_event(
                        event.Event(
                            data=json.dumps(user, ensure_ascii=False, default=str),
                            index=input_item["index"],
                            sourcetype="gws:users:identity",
                        )
                    )
                checkpointer.update(
                    "last_run",
                    {"last_run_timestamp": time.time()},
                )
                logger.info("Finished Google Workspace users ingestion")
                log.events_ingested(
                    logger,
                    input_name,
                    "gws:users:identity",
                    count,
                    input_item["index"],
                )
            except Exception as e:
                log.log_exception(
                    logger,
                    e,
                    "User Identity Error",
                    msg_before=f"Exception raised while ingesting data for users: {e}. "
                    f"{traceback.format_exc()}",
                )


if __name__ == "__main__":
    exit_code = UserIdentity().run(sys.argv)
    sys.exit(exit_code)
