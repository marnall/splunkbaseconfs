import os
import sys
import time
import json
import import_declare_test
from splunklib import modularinput as smi
from splunktaucclib.modinput_wrapper import base_modinput as base_mi

from analytics_service import AnalyticsService

bin_dir = os.path.dirname(os.path.abspath(__file__))

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


class ModInputappdynamics_analytics_api(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputappdynamics_analytics_api, self).__init__("splunk_ta_appdynamics", "appdynamics_analytics_api",
                                                                use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = super(ModInputappdynamics_analytics_api, self).get_scheme()
        scheme.title = ("Analytics Search")
        scheme.description = ("AppDynamics Analytics Search Import")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))
        scheme.add_argument(smi.Argument("source_entry", title="Source Name",
                                         description="Enter the source name to ingest data as, if 'appdynamics_' is not at the beginning it will be prepended",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("global_account", title="Controller Account",
                                         description="unused",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("analytics_account", title="Analytics Account",
                                         description="Select the account to be used to authenticate to AppDynamics Analytics",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("duration", title="Time Duration (in minutes)",
                                         description="The time period (in minutes) that you wish to retrieve data for.  e.g.:  5 = retrieve data for the past 5 minutes.",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("query", title="Search Query",
                                         description="Enter the query e.g:  \"SELECT * FROM transactions\"",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "Splunk_TA_AppDynamics"

    def validate_input(helper, definition):
        """Implement your own validation logic to validate the input stanza configurations"""
        pass

    def collect_events(helper, ew):
        # Implement your data collection logic here
        from splunk_service import SplunkService
        from ucc_utils import Util

        '''
        Variable declarations and initializations
        '''
        #  Process each input in inputs.conf separately
        #  Get the properties for each input (stanzas in inputs.conf)
        stanzas = helper.input_stanzas
        for stanza_name in stanzas:
            opt_splunk_key = helper.get_arg('splunk_key')
            opt_duration = helper.get_arg('duration')
            opt_source = helper.get_arg('source_entry')
            opt_query = helper.get_arg('query')
            opt_analytics_account = helper.get_arg('analytics_account')
            helper.log_info(f"Collecting analytics query {opt_query} with label {opt_source}")

            idx = Util.get_output_index(helper, stanza_name)
            st = helper.get_sourcetype()

            # If there are more than 1 input of this type, the arguments will be in a dictionary so grab them out
            if type(opt_splunk_key) == dict:
                opt_splunk_key = opt_splunk_key[stanza_name]
            if type(opt_duration) == dict:
                opt_duration = opt_duration[stanza_name]
            if type(opt_source) == dict:
                opt_source = opt_source[stanza_name]
            if type(opt_query) == dict:
                opt_query = opt_query[stanza_name]

            if type(idx) == dict:
                idx = idx[stanza_name]
            if type(st) == dict:
                st = st[stanza_name]

            if not opt_source.startswith("appdynamics_"):
                opt_source = "appdynamics_" + opt_source
            splunk = SplunkService(helper, idx, st, ew)
            analytics = AnalyticsService(
                opt_analytics_account['name'],
                helper.context_meta["session_key"],
                source=opt_source,
                duration=opt_duration,
                splunk=splunk,
                external_logger=helper.logger
            )
            analytics.search(opt_query)
            splunk.log_events_ingested()
            return

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
    exitcode = ModInputappdynamics_analytics_api().run(sys.argv)
    sys.exit(exitcode)
