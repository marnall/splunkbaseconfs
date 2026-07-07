
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
import requests
import ta_azure_utils.auth as azauth
import ta_azure_utils.utils as azutils

# encoding = utf-8


def get_call_record_ids(path):
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            yield file
            
class ModInputteams_call_record(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputteams_call_record, self).__init__("ta_ms_teams", "teams_call_record", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputteams_call_record, self).get_scheme()
        scheme.title = ("Teams Call Record (Deprecated)")
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
        scheme.add_argument(smi.Argument("endpoint", title="Endpoint",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("max_batch_size", title="Max Batch Size",
                                         description="Specify the maximum number of call records retrieved per interval.",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA_MS_Teams"

    def validate_input(helper, definition):
        try:
            int(definition.parameters.get('max_batch_size'))
        except ValueError:
            raise ValueError("Max Batch Size should be an integer without commas.")
    

    def collect_events(helper, ew):
        global_account = helper.get_arg("global_account")
        client_id = global_account["username"]
        client_secret = global_account["password"]
        tenant_id = helper.get_arg("tenant_id")
        endpoint = helper.get_arg("endpoint")
        max_batch_size = int(helper.get_arg("max_batch_size"))
        
        check_point_dir = helper.context_meta["checkpoint_dir"]
        mod_input_dir = os.path.abspath(os.path.join(check_point_dir, os.pardir))
        webhook_dir = os.path.join(mod_input_dir,"teams_webhook")
        
        environment = helper.get_arg("environment")
        if(environment == "gov"):
            graph_base_url = "https://graph.microsoft.us/%s" % endpoint
        else:
            graph_base_url = "https://graph.microsoft.com/%s" % endpoint
    
        access_token = azauth.get_graph_access_token(client_id, client_secret, tenant_id, environment, helper)
    
        if(access_token):
    
            call_record_ids = get_call_record_ids(webhook_dir)
            record_count = 0
    
            for call_record_id in call_record_ids:
                if record_count >= max_batch_size:
                    break
                else:
                    record_count = record_count + 1
                try:
                    # Get call record and index it
                    url = graph_base_url + "/communications/callRecords/%s?$expand=sessions($expand=segments)" % call_record_id
                    call_record = azutils.get_item(helper, access_token, url)
    
                    event = helper.new_event(
                        data=json.dumps(call_record),
                        index=helper.get_output_index())
                    ew.write_event(event)
    
                    # Delete checkpoint file
                    os.remove(os.path.join(webhook_dir, call_record_id))
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        helper.log_error("404 call record not found for callRecord ID: %s. Exception: %s" % (call_record_id, str(e)))
                        os.remove(os.path.join(webhook_dir, call_record_id))
                        
                except Exception as e:
                    helper.log_error("Error getting callRecord data: %s" % str(e))
                    #raise e
        else:
            helper.log_error("Could not get access token")

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
    exitcode = ModInputteams_call_record().run(sys.argv)
    sys.exit(exitcode)
