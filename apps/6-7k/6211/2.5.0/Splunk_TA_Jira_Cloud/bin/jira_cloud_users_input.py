#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import hashlib
import json
import sys
import traceback

import import_declare_test  # noqa
import jira_cloud_consts as jcc
import jira_cloud_utils as utils
import pymd5
from jira_cloud_checkpoint import JiraCloudCheckpoint as Checkpoint
from jira_cloud_connect import Connect
from solnlib import utils as sol_utils
from splunklib import modularinput as smi


class JiraUsersCollector:
    """Class for collecting Jira Users"""

    def __init__(self, event_writer, config, logger, proxy):
        self.event_writer = event_writer
        self.config = config
        self.logger = logger
        self.connect = Connect(logger=logger, proxy=proxy)
        self.checkpoint_updated = False
        self.event_ingested = 0
        self.params = {"startAt": 0, "maxResults": jcc.JIRA_USERS_MAX_RESULTS}
        self.checkpoint = Checkpoint(
            logger=self.logger,
            input_name=jcc.KVSTORE_USERS_COLLECTION_NAME,
            session_key=self.config.get("session_key"),
        )

    def collect_events(self):
        """This method collect user data."""

        sol_utils.handle_teardown_signals(self.exit_gracefully)

        self.page = 0
        self.last_page = False
        self.event_ingested = 0
        self.event_received = 0
        self.checkpoint_data = self.get_checkpoint()

        while not self.last_page:
            self.page += 1

            response = self.connect.get(
                domain=self.config.get("domain"),
                endpoint=jcc.JIRA_USERS_ENDPOINT,
                username=self.config.get("username"),
                token=self.config.get("token"),
                params=self.params,
            )
            users = response.json()
            total_events = len(users)

            if total_events > 0:
                checksum = self.get_checksum(response.content)
                old_checksum = self.checkpoint_data.get(str(self.page))
                self.logger.debug(
                    f"Checking the checksum for page={self.page}, old_checksum={old_checksum}, new_checksum={checksum}"
                )

                if not checksum == old_checksum:
                    self.ingest_events(users)
                    self.checkpoint_data.update({str(self.page): checksum})
                    self.checkpoint.update_checkpoint(
                        self.config.get("input_name"), self.checkpoint_data
                    )

                self.params["startAt"] = (
                    self.params["startAt"] + self.params["maxResults"]
                )
                self.event_received += total_events
            else:
                self.last_page = True

        self.logger.info(
            "Total events received = {} | Total events ingested = {}".format(
                self.event_received, self.event_ingested
            )
        )

    def get_checkpoint(self):
        """This method the checkpoint data."""

        try:
            self.logger.debug("Getting checkpoint data")
            return (
                self.checkpoint.get_checkpoint_data(self.config.get("input_name")) or {}
            )
        except Exception as e:
            msg = "Error while fetching checkpoint information. Reason: {}".format(
                traceback.format_exc()
            )
            utils.add_ucc_error_logger(
                logger=self.logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_users_input"),
                msg_before=msg,
            )
            sys.exit(1)

    def ingest_events(self, events):
        """This method writes events to the event writer and updates the checkpoint."""

        try:
            for raw_event in events:
                raw_event.pop("avatarUrls", None)

                smi_event = smi.Event(
                    data=json.dumps(raw_event),
                    sourcetype=jcc.JIRA_USERS_SOURCETYPE,
                    source=self.config.get("input_name"),
                    host=Connect.build_hostname(domain=self.config.get("domain")),
                    index=self.config.get("index"),
                )
                self.event_writer.write_event(smi_event)
                self.event_ingested += 1
            utils.log_events_ingested(
                logger=self.logger,
                modular_input_name=f'{self.config.get("input_type")}://{self.config.get("input_name")}',
                sourcetype=jcc.JIRA_USERS_SOURCETYPE,
                n_events=len(events),
                index=self.config.get("index"),
                account=self.config.get("api_token"),
                host=Connect.build_hostname(domain=self.config.get("domain")),
                license_usage_source=self.config.get("input_name"),
            )
        except Exception as e:
            msg = "Error writing event to Splunk: {}".format(traceback.format_exc())
            utils.add_ucc_error_logger(
                logger=self.logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_users_input"),
                msg_before=msg,
            )
            sys.exit(1)

    @staticmethod
    def get_checksum(string_to_encode):
        """This method create checksum."""

        try:
            return hashlib.new(
                name="md5", data=string_to_encode, usedforsecurity=False
            ).hexdigest()
        except ValueError:
            # Only happens on python less than 39 and FIPS enabled
            return pymd5.md5(string_to_encode).hexdigest()

    def exit_gracefully(self, signum, frame):
        """This method handles sigterm and updates the checkpoint"""

        self.logger.info(
            "Execution about to get stopped for input '{}' due to SIGTERM.".format(
                self.config["input_name"]
            )
        )
        try:
            self.checkpoint.update_checkpoint(
                self.config.get("input_name"), self.checkpoint_data
            )
        except Exception as exc:
            msg = "Unable to save checkpoint before SIGTERM termination. Error: {}".format(
                exc
            )
            utils.add_ucc_error_logger(
                logger=self.logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=exc,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_users_input"),
                msg_before=msg,
            )
        sys.exit(0)


class JiraCloudUsersInput(smi.Script):
    def __init__(self):
        super(JiraCloudUsersInput, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("jira_cloud_users_input")
        scheme.description = "Jira Users"
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
                "api_token",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "use_existing_checkpoint",
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        session_key = self._input_definition.metadata["session_key"]
        for input_name, input_items in inputs.inputs.items():
            input_items["input_name"] = input_name.split("://")[-1]
            input_items["input_type"] = input_name.split("://")[0]

        logfile_name = jcc.JIRA_CLOUD_USERS_LOGFILE_PREFIX + input_items["input_name"]
        _logger = utils.set_logger(session_key, logfile_name)

        try:
            _logger.info("Users Modular Input Started.")
            api_token = input_items.get("api_token")
            api_token_details = utils.get_api_token_details(
                session_key, _logger, api_token
            )

            _logger.debug("Getting proxy settings")
            proxy_settings = utils.get_proxy_settings(session_key, _logger)

            input_items["session_key"] = session_key
            input_items.update(api_token_details)

            jira_users_collector = JiraUsersCollector(
                ew, input_items, _logger, proxy_settings
            )
            jira_users_collector.collect_events()
            _logger.info("Users Modular Input Exited.")

        except Exception as e:
            msg = "Error while streaming events for input {}: {}".format(
                input_name, traceback.format_exc()
            )
            utils.add_ucc_error_logger(
                logger=_logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_users_input"),
                msg_before=msg,
            )


if __name__ == "__main__":
    exit_code = JiraCloudUsersInput().run(sys.argv)
    sys.exit(exit_code)
