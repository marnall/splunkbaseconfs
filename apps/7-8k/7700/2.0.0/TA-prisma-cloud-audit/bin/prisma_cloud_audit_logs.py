
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

import os
import sys
import time
import datetime
import json

import import_declare_test

from splunklib import modularinput as smi



import input_module_prisma_cloud_audit_logs as input_module

bin_dir = os.path.basename(__file__)

'''
'''
class ModInputprisma_cloud_audit_logs(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputprisma_cloud_audit_logs, self).__init__("ta_prisma_cloud_audit", "prisma_cloud_audit_logs", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputprisma_cloud_audit_logs, self).get_scheme()
        scheme.title = ("Prisma Cloud Audit Logs")
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
        scheme.add_argument(smi.Argument("global_account", title="Global Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("since_date", title="Since Date",
                                         description="Specify date since when audit events to be collected. Date format should be YYYY-MM-DD HH:MM:SS. If it\'s not specified then last 7 days events will be fetched.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("source_type", title="Source Type",
                                         description="defaults to prisma:audit:events. If its updated, time extraction must be added under new sourcetype.",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-prisma-cloud-audit"

    def validate_input(self, definition):
        """validate the input stanza"""
        input_module.validate_input(self, definition)

    def collect_events(self, ew):
        """write out the events"""
        input_module.collect_events(self, ew)

    def get_account_fields(self):
        account_fields = []
        account_fields.append("global_account")
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
    exitcode = ModInputprisma_cloud_audit_logs().run(sys.argv)
    sys.exit(exitcode)
