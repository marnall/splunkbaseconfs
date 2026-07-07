import hispasec_splunk_declare
import app_common

import os
import sys
import time
import datetime
import json

import splunktaucclib.modinput_wrapper.base_modinput as modinput_wrapper
from splunklib import modularinput as smi

import input_module_hispasec_notifications as input_module

bin_dir = os.path.basename(__file__)

class ModInputhispasec_notifications(modinput_wrapper.BaseModInput):

    def __init__(self):
        if 'use_single_instance_mode' in dir(input_module):
            use_single_instance = input_module.use_single_instance_mode()
        else:
            use_single_instance = False
        super(ModInputhispasec_notifications, self).__init__("hispasec_splunk", "hispasec_notifications", use_single_instance)
        self.global_checkbox_fields = None
        app_common.set_helper(self)

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputhispasec_notifications, self).get_scheme()
        scheme.title = ("Hispasec Notifications")
        scheme.description = ("Displays logs that provide summaries about notifications from Hispasec API")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        return scheme

    def get_app_name(self):
        return "Hispasec_Splunk"

    def validate_input(self, definition):
        """validate the input stanza"""
        input_module.validate_input(self, definition)

    def collect_events(self, ew):
        """write out the events"""
        input_module.collect_events(self, ew)

    def get_account_fields(self):
        account_fields = []
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields

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
    exitcode = ModInputhispasec_notifications().run(sys.argv)
    sys.exit(exitcode)
