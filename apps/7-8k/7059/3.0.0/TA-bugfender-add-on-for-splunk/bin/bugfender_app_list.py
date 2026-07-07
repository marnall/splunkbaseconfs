
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

class ModInputbugfender_app_list(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputbugfender_app_list, self).__init__("ta_bugfender_add_on_for_splunk", "bugfender_app_list", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputbugfender_app_list, self).get_scheme()
        scheme.title = ("Bugfender Apps")
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
        return scheme

    def get_app_name(self):
        return "TA-bugfender-add-on-for-splunk"

    def validate_input(helper, definition):
        """Implement your own validation logic to validate the input stanza configurations"""
        # This example accesses the modular input variable
        # bugfender_account = definition.parameters.get('bugfender_account', None)
        pass
    

    def collect_events(helper, ew):
        # sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
        
        app_list = bf.get_bugfender_app_list(helper)
    
        for app in app_list:
            event = helper.new_event(data=json.dumps(app), time=None, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
            ew.write_event(event)
        helper.log_debug(f"Modular input {helper.get_input_type()} terminated successfully!")

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
    exitcode = ModInputbugfender_app_list().run(sys.argv)
    sys.exit(exitcode)
