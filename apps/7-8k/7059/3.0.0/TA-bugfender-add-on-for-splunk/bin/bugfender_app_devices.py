import import_declare_test

import sys
import json

from splunklib import modularinput as smi

import os
import traceback
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput  as base_mi 
import bugfender_import_data as bf

bin_dir  = os.path.basename(__file__)
app_name = os.path.basename(os.path.dirname(os.getcwd()))

class ModInputBUGFENDER_APP_DEVICES(base_mi.BaseModInput): 

    def __init__(self):
        use_single_instance = False
        super(ModInputBUGFENDER_APP_DEVICES, self).__init__(app_name, "bugfender_app_devices", use_single_instance) 
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = smi.Scheme('bugfender_app_devices')
        scheme.description = 'Bugfender App Devices'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                'bugfender_account',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'app_id',
                required_on_create=True,
            )
        )
        
        return scheme

    def validate_input(self, definition):
        """validate the input stanza"""
        """Implement your own validation logic to validate the input stanza configurations"""
        pass

    def get_app_name(self):
        return "app_name" 

    def collect_events(helper, ew):
        # sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
        
        devices = bf.get_bugfender_app_devices(helper)
    
        for device in devices:
            event = helper.new_event(data=json.dumps(device), time=None, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
            ew.write_event(event)
    
        helper.log_debug(f"Modular input {helper.get_input_type()} terminated successfully!")


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


if __name__ == '__main__':
    exit_code = ModInputBUGFENDER_APP_DEVICES().run(sys.argv)
    sys.exit(exit_code)


