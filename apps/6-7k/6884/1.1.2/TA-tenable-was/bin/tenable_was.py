
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
from tenable_validations import *
from was_processor import WAS_Event_Proccessor
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

class ModInputtenable_was(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputtenable_was, self).__init__("ta_tenable_was", "tenable_was", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputtenable_was, self).get_scheme()
        scheme.title = ("Tenable WAS")
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
        scheme.add_argument(smi.Argument("start_time", title="Start Time",
                                         description="The date (UTC in \"YYYY-MM-DDThh:mm:ssZ\" format) from when to start collecting the data. Default value taken will be start of epoch time.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("tenable_was_domain", title="Tenable WAS Domain",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("tenable_was_api_key", title="Tenable WAS Access Key",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("name", title="Tenable WAS Secret Key",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-tenable-was"

    def validate_input(helper, definition):
        """Implement your own validation logic to validate the input stanza configurations"""
        # This example accesses the modular input variable
        # tenable_was_domain = definition.parameters.get('tenable_was_domain', None)
        # tenable_was_api_key = definition.parameters.get('tenable_was_api_key', None)
        validate_io_interval(helper, definition.parameters.get("interval"))
        validate_start_time(helper, definition.parameters.get("start_time"))
        # pass


    def collect_events(helper, ew):
        """Implement your data collection logic here"""

        # The following examples get the arguments of this input.
        # Note, for single instance mod input, args will be returned as a dict.
        # For multi instance mod input, args will be returned as a single value.
        tenable_was_domain = helper.get_arg('tenable_was_domain')
        tenable_was_api_key = helper.get_arg('tenable_was_api_key')
        tenable_was_secret_key = helper.get_arg('tenable_was_secret_key')
        tenable_was_input = helper.get_arg('name')
        tenable_was_start_time = helper.get_arg("start_time") if helper.get_arg(
            "start_time") else "1970-01-01T00:00:00Z"
        helper.log_debug("tenable_was_start_time {0}".format(tenable_was_start_time))
        helper.log_debug("tenable_was_input {0}".format(tenable_was_input))
        twas = WAS_Event_Proccessor(input_name=tenable_was_input, start_time=tenable_was_start_time, api_key=tenable_was_api_key, secret_key=tenable_was_secret_key, hostname=tenable_was_domain)
        twas.create_events(helper, ew)


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
    exitcode = ModInputtenable_was().run(sys.argv)
    sys.exit(exitcode)
