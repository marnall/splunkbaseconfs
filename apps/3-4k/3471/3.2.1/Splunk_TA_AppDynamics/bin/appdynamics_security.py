'''
    Author: John Southerland josouthe@cisco.com +1.214.734.8099 (AppDynamics Field Architect)
    Aug 12 2024: First version, retrieve high level status of all Applications, Business Transactions, Databases, and Servers
'''
import concurrent.futures
import copy
import json
import os
from datetime import timezone, datetime

bin_dir = os.path.dirname(os.path.abspath(__file__))
import sys
import import_declare_test
from splunklib import modularinput as smi
from splunktaucclib.modinput_wrapper import base_modinput as base_mi


class ModInputappdynamics_security(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputappdynamics_security, self).__init__(
            "splunk_ta_appdynamics",
            "appdynamics_security",
            use_single_instance
        )
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = super(ModInputappdynamics_security, self).get_scheme()
        scheme.title = ("SecureApp Data")
        scheme.description = ("Secure App Data in AppDynamics")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))
        scheme.add_argument(smi.Argument("global_account", title="Global Account",
                                         description="Select the account to be used to authenticate to AppDynamics.",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("duration", title="Time Duration (in minutes)",
                                         description="The time period (in minutes) that you wish to retrieve data for.  e.g.:  5 = retrieve data for the past 5 minutes. [5-60]",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("application_list", title="Applications to Collect Metrics for",
                                         description="select the applications",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("metrics_to_collect", title="Metrics to Collect",
                                         description="select the metrics you want to ingest",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "Splunk_TA_AppDynamics"

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

    def validate_input(helper, definition):
        pass

    def collect_events(helper, ew):
        from oauth_helper import OAuth, BasicAuth
        from controller_service import ControllerService
        from splunk_service import SplunkService
        from ucc_utils import Util
        from appdynamics_utils import normalize_controller_url
        import time
        import json

        helper.log_info("Collecting metrics")

        #  Process each account input in inputs.conf separately
        #  Get the properties for each input (stanzas in inputs.conf)
        stanzas = helper.input_stanzas
        for stanza_name in stanzas:
            opt_duration = helper.get_arg('duration')
            if type(opt_duration) == dict:
                opt_duration = opt_duration[stanza_name]
            opt_global_account = helper.get_arg('global_account')
            opt_metrics = helper.get_arg('metrics_to_collect')
            opt_application_list = helper.get_arg('application_list')
            if type(opt_application_list) == dict:
                opt_application_list = opt_application_list[stanza_name]
            if type(opt_metrics) == dict:
                opt_metrics = opt_metrics[stanza_name]
            appd_controller_url = normalize_controller_url(opt_global_account['appd_controller_url'])
            idx = Util.get_output_index(helper, stanza_name)
            if type(idx) == dict:
                idx = idx[stanza_name]
            st = helper.get_sourcetype()
            if type(st) == dict:
                st = st[stanza_name]

        helper.log_debug(f"controller: {appd_controller_url} account: {opt_global_account}")
        helper.log_debug(f"metrics: {opt_metrics}")
        helper.log_debug(f"application_list: {opt_application_list}")
        max_workers = Util.get_max_workers(helper.context_meta["session_key"])
        start_time = time.time()
        now = round(time.time() * 1000)
        timeRangeStart = now - (int(opt_duration) * 60000)
        timeRangeEnd = now

        controller = ControllerService(
            helper=helper,
            global_account=opt_global_account,
            duration=opt_duration,
            session_key=helper.context_meta["session_key"],
            source=helper.get_arg('name')
        )

        splunk = SplunkService(helper, idx, st, ew)

        ''' end of declarations, followed by the actual code'''

        '''The logic is all below here....'''
        def process_app_security_query(application):
            try:
                if "attack_counts" in opt_metrics:
                    data = copy.deepcopy(application)
                    data['attacks'] = controller.get_application_security_attack_counts(application['appdApplicationId'])
                    splunk.send_data("application_security_attack_counts", data)
                    attacks = controller.get_application_security_attacks(application['appdApplicationId'])
                    if attacks is not None:
                        for attack in attacks:
                            splunk.send_data("application_security_attacks", attack)
                    ''' This new public api isn't quite ready to replace the private api, so we will comment out this work for a later date'''
                    '''new_data = controller.get_application_security_attacks_public_api(application['appdApplicationId'])
                    if new_data is not None:
                        for attack in new_data:
                            splunk.send_data("application_security_attacks_new", attack)'''
                if "business_risk" in opt_metrics:
                    data = copy.deepcopy(application)
                    data['business_risk'] = controller.get_application_security_business_risk(application['appdApplicationId'])
                    splunk.send_data("application_security_business_risk", data)
                if "vulnerabilities" in opt_metrics:
                    data = copy.deepcopy(application)
                    data['vulnerabilities_count'] = controller.get_application_security_vulnerabilities_count(application['appdApplicationId'])
                    splunk.send_data("application_security_vulnerability_counts", data)
                    vulnerabilites = controller.get_application_security_vulnerabilities(application['appdApplicationId'])
                    if vulnerabilites is not None:
                        for vuln in vulnerabilites:
                            splunk.send_data("application_security_vulnerabilities", vuln)
                '''
                #This is not working because of the load generated, disabling until we can figure out a better way:
                if "business_transactions" in opt_metrics:
                    for btData in controller.get_application_security_business_transactions():
                        splunk.send_data("business_transactions_security", btData)
                '''
            except Exception as e:
                splunk.log_exception(e)
                helper.log_warning("Error fetching security status for app %s: %s", application, e)

        try:
            applications = controller.get_application_security_list(opt_application_list)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(process_app_security_query, applications))
        except Exception as e:
            splunk.log_exception(e)

        splunk.log_events_ingested()
        end_time = time.time()
        helper.log_info(f"Completed Collecting Security Data, run duration: {end_time - start_time}")


if __name__ == "__main__":
    exitcode = ModInputappdynamics_security().run(sys.argv)
    sys.exit(exitcode)
