#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import sys
import traceback
from urllib.parse import urlsplit

import import_declare_test  # noqa: 401

import gws_checkpoint
from gws_runner import run_ingest
from gws_utils import (
    APP_NAME,
    logger_for_input,
    get_activity_report_checkpoint_collection_name_from_full_name,
)
from solnlib import conf_manager
from solnlib.utils import remove_http_proxy_env_vars
from splunklib import modularinput as smi
from splunklib import client
from solnlib import modular_input, log

APPLICATION_NAME_MAP = {
    "admin": "admin",
    "login": "login",
    "drive": "drive",
    "saml": "saml",
    "oauthtoken": "token",
    "gcp": "gcp",
    "groups_enterprise": "groups_enterprise",
    "calendar": "calendar",
    "context_aware_access": "context_aware_access",
    "rules": "rules",
    "chat": "chat",
    "chrome": "chrome",
    "mobile": "mobile",
    "access_transparency": "access_transparency",
    "data_studio": "data_studio",
    "gemini_in_workspace_apps": "gemini_in_workspace_apps",
}

remove_http_proxy_env_vars()


class ActivityReport(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("activity_report")
        scheme.description = "Activity"
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
                "application",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "lookbackOffset",
                required_on_create=True,
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
        #   "activity_report://<input_name>": {
        #     "account": "<account_name>",
        #     "application": "<application_name>",
        #     "disabled": "0",
        #     "host": "$decideOnStartup",
        #     "index": "<index_name>",
        #     "interval": "<interval_value>",
        #     "lookbackOffset": "<lookbackOffset_value>",
        #     "python.version": "python3",
        #   },
        # }
        for input_name, input_item in inputs.inputs.items():
            logger = logger_for_input(input_name)
            try:
                application_name = input_item.get("application", "")
                application = APPLICATION_NAME_MAP.get(application_name, "")
                splunkd_uri = self._input_definition.metadata["server_uri"]
                session_key = self._input_definition.metadata["session_key"]

                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=APP_NAME,
                    conf_name="splunk_ta_google_workspace_settings",
                )
                logger.setLevel(log_level)

                logger.info("Starting ingestion pipeline")

                splunkd = urlsplit(splunkd_uri, allow_fragments=False)

                service = client.connect(
                    scheme=splunkd.scheme,
                    host=splunkd.hostname,
                    port=splunkd.port,
                    token=session_key,
                    app=APP_NAME,
                )
                try:
                    kvstore_checkpointer = modular_input.KVStoreCheckpointer(
                        get_activity_report_checkpoint_collection_name_from_full_name(
                            input_name
                        ),
                        session_key,
                        APP_NAME,
                    )
                except Exception as kvstore_exc:
                    logger.error(
                        f"Failed to initialize KVStore checkpointer for input '{input_name}': {kvstore_exc}. "
                        "The add-on requires KVStore to track ingestion checkpoints. "
                        "This input will be skipped until KVStore is available. "
                        "Check KVStore status at /services/kvstore/status on this Splunk instance."
                    )
                    continue
                gws_checkpoint.migrate_activity_report_checkpoint(
                    logger,
                    kvstore_checkpointer,
                    service,
                    input_name,
                )
                run_ingest(
                    logger,
                    session_key,
                    input_item["account"],
                    input_name,
                    application,
                    input_item["lookbackOffset"],
                    event_writer,
                    kvstore_checkpointer,
                    input_item["index"],
                )
            except Exception as e:
                log.log_exception(
                    logger,
                    e,
                    "Activity Report Error",
                    msg_before=f"Exception raised while ingesting data for activity: {e}.",
                )


if __name__ == "__main__":
    exit_code = ActivityReport().run(sys.argv)
    sys.exit(exit_code)
