
import os
import sys
import time
import datetime
import json

import import_declare_test

from splunklib import modularinput as smi




bin_dir = os.path.basename(__file__)

'''
'''
import import_declare_test

import os
import os.path as op
import sys
import time
import datetime
import json

import traceback
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput as base_mi
import bugfender_import_data as bf

# encoding = utf-8


'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

class ModInputbugfender_app_logs(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputbugfender_app_logs, self).__init__("ta_bugfender_add_on_for_splunk", "bugfender_app_logs", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputbugfender_app_logs, self).get_scheme()
        scheme.title = ("Bugfender App Logs")
        scheme.description = ("Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(smi.Argument("bugfender_account", title="Bugfender Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("app_id", title="Bugfender App ID",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("initial_start_date", title="Initial Start Date",
                                         description="Provide Initial Start date. This is only used for the first time, the input is run. The next inputs are using a saved timestamp. Must be formatted as RFC3339 string, e.g. 2023-08-15T00:00:00Z.",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-bugfender-add-on-for-splunk"

    def validate_input(helper, definition):
        initial_start_date = helper.get_arg("initial_start_date")
        if (initial_start_date):
            bf.validate_initial_start_date(initial_start_date)
    

    def collect_events(helper, ew):
        log_list = bf.get_bugfender_app_logs(helper)
    
        event_count = 0
        for item in log_list:
            timestamp_rfc3339 = item.get("time")
            timestamp_utc_seconds = bf.convert_rfc3339_to_utc_total_seconds(timestamp_rfc3339, helper)
            event = helper.new_event(data=json.dumps(item), time=timestamp_utc_seconds, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
            ew.write_event(event)
            event_count += 1
    
        helper.log_debug(f"Modular input {helper.get_input_type()} terminated successfully! {event_count} events in total were indexed.")

    def get_account_fields(self):
        account_fields = []
        account_fields.append("bugfender_account")
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
    exitcode = ModInputbugfender_app_logs().run(sys.argv)
    sys.exit(exitcode)
