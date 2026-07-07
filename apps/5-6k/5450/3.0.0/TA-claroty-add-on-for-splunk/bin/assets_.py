import import_declare_test

import os
import sys
import json

from splunktaucclib.modinput_wrapper import base_modinput
from splunklib import modularinput as smi

import input_module_assets_ as input_module

bin_dir = os.path.dirname(os.path.abspath(__file__))


class ModInputAssets(base_modinput.BaseModInput):

    def __init__(self):
        if 'use_single_instance_mode' in dir(input_module):
            use_single_instance = input_module.use_single_instance_mode()
        else:
            use_single_instance = False
        super().__init__("ta_claroty_add_on_for_splunk", "assets_", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = super().get_scheme()
        scheme.title = "Assets"
        scheme.description = "Go to the add-on's configuration UI and configure modular inputs under the Inputs menu."
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))
        scheme.add_argument(smi.Argument("emc_ip", title="EMC IP",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("emc_admin_account", title="EMC Admin Account",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("sites", title="Sites",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("asset_class", title="Class",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("asset_type", title="Asset Type",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("asset_vendor", title="Vendor",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("asset_criticality", title="Criticality",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("from_timestamp", title="From Timestamp",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("notification_email", title="Notification Email",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-claroty-add-on-for-splunk"

    def validate_input(self, definition):
        input_module.validate_input(self, definition)

    def collect_events(self, ew):
        input_module.collect_events(self, ew)

    def get_account_fields(self):
        return ["emc_admin_account"]

    def get_checkbox_fields(self):
        return []

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
    exitcode = ModInputAssets().run(sys.argv)
    sys.exit(exitcode)
