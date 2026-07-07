import import_declare_test

import os
import sys
import json

from splunktaucclib.modinput_wrapper import base_modinput
from splunklib import modularinput as smi

import input_module_jamfcomputers as input_module
from legacy_migration import migrate_legacy_inputs, cleanup_legacy_client_prefix, is_splunkd_not_ready

bin_dir = os.path.basename(__file__)


class ModInputjamfcomputers(base_modinput.BaseModInput):

    def __init__(self):
        if 'use_single_instance_mode' in dir(input_module):
            use_single_instance = input_module.use_single_instance_mode()
        else:
            use_single_instance = False
        super(ModInputjamfcomputers, self).__init__("jamf_pro_addon_for_splunk", "jamfcomputers", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = super(ModInputjamfcomputers, self).get_scheme()
        scheme.title = "JamfComputers"
        scheme.description = "Go to the add-on's configuration UI and configure modular inputs under the Inputs menu."
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))
        scheme.add_argument(smi.Argument("account", title="Account",
                                         description="The Jamf Pro server (configured on the Configuration tab) this input pulls from.",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("exclude_unmanaged", title="Exclude unmanaged computers",
                                         description="Exclude unmanaged computers from the inventory pull.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("sections", title="Sections",
                                         description="Select the sections to import. General & User and Location are included by default. Others are optional.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("days_since_contact", title="Days Since Contact",
                                         description="Exclude computers with no check-in within this many days, 0=no exclusion.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("host_as_device_name", title="Host as Device Name",
                                         description="Writes the devices name as the Host Name.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("use_proxy", title="Use proxy",
                                         description="Use the System or Per-App Proxy",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "JAMF-Pro-addon-for-splunk"

    def validate_input(self, definition):
        input_module.validate_input(self, definition)

    def collect_events(self, ew):
        input_module.collect_events(self, ew)

    def get_account_fields(self):
        return ["account"]

    def _parse_input_args_from_global_config(self, inputs):
        try:
            migrate_legacy_inputs(
                inputs.metadata["session_key"],
                inputs.metadata["server_uri"],
                "jamfcomputers",
            )
            cleanup_legacy_client_prefix(
                inputs.metadata["session_key"],
                inputs.metadata["server_uri"],
            )
        except Exception as exc:
            if is_splunkd_not_ready(exc):
                self.log_warning("legacy_migration: splunkd REST not ready; will retry next fire")
            else:
                import traceback
                self.log_warning(
                    "legacy_migration failed; continuing without migration\n" + traceback.format_exc()
                )
        super()._parse_input_args_from_global_config(inputs)

    def get_checkbox_fields(self):
        return ["exclude_unmanaged", "host_as_device_name", "use_proxy"]

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields


if __name__ == "__main__":
    exitcode = ModInputjamfcomputers().run(sys.argv)
    sys.exit(exitcode)
