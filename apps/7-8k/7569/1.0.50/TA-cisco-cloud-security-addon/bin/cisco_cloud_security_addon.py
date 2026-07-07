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
from umbrella.event_processer import AWSS3Connection 

bin_dir  = os.path.basename(__file__)
app_name = os.path.basename(os.path.dirname(os.getcwd()))

class ModInputCISCO_CLOUD_SECURITY_ADDON(base_mi.BaseModInput): 

    def __init__(self):
        use_single_instance = False
        super(ModInputCISCO_CLOUD_SECURITY_ADDON, self).__init__(app_name, "cisco_cloud_security_addon", use_single_instance) 
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = smi.Scheme('cisco_cloud_security_addon')
        scheme.description = 'Cisco Cloud Security Addon'
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
                'region',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'access_key_id',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'secret_access_key',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'bucket_name',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'prefix',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'start_date',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'event_type',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'account_name',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'event_log_name',
                required_on_create=False,
            )
        )
        
        return scheme

    def validate_input(self, definition):
        """validate the input stanza"""
        """Implement your own validation logic to validate the input stanza configurations"""
        pass

    def get_app_name(self):
        return "TA-cisco-cloud-security-addon" 

    def collect_events(helper, ew):
        aws_s3_conn = AWSS3Connection()
        aws_s3_conn.ew = ew
        aws_s3_conn.helper = helper
        # collect events AWS S3 bucket
        aws_s3_conn.fetch_events_from_s3_bucket()
        #aws_s3_conn.delete_existing_check_point()
    
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
    exit_code = ModInputCISCO_CLOUD_SECURITY_ADDON().run(sys.argv)
    sys.exit(exit_code)


