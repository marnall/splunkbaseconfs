import import_declare_test

import json
import sys
import os

from splunklib import modularinput as smi
from splunktaucclib.modinput_wrapper import base_modinput as base_mi 

import sb_flv
import im_dynatrace_audit_logs as input_module

bin_dir = os.path.basename(__file__)


class DYNATRACE_AUDIT_LOGS(base_mi.BaseModInput):
    
    def __init__(self):
        use_single_instance = False
        super(DYNATRACE_AUDIT_LOGS, self).__init__("siembazaar_ta_dynatrace_audit_logs", "dynatrace_audit_logs", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = smi.Scheme('dynatrace_audit_logs')
        scheme.description = 'Dynatrace Audit Logs'
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
                'dynatrace_account',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'dynatrace_license',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'dynatrace_endpoint',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'since_date',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'page_size',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'filter',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'custom_source_type',
                required_on_create=False,
            )
        )
        return scheme

    def get_app_name(self):
        return "SIEMBazaar_TA_Dynatrace_audit_logs"
    
    def validate_input(self, definition):
        """validate the input stanza"""
        input_module.validate_input(self, definition)

    def collect_events(self, ew): 
        flv_ok = sb_flv.flv(self)
        if flv_ok:
            """write out the events"""
            input_module.collect_events(self, ew)

    def get_account_fields(self):
        account_fields = []
        account_fields.append("dynatrace_account")
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
    exit_code = DYNATRACE_AUDIT_LOGS().run(sys.argv)
    sys.exit(exit_code)