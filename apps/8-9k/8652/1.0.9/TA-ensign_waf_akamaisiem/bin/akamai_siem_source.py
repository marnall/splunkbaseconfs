import import_declare_test

import os
import sys
import json

from splunktaucclib.modinput_wrapper.base_modinput import BaseModInput
from splunklib import modularinput as smi

import input_module_akamai_siem_source as input_module

bin_dir = os.path.basename(__file__)

class ModInputAkamaiSiemSource(BaseModInput):

    def __init__(self):
        if 'use_single_instance_mode' in dir(input_module):
            use_single_instance = input_module.use_single_instance_mode()
        else:
            use_single_instance = False
        super(ModInputAkamaiSiemSource, self).__init__(
            "ta_ensign_waf_akamaisiem", "akamai_siem_source", use_single_instance
        )
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = super(ModInputAkamaiSiemSource, self).get_scheme()
        scheme.title = ("Akamai Web Security Source")
        scheme.description = ("Go to the add-on's configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.add_argument(smi.Argument("name", title="Name", description="", required_on_create=True))
        scheme.add_argument(smi.Argument("akamai_account", title="Akamai Account", required_on_create=True, required_on_edit=False))
        scheme.add_argument(smi.Argument("config_id", title="Config ID", required_on_create=True, required_on_edit=False))
        scheme.add_argument(smi.Argument("limit_num", title="API Limit", required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("proxy_server", title="Proxy Server", required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("custom_sourcetype", title="Custom Sourcetype", required_on_create=False, required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-ensign_waf_akamaisiem"

    def validate_input(self, definition):
        input_module.validate_input(self, definition)

    def collect_events(self, ew):
        input_module.collect_events(self, ew)

    def get_account_fields(self):
        return []

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
    exitcode = ModInputAkamaiSiemSource().run(sys.argv)
    sys.exit(exitcode)
