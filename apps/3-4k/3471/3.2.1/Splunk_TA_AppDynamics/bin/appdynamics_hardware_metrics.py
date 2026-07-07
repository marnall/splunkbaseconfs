'''
    Author: John Southerland josouthe@cisco.com +1.214.734.8099 (AppDynamics Field Architect)
    Aug 12 2024: First version, retrieve high level status of all Applications, Business Transactions, Databases, and Servers
'''
import concurrent.futures
import json
import os

bin_dir = os.path.dirname(os.path.abspath(__file__))
import sys
import import_declare_test
from splunklib import modularinput as smi
from splunktaucclib.modinput_wrapper import base_modinput as base_mi


class ModInputappdynamics_hardware_metrics(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputappdynamics_hardware_metrics, self).__init__("splunk_ta_appdynamics", "appdynamics_hardware_metrics",
                                                                 use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = super(ModInputappdynamics_hardware_metrics, self).get_scheme()
        scheme.title = ("Database Metrics")
        scheme.description = ("AppDynamics Database Metric Import")
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
        scheme.add_argument(smi.Argument("tiernode_radio", title="Collect Tier, Node, or Both",
                                         description="Collect which level of metrics",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("collect_baselines_radio", title="Collect Baseline Metrics As Well",
                                         description="Collect Baseline Metrics As Well",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("compress_data_flag", title="Return one record for the duration, instead of per minute",
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

        helper.log_info("Collecting Database metrics")


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
            st = helper.get_sourcetype()
            if type(st) == dict:
                st = st[stanza_name]
            opt_baseline_flag = helper.get_arg('collect_baselines_radio')
            if type(opt_baseline_flag) == dict:
                opt_baseline_flag = opt_baseline_flag[stanza_name]
            opt_compress_data_flag = helper.get_arg('compress_data_flag')
            if type(opt_compress_data_flag) == dict:
                opt_compress_data_flag = opt_compress_data_flag[stanza_name]
            opt_tiernode_flag = helper.get_arg('tiernode_radio')
            if type(opt_tiernode_flag) == dict:
                opt_tiernode_flag = opt_tiernode_flag[stanza_name]

        helper.log_info(f"Databases: {opt_app_list}")
        helper.log_info(f"Metrics: {opt_metrics} Tier/Node: {opt_tiernode_flag}")
        helper.log_info(f"Baseline Metrics: {opt_baseline_flag} Compress Data: {opt_compress_data_flag}")
        helper.log_debug(f"controller: {appd_controller_url} account: {opt_global_account}")
        max_workers = Util.get_max_workers(helper.context_meta["session_key"])
        start_time = time.time()
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

        def get_section_as_list(data):
            # This, this is why i hate python
            if not isinstance(data, list):
                data = [data]  # Force it into a list if it's a single item
            return data

        def get_app_name(application_name):
            return application_name.split('|', 2)[0]

        def get_app_id(application_name):
            return application_name.split('|', 2)[1]


        '''The logic is all below here....'''
        if not opt_app_list:
            opt_app_list = []
            for app in get_section_as_list(controller.get_all_app_list()["apmApplications"]):
                if app["active"]:
                    opt_app_list.append(f"{app['name']}|{app['id']}")
        opt_app_list = get_section_as_list(opt_app_list)
        opt_metrics = get_section_as_list(opt_metrics)
        def process_tiernode_query(app):
            try:
                app_name = get_app_name(app)
                app_id = get_app_id(app)
                tiers = controller.get_tiers(app_id)
                for tier_name in tiers:
                    tier_id = tiers[tier_name]
                    if "cpu" in opt_metrics:
                        if "tier" in opt_tiernode_flag:
                            helper.log_info(f"Collecting CPU Metrics for {tier_name}")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Hardware Resources|CPU|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_cpu", metric)
                        if "node" in opt_tiernode_flag:
                            helper.log_info(f"Collecting CPU Metrics for {tier_name} Nodes")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Individual Nodes|*|Hardware Resources|CPU|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_cpu", metric)
                    if "disk" in opt_metrics:
                        if "tier" in opt_tiernode_flag:
                            helper.log_info(f"Collecting Disk Metrics for {tier_name}")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Hardware Resources|Disks|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_disk", metric)
                        if "node" in opt_tiernode_flag:
                            helper.log_info(f"Collecting Disk Metrics for {tier_name} Nodes")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Individual Nodes|*|Hardware Resources|Disks|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_disk", metric)
                    if "disk_detailed" in opt_metrics:
                        if "tier" in opt_tiernode_flag:
                            helper.log_info(f"Collecting Detailed Disk Metrics for {tier_name}")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Hardware Resources|Disks|*|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_disk_details", metric)
                        if "node" in opt_tiernode_flag:
                            helper.log_info(f"Collecting Detailed Disk Metrics for {tier_name} Nodes")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Individual Nodes|*|Hardware Resources|Disks|*|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_disk_details", metric)
                    if "memory" in opt_metrics:
                        if "tier" in opt_tiernode_flag:
                            helper.log_info(f"Collecting Memory Metrics for {tier_name}")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Hardware Resources|Memory|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_memory", metric)
                        if "node" in opt_tiernode_flag:
                            helper.log_info(f"Collecting Memory Metrics for {tier_name} Nodes")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Individual Nodes|*|Hardware Resources|Memory|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_memory", metric)
                    if "network" in opt_metrics:
                        if "tier" in opt_tiernode_flag:
                            helper.log_info(f"Collecting Network Metrics for {tier_name}")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Hardware Resources|Network|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_network", metric)
                        if "node" in opt_tiernode_flag:
                            helper.log_info(f"Collecting Network Metrics for {tier_name} Nodes")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Individual Nodes|*|Hardware Resources|Network|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_network", metric)
                    if "network_detailed" in opt_metrics:
                        if "tier" in opt_tiernode_flag:
                            helper.log_info(f"Collecting Detailed Network Metrics for {tier_name}")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Hardware Resources|Network|*|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_network_details", metric)
                        if "node" in opt_tiernode_flag:
                            helper.log_info(f"Collecting Detailed Network Metrics for {tier_name} Nodes")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Individual Nodes|*|Hardware Resources|Network|*|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_network_details", metric)
                    if "system" in opt_metrics:
                        if "tier" in opt_tiernode_flag:
                            helper.log_info(f"Collecting System Metrics for {tier_name}")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Hardware Resources|System|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_system", metric)
                        if "node" in opt_tiernode_flag:
                            helper.log_info(f"Collecting System Metrics for {tier_name} Nodes")
                            for metric in controller.get_metric_data(app_id, f"Application Infrastructure Performance|{tier_name}|Individual Nodes|*|Hardware Resources|System|*", opt_compress_data_flag, opt_baseline_flag):
                                metric['application_id'] = app_id
                                metric['application_name'] = app_name
                                metric['tier_id'] = tier_id
                                metric['tier_name'] = tier_name
                                helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                                splunk.send_data("appdynamics_system", metric)
            except Exception as e:
                splunk.log_exception(e)
                helper.log_warning("Error fetching Tier Node metrics for app %s: %s", app, e)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(process_tiernode_query, opt_app_list))
        except Exception as e:
            splunk.log_exception(e)

        splunk.log_events_ingested()
        end_time = time.time()
        helper.log_info(f"Completed Collecting Database Metrics, run duration: {end_time - start_time}")


if __name__ == "__main__":
    exitcode = ModInputappdynamics_hardware_metrics().run(sys.argv)
    sys.exit(exitcode)
