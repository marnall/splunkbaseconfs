
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
import dateutil.parser

# encoding = utf-8

def get_start_date(helper, check_point_key):
    
    # Try to get a date from the check point first
    d = helper.get_check_point(check_point_key)
    
    # If there was a check point date, retun it.
    if (d not in [None,'']):
        return d
    else:
        # No check point date, so look if a start date was specified as an argument
        start_date = helper.get_arg("start_date")
        if (start_date not in [None,'']):
            d = dateutil.parser.parse(start_date)
            return d.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        else:
            # If there was no start date specified, default to 7 days ago
            return (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
class ModInputteams_call_record(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputteams_call_record, self).__init__("ta_ms_teams", "teams_call_records", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputteams_call_record, self).get_scheme()
        scheme.title = ("Teams Call Record (New)")
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
        scheme.add_argument(smi.Argument("exclude_null_values", title="Exclude Null Values",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=True))
        scheme.add_argument(smi.Argument("start_date", title="Start Date",
                                         description="The date/time to start collecting data.  If no value is given, the input will start getting data 7 days in the past.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("endpoint", title="Endpoint",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA_MS_Teams"

    def validate_input(helper, definition):
        pass
    

    def collect_events(helper, ew):

        global_account = helper.get_arg("global_account")
        client_id = global_account["username"]
        client_secret = global_account["password"]
        tenant_id = helper.get_arg("tenant_id")
        exclude_null_values = helper.get_arg("exclude_null_values")
        endpoint = helper.get_arg("endpoint")
        input_name = helper.get_input_stanza_names()
        check_point_key = "call_record_id_last_date_%s" % helper.get_input_stanza_names()
        
        environment = helper.get_arg("environment")
        graph_base_url = azutils.get_environment_graph(environment)
        query_date = get_start_date(helper, check_point_key)

        session = azauth.get_graph_session(client_id, client_secret, tenant_id, environment, helper)
    
        if(session):
            call_record_ids_url = graph_base_url + "/%s/communications/callRecords?$select=id,startDateTime&$filter=startDateTime+gt+%s" % (endpoint, query_date)

            helper.log_debug("_Splunk_ input_name=%s Call Record IDs Graph URL used: %s" % (input_name, call_record_ids_url))
            max_dateTime = query_date
    
            response = azutils.get_items_batch_session(helper=helper, url=call_record_ids_url, session=session)
            call_record_ids = None if response == None else response['value']

            while call_record_ids:
                for call_record_id in call_record_ids:
                    # Keep track of the largest datetime seen during this query.
                    this_dateTime = call_record_id["startDateTime"]

                    if(this_dateTime > max_dateTime):
                        max_dateTime = this_dateTime
            
                    try:
                        # Get call record and index it
                        call_record_url = graph_base_url + "/%s/communications/callRecords/%s?$expand=sessions($expand=segments)" % (endpoint, call_record_id["id"])
                        helper.log_debug("_Splunk_ input_name=%s Call Record Graph URL used: %s" % (input_name, call_record_url))

                        call_record = azutils.get_item_session(helper=helper, session=session, url=call_record_url)
        
                        event = helper.new_event(
                            data=json.dumps(call_record),
                            index=helper.get_output_index())
                        ew.write_event(event)

                        # Check point the largest dateTime seen during the query
                        helper.save_check_point(check_point_key, max_dateTime)

                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 404:
                            helper.log_error("404 call record not found for callRecord ID: %s. Exception: %s" % (call_record_id, str(e)))
                            
                    except Exception as e:
                        helper.log_error("Error getting callRecord data: %s" % str(e))
                        raise e
                    
                sys.stdout.flush()
                response = azutils.handle_nextLink(helper=helper, response=response, session=session)
                call_record_ids = None if response == None else response['value']
        else:
            helper.log_error("_Splunk_ Could not get access token")

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
