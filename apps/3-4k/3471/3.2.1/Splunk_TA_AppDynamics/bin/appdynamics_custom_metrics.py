'''
    Author: John Southerland josouthe@cisco.com +1.214.734.8099 (AppDynamics Field Architect)
    Aug 12 2024: First version, retrieve high level status of all Applications, Business Transactions, Databases, and Servers
'''
import json
import os

bin_dir = os.path.dirname(os.path.abspath(__file__))
import sys
import import_declare_test
from splunklib import modularinput as smi
from splunktaucclib.modinput_wrapper import base_modinput as base_mi


class ModInputappdynamics_custom_metrics(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputappdynamics_custom_metrics, self).__init__("splunk_ta_appdynamics", "appdynamics_custom_metrics",
                                                                 use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = super(ModInputappdynamics_custom_metrics, self).get_scheme()
        scheme.title = ("Custom Metrics")
        scheme.description = ("AppDynamics Custom Metric Import")
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
        scheme.add_argument(smi.Argument("application_list", title="Applications to Collect Custom Metrics for",
                                         description="select the applications",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("metrics_to_collect", title="Metrics to Collect",
                                         description="select the metrics you want to ingest",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("collect_baselines_radio", title="Collect Baseline Metrics As Well",
                                         description="Collect Baseline Metrics As Well",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("source_type_entry", title="Source Type",
                                         description="Splunk Key to ingest metrics as",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("source_entry", title="Source Name",
                                         description="Splunk Key to ingest metrics as",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(
            smi.Argument("compress_data_flag", title="Return one record for the duration, instead of per minute",
                         description="Return one record for the duration, instead of per minute",
                         required_on_create=True,
                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "Splunk_TA_AppDynamics"

    def get_account_fields(self):
        account_fields = []
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = ['compress_data_flag']
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

        helper.log_info("Collecting Custom metrics")


        #  Process each account input in inputs.conf separately
        #  Get the properties for each input (stanzas in inputs.conf)
        stanzas = helper.input_stanzas
        for stanza_name in stanzas:
            opt_duration = helper.get_arg('duration')
            if type(opt_duration) == dict:
                opt_duration = opt_duration[stanza_name]
            opt_global_account = helper.get_arg('global_account')
            opt_metrics = helper.get_arg('metrics_to_collect')
            if type(opt_metrics) == dict:
                opt_metrics = opt_metrics[stanza_name]
            opt_app_list = helper.get_arg('application_list')
            if type(opt_app_list) == dict:
                opt_app_list = opt_app_list[stanza_name]
            appd_controller_url = normalize_controller_url(opt_global_account['appd_controller_url'])
            idx = Util.get_output_index(helper, stanza_name)
            if type(idx) == dict:
                idx = idx[stanza_name]
            st = helper.get_arg('source_type_entry')
            if type(st) == dict:
                st = st[stanza_name]
            if not st.startswith("appdynamics_"):
                st = "appdynamics_" + opt_source
            opt_baseline_flag = helper.get_arg('collect_baselines_radio')
            if type(opt_baseline_flag) == dict:
                opt_baseline_flag = opt_baseline_flag[stanza_name]
            opt_compress_data_flag = helper.get_arg('compress_data_flag')
            if type(opt_compress_data_flag) == dict:
                opt_compress_data_flag = opt_compress_data_flag[stanza_name]
            opt_source = helper.get_arg('source_entry')
            if type(opt_source) == dict:
                opt_source = opt_source[stanza_name]
            if not opt_source.startswith("appdynamics_"):
                opt_source = "appdynamics_" + opt_source

        helper.log_info(f"Applications: {opt_app_list}")
        helper.log_info(f"Metrics: {opt_metrics}")
        helper.log_info(f"Baseline Metrics: {opt_baseline_flag} Compress Data: {opt_compress_data_flag}")
        helper.log_debug(f"controller: {appd_controller_url} account: {opt_global_account}")
        app_id_map = {}
        app_baseline_map = {}

        controller = ControllerService(
            helper=helper,
            global_account=opt_global_account,
            duration=opt_duration,
            session_key=helper.context_meta["session_key"],
            source=helper.get_arg('name')
        )

        splunk = SplunkService( helper, idx, st, ew)

        ''' end of declarations, followed by the actual code'''

        def get_app_id(application_name):
            return application_name.split('|', 2)[1]

        def get_app_name(application_name):
            return application_name.split('|', 2)[2]

        def get_section_as_list(data):
            # This, this is why i hate python
            if not isinstance(data, list):
                data = [data]  # Force it into a list if it's a single item
            return data

        '''The logic is all below here....'''
        if not opt_app_list:  # default to all apps when empty; validator often ensures apps selected
            opt_app_list = []
            applications = controller.get_all_app_list()
            for app in get_section_as_list(applications["apmApplications"]):
                if app["active"]:
                    opt_app_list.append(f"unused|{app['id']}|{app['name']}")

            for app in get_section_as_list(applications["analyticsApplication"]):
                if app["active"]:
                    opt_app_list.append(f"unused|{app['id']}|{app['name']}")

            for app in get_section_as_list(applications["dbMonApplication"]):
                if app["active"]:
                    opt_app_list.append(f"unused|{app['id']}|{app['name']}")

            for app in get_section_as_list(applications["eumWebApplications"]):
                if app["active"]:
                    opt_app_list.append(f"unused|{app['id']}|{app['name']}")

            for app in get_section_as_list(applications["mobileAppContainers"]):
                if app["active"]:
                    opt_app_list.append(f"unused|{app['id']}|{app['name']}")

            for app in get_section_as_list(applications["simApplication"]):
                if app["active"]:
                    opt_app_list.append(f"unused|{app['id']}|{app['name']}")
        for application in get_section_as_list(opt_app_list):
            for metric_path in opt_metrics.split(","):
                helper.log_info(f"Collecting Custom Metrics for '{application}' path: '{metric_path}'")
                try:
                    for metric in controller.get_metric_data(get_app_id(application), metric_path, opt_compress_data_flag, opt_baseline_flag):
                        metric['application_id'] = get_app_id(application)
                        metric['application_name'] = get_app_name(application)
                        helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                        splunk.send_data(opt_source, metric)
                except Exception as e:
                    splunk.log_exception(e)

        splunk.log_events_ingested()
        helper.log_info("Completed Collecting Custom Metrics")


if __name__ == "__main__":
    exitcode = ModInputappdynamics_custom_metrics().run(sys.argv)
    sys.exit(exitcode)
