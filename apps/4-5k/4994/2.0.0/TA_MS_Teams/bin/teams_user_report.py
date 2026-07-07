
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
import io
import requests
import ta_azure_utils.auth as azauth
import ta_azure_utils.utils as azutils

# encoding = utf-8



class ModInputteams_user_report(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputteams_user_report, self).__init__("ta_ms_teams", "teams_user_report", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputteams_user_report, self).get_scheme()
        scheme.title = ("Teams User Report")
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
        scheme.add_argument(smi.Argument("tenant_id", title="Tenant ID",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("environment", title="Environment",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("period", title="Period",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA_MS_Teams"

    def validate_input(helper, definition):
        pass
    

    def collect_events(helper, ew):
        
        global_account = helper.get_arg('global_account')
        client_id = global_account['username']
        client_secret = global_account['password']
        tenant_id = helper.get_arg('tenant_id')
        period = helper.get_arg('period')
        
        environment = helper.get_arg("environment")
        if(environment == "gov"):
            graph_base_url = "https://graph.microsoft.us"
        else:
            graph_base_url = "https://graph.microsoft.com"
        
        try:
            access_token = azauth.get_graph_access_token(client_id, client_secret, tenant_id, environment, helper)
        except Exception as e:
            helper.log_error('Error generating access token: {}'.format(e))
            return
    
        try:
            url = graph_base_url + "/beta/reports/getTeamsUserActivityUserDetail(period='{}')?$format=application/json".format(period)
                
            report_items = azutils.get_items(helper, access_token, url)
            for report_item in report_items:
                event=helper.new_event(
                    data=json.dumps(report_item),
                    time=report_item['reportRefreshDate'],
                    source=helper.get_input_type(), 
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype()
                )
                ew.write_event(event)
    
        except Exception as e:
            helper.log_error(e)
            raise e

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
    exitcode = ModInputteams_user_report().run(sys.argv)
    sys.exit(exitcode)
