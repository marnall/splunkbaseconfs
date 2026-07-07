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


class ModInputappdynamics_database_metrics(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputappdynamics_database_metrics, self).__init__("splunk_ta_appdynamics", "appdynamics_database_metrics",
                                                                 use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = super(ModInputappdynamics_database_metrics, self).get_scheme()
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
        scheme.add_argument(smi.Argument("database_list", title="Databases to Collect Metrics for",
                                         description="select the databases",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("metrics_to_collect", title="Metrics to Collect",
                                         description="select the metrics you want to ingest",
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
            opt_db_list = helper.get_arg('database_list')
            if type(opt_db_list) == dict:
                opt_db_list = opt_db_list[stanza_name]
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

        helper.log_info(f"Databases: {opt_db_list}")
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

        def get_section_as_list(data):
            # This, this is why i hate python
            if not isinstance(data, list):
                data = [data]  # Force it into a list if it's a single item
            return data

        def get_app_id(application_name):
            return application_name.split('|', 3)[2]

        def get_db_id(application_name):
            return application_name.split('|', 2)[1]

        def get_db_name(application_name):
            return application_name.split('|', 2)[0]

        '''The logic is all below here....'''
        if not opt_db_list: #If database list isn't an input, just get them all
            opt_db_list = []
            application = controller.get_database_application()
            databases = controller.get_databases()
            for db in get_section_as_list(databases):
                opt_db_list.append(f"{db['name']}|{db['id']}|{application['id']}")
            helper.log_info(f"No Databases Selected, All Databases: {opt_db_list}")
        opt_db_list = get_section_as_list(opt_db_list)
        opt_metrics = get_section_as_list(opt_metrics)
        for database in opt_db_list:
            try:
                db_name = get_db_name(database)
                if "custom_metrics" in opt_metrics:
                    helper.log_info(f"Collecting Custom Metrics for {db_name}")
                    metric_data = controller.get_metric_data(get_app_id(database), f"Databases|{get_db_name(database)}|Custom Metric|*", opt_compress_data_flag, opt_baseline_flag)
                    if metric_data is not None:
                        for metric in metric_data:
                            metric['database_id'] = get_db_id(database)
                            metric['database_name'] = get_db_name(database)
                            helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                            splunk.send_data("appdynamics_custom_metrics", metric)
                if "hardware" in opt_metrics:
                    helper.log_info("Collecting Hardware Resource Metrics for {db_name}")
                    metric_data = controller.get_metric_data(get_app_id(database), f"Databases|{get_db_name(database)}|Hardware Resources|*|*", opt_compress_data_flag, opt_baseline_flag)
                    if metric_data is not None:
                        for metric in metric_data:
                            metric['database_id'] = get_db_id(database)
                            metric['database_name'] = get_db_name(database)
                            helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                            splunk.send_data("appdynamics_hardware", metric)
                if "kpi" in opt_metrics:
                    helper.log_info("Collecting KPI Metrics for {db_name}")
                    metric_data = controller.get_metric_data(get_app_id(database), f"Databases|{get_db_name(database)}|KPI|*", opt_compress_data_flag, opt_baseline_flag)
                    if metric_data is not None:
                        for metric in metric_data:
                            metric['database_id'] = get_db_id(database)
                            metric['database_name'] = get_db_name(database)
                            helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                            splunk.send_data("appdynamics_kpi", metric)
                if "performance" in opt_metrics:
                    helper.log_info("Collecting Performance Metrics for {db_name}")
                    metric_data = controller.get_metric_data(get_app_id(database), f"Databases|{get_db_name(database)}|Performance|*", opt_compress_data_flag, opt_baseline_flag)
                    if metric_data is not None:
                        for metric in metric_data:
                            metric['database_id'] = get_db_id(database)
                            metric['database_name'] = get_db_name(database)
                            helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                            splunk.send_data("appdynamics_performance", metric)
                if "server_stats" in opt_metrics:
                    helper.log_info("Collecting Server Statistic Metrics for {db_name}")
                    metric_data = controller.get_metric_data(get_app_id(database), f"Databases|{get_db_name(database)}|Server Statistic|*", opt_compress_data_flag, opt_baseline_flag)
                    if metric_data is not None:
                        for metric in metric_data:
                            metric['database_id'] = get_db_id(database)
                            metric['database_name'] = get_db_name(database)
                            helper.log_debug(f"Metric Data: {json.dumps(metric)}")
                            splunk.send_data("appdynamics_server_stats", metric)
            except Exception as e:
                splunk.log_exception(e)

        splunk.log_events_ingested()
        helper.log_info("Completed Collecting Database Metrics")


if __name__ == "__main__":
    exitcode = ModInputappdynamics_database_metrics().run(sys.argv)
    sys.exit(exitcode)
