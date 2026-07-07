
import os
import sys
import time
import datetime
import json

import import_declare_test

from splunklib import modularinput as smi




bin_dir = os.path.basename(__file__)

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
from asm_processor import TASM_Event_Proccessor
import random

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

class ModInputtenable_easm(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputtenable_easm, self).__init__("ta_tenable_easm", "tenable_easm", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputtenable_easm, self).get_scheme()
        scheme.title = ("Tenable EASM")
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
        scheme.add_argument(smi.Argument("tenable_easm_domain", title="Tenable EASM Domain",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("tenable_easm_api_key", title="Tenable EASM API Key",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-tenable-easm"

    def validate_input(helper, definition):
        """Implement your own validation logic to validate the input stanza configurations"""
        # This example accesses the modular input variable
        # tenable_easm_domain = definition.parameters.get('tenable_easm_domain', None)
        # tenable_easm_api_key = definition.parameters.get('tenable_easm_api_key', None)
        pass


    def collect_events(helper, ew):
        """Implement your data collection logic here"""

        # The following examples get the arguments of this input.
        # Note, for single instance mod input, args will be returned as a dict.
        # For multi instance mod input, args will be returned as a single value.
        easm_domain = helper.get_arg('tenable_easm_domain')
        easm_api_key = helper.get_arg('tenable_easm_api_key')
        tasm = TASM_Event_Proccessor(api_key=easm_api_key, hostname=easm_domain)
        tasm.create_events(helper, ew)

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
    exitcode = ModInputtenable_easm().run(sys.argv)
    sys.exit(exitcode)
