import import_declare_test

import sys
import json

from splunklib import modularinput as smi

import os
import time
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput as base_mi

bin_dir = os.path.basename(__file__)
app_name = os.path.basename(os.path.dirname(os.getcwd()))


class ModInputCISCO_SPACES_FIREHOSE(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputCISCO_SPACES_FIREHOSE, self).__init__(
            app_name, "cisco_spaces_firehose", use_single_instance
        )
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = smi.Scheme("cisco_spaces_firehose")
        scheme.description = "Cisco Spaces"
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
                "stream",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition):
        """validate the input stanza"""
        """Implement your own validation logic to validate the input stanza configurations"""
        pass

    def get_app_name(self):
        return "ta_cisco_spaces"

    def collect_events(helper, ew):
        helper.log_info("'Cisco Spaces' modular input starting execution.")

        meta_streams_account = helper.get_arg("stream")
        activation_token = meta_streams_account.get("activation_token")
        region = meta_streams_account.get("region")
        location_updates_status = meta_streams_account.get("location_updates_status")

        url = "https://partners.dnaspaces.io/api/partners/v1/firehose/events"
        sourcetype = "cisco:spaces:firehose"

        s = requests.Session()
        s.headers = {"Content-Type": "application/json", "X-API-Key": activation_token}

        # debug
        header_copy = s.headers.copy()
        header_copy["X-API-Key"] = "****"
        helper.log_debug(
            f"Starting stream to Cisco Spaces API with the following header: {header_copy}"
        )

        try:
            with s.get(
                url=url,
                stream=True,
            ) as response:
                response.raise_for_status()
                event_count = 0
                for event in response.iter_lines():
                    try:
                        raw_event = json.loads(event)
                        event_type = raw_event["eventType"]

                        if (
                            event_type != "DEVICE_LOCATION_UPDATE"
                            or location_updates_status in ["1", True, "true", "True"]
                        ):
                            event = helper.new_event(
                                data=json.dumps(
                                    raw_event, ensure_ascii=False, default=str
                                ),
                                source=helper.get_input_type(),
                                index=helper.get_output_index(),
                                sourcetype=sourcetype,
                            )
                            ew.write_event(event)
                            event_count += 1
                            helper.log_debug(
                                f"Event received from Cisco Spaces with event type '{event_type}' indexed for Splunk. Response headers are {response.headers}"
                            )
                    except json.JSONDecodeError as e:
                        helper.log_info(
                            f"JSON decoding error for event: {e}, but ignoring"
                        )
                        continue
        except requests.exceptions.ChunkedEncodingError as e:
            helper.log_info(
                f"Received requests.exceptions.ChunkedEncodingError, but ignoring it. Error message is: {str(e)}"
            )
            time.sleep(5)
        except Exception as e:
            helper.log_error(
                f"Something went wrong. Aborting. Error message is '{str(e)}'."
            )
            raise e

        helper.log_info(
            f"'Cisco Spaces' modular input successfully completed execution. {event_count} event(s) were indexed for Splunk."
        )

    def get_account_fields(self):
        account_fields = []
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, "global_checkbox_param.json")
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, "r") as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error(
                    "Get exception when loading global checkbox parameter names. "
                    + str(e)
                )
                self.global_checkbox_fields = []
        return self.global_checkbox_fields


if __name__ == "__main__":
    exit_code = ModInputCISCO_SPACES_FIREHOSE().run(sys.argv)
    sys.exit(exit_code)
