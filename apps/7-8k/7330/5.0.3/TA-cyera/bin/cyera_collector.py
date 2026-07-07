import ta_cyera_declare

import os
import sys
import time
import datetime
import json

import modinput_wrapper.base_modinput
from splunklib import modularinput as smi


import input_module_cyera_collector as input_module

bin_dir = os.path.basename(__file__)

'''
    Cyera Collector -- Centralized orchestrator input.
    Collects from all enabled Cyera API endpoints using a single JWT,
    shared rate limit tracking, and controlled parallelism.
'''
class ModInputcyera_collector(modinput_wrapper.base_modinput.BaseModInput):

    def __init__(self):
        if 'use_single_instance_mode' in dir(input_module):
            use_single_instance = input_module.use_single_instance_mode()
        else:
            use_single_instance = False
        super(ModInputcyera_collector, self).__init__("ta_cyera", "cyera_collector", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputcyera_collector, self).get_scheme()
        scheme.title = ("Cyera Collector (Recommended)")
        scheme.description = ("Collects from all enabled Cyera API endpoints in a single coordinated process. Eliminates rate limit competition between separate inputs.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        scheme.add_argument(smi.Argument("cyera_account", title="Cyera Account",
                                         description="Create an API clientID and Secret through your Cyera Application by following the KB article here: (https://support.cyera.io/hc/en-us/articles/20612742894231-Cyera-API).",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("enable_events", title="Collect Events",
                                         description="Enable collection of Cyera events.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("enable_issues", title="Collect Issues",
                                         description="Enable collection of Cyera issues.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("enable_datastores", title="Collect Datastores",
                                         description="Enable collection of Cyera datastores.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("enable_classifications", title="Collect Classifications",
                                         description="Enable collection of Cyera classifications.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("enable_audit", title="Collect Audit Logs",
                                         description="Enable collection of Cyera audit logs.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("retrieve_all_datastores", title="Retrieve All Datastores Every Time",
                                         description="Retrieve all datastores every run instead of incremental changes.",
                                         required_on_create=False,
                                         required_on_edit=False))
        # Per-endpoint interval overrides
        scheme.add_argument(smi.Argument("interval_events", title="Events Interval",
                                         description="Collection interval for events in seconds. Leave blank to use the base interval.",
                                         required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("interval_issues", title="Issues Interval",
                                         description="Collection interval for issues in seconds. Leave blank to use the base interval.",
                                         required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("interval_datastores", title="Datastores Interval",
                                         description="Collection interval for datastores in seconds. Leave blank to use the base interval.",
                                         required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("interval_classifications", title="Classifications Interval",
                                         description="Collection interval for classifications in seconds. Leave blank to use the base interval.",
                                         required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("interval_audit", title="Audit Interval",
                                         description="Collection interval for audit logs in seconds. Leave blank to use the base interval.",
                                         required_on_create=False, required_on_edit=False))
        # Per-endpoint index overrides
        scheme.add_argument(smi.Argument("index_events", title="Events Index",
                                         description="Target index for events. Leave blank to use the base index.",
                                         required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("index_issues", title="Issues Index",
                                         description="Target index for issues. Leave blank to use the base index.",
                                         required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("index_datastores", title="Datastores Index",
                                         description="Target index for datastores. Leave blank to use the base index.",
                                         required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("index_classifications", title="Classifications Index",
                                         description="Target index for classifications. Leave blank to use the base index.",
                                         required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("index_audit", title="Audit Index",
                                         description="Target index for audit logs. Leave blank to use the base index.",
                                         required_on_create=False, required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-cyera"

    def validate_input(self, definition):
        """validate the input stanza"""
        input_module.validate_input(self, definition)

    def collect_events(self, ew):
        """write out the events"""
        input_module.collect_events(self, ew)

    def get_account_fields(self):
        account_fields = []
        account_fields.append("cyera_account")
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        checkbox_fields.append("enable_events")
        checkbox_fields.append("enable_issues")
        checkbox_fields.append("enable_datastores")
        checkbox_fields.append("enable_classifications")
        checkbox_fields.append("enable_audit")
        checkbox_fields.append("retrieve_all_datastores")
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
    exitcode = ModInputcyera_collector().run(sys.argv)
    sys.exit(exitcode)
