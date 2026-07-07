


import os
import sys
import time
import datetime
import json

import import_declare_test

from splunklib import modularinput as smi



import input_module_workspaceone_audit_logs as input_module

bin_dir = os.path.basename(__file__)

'''
'''
class ModInputworkspaceone_audit_logs(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputworkspaceone_audit_logs, self).__init__("ta_workspaceone", "workspaceone_audit_logs", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputworkspaceone_audit_logs, self).get_scheme()
        scheme.title = ("WorkspaceOne audit logs")
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
        scheme.add_argument(smi.Argument("auth_url", title="Auth URL",
                                         description="example : https://company.worksapceoneaccess.com/SAAS/auth/oauthtoken",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("data_url", title="Data URL",
                                         description="example : https://company.worksapceoneaccess.com",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("since_date", title="Since Date",
                                         description="Must be in epoch milliseconds(13 Digits. example : 1708190225250). If it\'s empty, TA collect events from last 7 days.",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-workspaceone"

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
    exitcode = ModInputworkspaceone_audit_logs().run(sys.argv)
    sys.exit(exitcode)
