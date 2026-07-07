import lib_path
import sys
import json
from hashlib import sha256
from datetime import datetime

from splunktaucclib.modinput_wrapper.base_modinput import BaseModInput
from splunklib.modularinput.argument import Argument
from c42_util import (
    Code42ModInput,
    get_app_version,
    parse_timestamp,
    InvalidIntervalException,
)

C42_AUDIT_LOG_INITIAL_DAYS_BACK = 2
C42_AUDIT_LOG_MIN_POLLING_INTERVAL = 900


def _get_all_audit_log_events_from_sdk(sdk, checkpoint):
    """Use py42 to make requests to get all the audit-log events
    starting at the given checkpoint time.
    """
    response_gen = sdk.audit_log.v1.iter_all(
        start_time=datetime.fromtimestamp(checkpoint)
    )
    return sorted(response_gen, key=lambda x: x.get("timestamp"))


def _hash_event(event):
    """Hash an event for the sake of storing it and using it to distinguish
    it from other events during the time de-duplication.
    """
    if isinstance(event, dict):
        event = json.dumps(event, sort_keys=True)
    return sha256(event.encode()).hexdigest()


class AuditLogModInput(Code42ModInput, BaseModInput):

    checkpoint_key = None

    def __init__(self):
        super().__init__("ta_code42_insider_threats_add_on", "c42_audit_log", False)

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super().get_scheme()
        scheme.title = "Audit Log"
        scheme.description = "Go to the add-on's configuration UI and configure modular inputs under the Inputs menu."
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(
            Argument("name", title="Name", description="", required_on_create=True)
        )
        scheme.add_argument(
            Argument(
                "c42_account",
                title="Code42 API Client",
                description="The Code42 API Client used to query for audit log events. Must include the 'Audit Log Read' permission. Your product plan must also include full API access.",
                required_on_create=True,
                required_on_edit=False,
            )
        )
        return scheme

    def get_app_name(self):
        return "TA-code42-insider-threats-add-on"

    def get_account_fields(self):
        return ["c42_account"]

    def get_checkbox_fields(self):
        return []

    def get_global_checkbox_fields(self):
        return []

    def validate_input(self, definition):
        """validate the input stanza"""
        if int(definition.parameters["interval"]) < C42_AUDIT_LOG_MIN_POLLING_INTERVAL:
            raise InvalidIntervalException(
                "c42_audit_log", C42_AUDIT_LOG_MIN_POLLING_INTERVAL
            )

    def _log_search_message(self, checkpoint):
        """Log a message about the current query being made."""
        message = "Executing Code42 audit log search -- events on or after: {0}".format(
            checkpoint
        )
        self.log_info(message)

    def collect_events(self, ew):
        """The main method that creates events in Splunk from Code42 Audit Log events."""
        self.checkpoint_key = self.get_input_stanza_names()
        try:
            self.log_info("Preparing to search for new Code42 Audit Log events.")
            self.raise_interval_error_if_needed(
                C42_AUDIT_LOG_MIN_POLLING_INTERVAL, "Audit Log"
            )
            sdk = self.initialize_sdk()
            checkpoint, checkpoint_events = self.get_checkpoint_data(
                checkpoint_key=self.checkpoint_key,
                initial_days_back=C42_AUDIT_LOG_INITIAL_DAYS_BACK,
            )
            self._log_search_message(checkpoint)
            events = _get_all_audit_log_events_from_sdk(sdk, checkpoint)
            self.log_info(f"Processing {len(events)} audit-log events.")
            new_timestamp = None
            new_events = []

            for event in events:
                event_hash = _hash_event(event)

                # De-duplicate events across checkpointed runs.
                if event_hash not in checkpoint_events:
                    if event["timestamp"] != new_timestamp:
                        new_timestamp = event["timestamp"]
                        new_events = []

                    new_events.append(event_hash)
                    self.write_event(ew, event)
                else:
                    self.log_info("Duplicate event found, skipping.")

            if new_timestamp is not None and new_events:
                parsed_timestamp = parse_timestamp(new_timestamp)
                self.save_check_point(
                    self.checkpoint_key,
                    {"timestamp": parsed_timestamp, "events": new_events},
                )

        except KeyError as err:
            # version 1.2.0+ requires api clients for authentication. Notify after upgrade if it hasn't been re-configured yet.
            if err.args[0] == "api_client_id":
                self.notify_api_client_config_required()
            else:
                raise err

        except Exception as err:
            self.log_error_with_traceback(err)


if __name__ == "__main__":
    exitcode = AuditLogModInput().run(sys.argv)
    sys.exit(exitcode)
