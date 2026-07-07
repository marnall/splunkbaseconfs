import lib_path
import sys
from datetime import timezone, timedelta, datetime
import json

from splunktaucclib.modinput_wrapper.base_modinput import BaseModInput
from splunklib.modularinput.argument import Argument
from c42_util import (
    Code42ModInput,
    InvalidIntervalException,
)

C42_ALERTS_INITIAL_DAYS_BACK = 30
C42_ALERTS_MIN_POLLING_INTERVAL = 300
C42_ALERTS_RESPONSE_MAX_RESULTS = 500


def _get_all_alert_details_from_sdk(sdk, sessions):
    """Use incydr sdk to add file event data to alerts."""
    sessions_file_events = []
    for session in sessions:
        current_session = session
        try:
            current_session.fileEvents = json.loads(sdk.sessions.v1.get_session_events(
                current_session.session_id
            ).json())["fileEvents"]
        except:
            current_session.fileEvents = {}
        sessions_file_events.append(current_session)

    return sessions_file_events


class AlertsModInput(Code42ModInput, BaseModInput):

    checkpoint_key = None

    def __init__(self):
        super().__init__("ta_code42_insider_threats_add_on", "c42_alerts", False)

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super().get_scheme()
        scheme.title = "Alerts"
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
                description="The Code42 API Client used to query for alerts. Must include the 'Sessions Read' permission. Your product plan must also include full API access.",
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "c42_search_behavior",
                title="Search Behavior",
                description='Select whether to ingest all alerts or only those in the below categories (if "All Alerts" is selected, the below items are all treated as selected).',
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "severity_low",
                title="Low",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "severity_medium",
                title="Medium",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "severity_high",
                title="High",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "risk_severity_low",
                title="Risk Severity Low",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "risk_severity_moderate",
                title="Risk Severity Moderate",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "risk_severity_high",
                title="Risk Severity High",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "risk_severity_critical",
                title="Risk Severity Critical",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        ),
        scheme.add_argument(
            Argument(
                "add_file_events",
                title="Add file events to sessions",
                description="",
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
        return [
            "severity_low",
            "severity_medium",
            "severity_high",
            "risk_severity_low",
            "risk_severity_moderate",
            "risk_severity_high",
            "risk_severity_critical",
            "add_file_events",
        ]

    def get_global_checkbox_fields(self):
        return []

    def validate_input(self, definition):
        """validate the input stanza"""
        if int(definition.parameters["interval"]) < C42_ALERTS_MIN_POLLING_INTERVAL:
            raise InvalidIntervalException(
                "c42_alerts", C42_ALERTS_MIN_POLLING_INTERVAL
            )
        
    def _get_all_alerts_from_sdk(self, sdk, checkpoint, severity_filter):
        """Use the incydr sdk to get all the session ids
        starting at the given checkpoint time.
        """
        # severity_filter must be a list of severities by number (0,1,2,3,4)
        # only allowable sort keys are end_time and score, so we use end_time
        initial_days_back = (
            datetime.now(tz=timezone.utc) - timedelta(days=C42_ALERTS_INITIAL_DAYS_BACK)
        ).timestamp()

        self.log_debug(f"{type(initial_days_back)} - {initial_days_back}")
        
        all_sessions = sdk.sessions.v1.iter_all(
            start_time=int(initial_days_back * 1000), severities=severity_filter
        )
        return_sessions = []
        for session in all_sessions:
            if round(session.last_updated / 1000) >= checkpoint:
                session.actor = sdk.actors.v1.get_actor_by_id(session.actor_id).name
                return_sessions.append(session)
        return return_sessions

    def collect_events(self, ew):
        """The main method that creates events in Splunk from Code42 Alerts."""

        self.checkpoint_key = self.get_input_stanza_names()

        try:
            self.log_info("Preparing to search for new Code42 Alerts.")
            self.raise_interval_error_if_needed(
                C42_ALERTS_MIN_POLLING_INTERVAL, "Alerts"
            )
            alerts, checkpoint_alerts = self._get_all_alerts()
            self.log_debug(f"Processing {len(alerts)} alerts.")
            new_timestamp = 0
            new_alerts = []

            for alert in alerts:
                self.log_debug(f"    Deduplicating {alert.session_id}")
                # De-duplicate events across checkpointed runs.
                if alert.session_id not in checkpoint_alerts:
                    self.log_debug(f"    Writing {alert.session_id}")
                    if round(alert.last_updated / 1000) > new_timestamp:
                        new_timestamp = round(alert.last_updated / 1000)
                        new_alerts = []

                    new_alerts.append(alert.session_id)
                    self.write_event(ew, alert)

            if new_timestamp is not None and new_alerts:
                new_save_data = {
                    "timestamp": new_timestamp,
                    "events": new_alerts,
                }
                self.save_check_point(self.checkpoint_key, new_save_data)

        except KeyError as err:
            # version 1.2.0+ requires api clients for authentication.
            # Notify after upgrade if it hasn't been re-configured yet.
            if err.args[0] == "api_client_id":
                self.notify_api_client_config_required()
            else:
                raise err

        except Exception as err:
            self.log_error_with_traceback(err)

    def _get_all_alerts(self):
        """Get all the Alerts from Code42.
        Also returns the checkpointed alerts from the last poll
        to deduplicate alerts at the start of the next poll.
        """
        add_file_events = self.get_arg("add_file_events")
        sdk = self.initialize_sdk()
        checkpoint, checkpoint_alerts = self.get_checkpoint_data(
            checkpoint_key=self.checkpoint_key,
            initial_days_back=C42_ALERTS_INITIAL_DAYS_BACK,
        )
        severity_filter = self._get_severity_filter()
        self._log_search_message(checkpoint, severity_filter)
        sessions = self._get_all_alerts_from_sdk(sdk, checkpoint, severity_filter)
        if add_file_events:
            sessions = _get_all_alert_details_from_sdk(sdk, sessions)
        return sessions, checkpoint_alerts

    def _get_severity_filter(self):
        if self.get_arg("c42_search_behavior") == "all":
            return None
        else:
            if any(
                [
                    self.get_arg("severity_low"),
                    self.get_arg("severity_medium"),
                    self.get_arg("severity_high"),
                ]
            ):
                self._convert_severity_config_to_risk_severity()
            severities = set()
            if self.get_arg("severity_low") or self.get_arg("risk_severity_low"):
                severities.add(1)
            if self.get_arg("severity_medium") or self.get_arg(
                "risk_severity_moderate"
            ):
                severities.add(2)
            if self.get_arg("severity_high"):
                severities.update([3, 4])
            if self.get_arg("risk_severity_high"):
                severities.add(3)
            if self.get_arg("risk_severity_critical"):
                severities.add(4)

            return list(severities)

    def _convert_severity_config_to_risk_severity(self):
        data = {
            "severity_low": 0,
            "severity_medium": 0,
            "severity_high": 0,
        }
        if self.get_arg("severity_low"):
            data["risk_severity_low"] = 1
        if self.get_arg("severity_medium"):
            data["risk_severity_moderate"] = 1
        if self.get_arg("severity_high"):
            data["risk_severity_high"] = 1
            data["risk_severity_critical"] = 1
        try:
            self.update_mod_input_config(**data)
            self.log_debug(f"converted severity configs to riskSeverity")
        except Exception as err:
            self.log_error(
                f"failed to convert c42_alert severity configs to riskSeverity: {err}"
            )

    def _log_search_message(self, checkpoint, severity_filter):
        """Log a message about the current query being made."""
        checkpoint_str = (
            str(datetime.fromtimestamp(checkpoint))
            if isinstance(checkpoint, float)
            else checkpoint
        )
        message = f"Executing Code42 alerts search -- filters: {severity_filter}, alerts on or after: {checkpoint_str}"
        self.log_info(message)


if __name__ == "__main__":
    exitcode = AlertsModInput().run(sys.argv)
    sys.exit(exitcode)
