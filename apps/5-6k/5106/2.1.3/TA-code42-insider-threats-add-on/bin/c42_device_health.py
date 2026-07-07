import lib_path
import sys
from time import sleep

from splunktaucclib.modinput_wrapper.base_modinput import BaseModInput
from splunklib.modularinput.argument import Argument

from c42_util import (
    Code42ModInput,
    get_now,
    InvalidIntervalException,
)

C42_DEVICE_HEALTH_DEFAULT_RATE_LIMIT = 60
C42_DEVICE_HEALTH_MIN_POLLING_INTERVAL = 300


class DeviceHealthModInput(Code42ModInput, BaseModInput):

    checkpoint_key = None

    def __init__(self):
        super().__init__("ta_code42_insider_threats_add_on", "c42_device_health", False)

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super().get_scheme()
        scheme.title = "Device Health"
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
                description="The Code42 API Client used to query for agent health events. Must include the 'Devices Read' permission. Your product plan must also include full API access.",
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
        if (
            int(definition.parameters["interval"])
            < C42_DEVICE_HEALTH_MIN_POLLING_INTERVAL
        ):
            raise InvalidIntervalException(
                "c42_device_health", C42_DEVICE_HEALTH_MIN_POLLING_INTERVAL
            )

    def collect_events(self, ew):
        """The main method that creates events in Splunk from Code42 Device Health data."""

        self.checkpoint_key = self.get_input_stanza_names()

        try:
            self.log_info("Preparing to get device information from Code42.")
            self.raise_interval_error_if_needed(
                C42_DEVICE_HEALTH_MIN_POLLING_INTERVAL, "Agent Health"
            )
            sdk = self.initialize_sdk()
            state = self.get_check_point(self.checkpoint_key) or {}

            generator = sdk.agents.v1.iter_all(active=True)
            for agent in generator:
                self.write_event(ew, agent)

            self.save_check_point(
                self.checkpoint_key, {"timestamp": get_now().timestamp()}
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
    exitcode = DeviceHealthModInput().run(sys.argv)
    sys.exit(exitcode)
