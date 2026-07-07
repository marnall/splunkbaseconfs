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


class ModInputappdynamics_status(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputappdynamics_status, self).__init__("splunk_ta_appdynamics", "appdynamics_status", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = super(ModInputappdynamics_status, self).get_scheme()
        scheme.title = ("High Level Status")
        scheme.description = ("Status of all Applications, Business Transactions, Databases, and Servers being monitored in AppDynamics")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))
        scheme.add_argument(smi.Argument("global_account", title="Global Account",
                                         description="Select the account to be used to authenticate to AppDynamics.",
                                         required_on_create=True,
                                         required_on_edit=True))
        scheme.add_argument(smi.Argument("duration", title="Time Duration (in minutes)",
                                         description="The time period (in minutes) that you wish to retrieve data for.  e.g.:  5 = retrieve data for the past 5 minutes. [5-60]",
                                         required_on_create=True,
                                         required_on_edit=True))
        scheme.add_argument(smi.Argument("metrics_to_collect", title="Metrics to Collect",
                                         description="select the metrics you want to ingest",
                                         required_on_create=True,
                                         required_on_edit=True))
        scheme.add_argument(smi.Argument("application_list", title="Application list",
                                         description="...",
                                         required_on_create=False,
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
        from controller_service import ControllerService
        from splunk_service import SplunkService
        from ucc_utils import Util
        from appdynamics_utils import normalize_controller_url

        helper.log_info("Collecting metrics")

        #  Process each account input in inputs.conf separately
        #  Get the properties for each input (stanzas in inputs.conf)
        stanzas = helper.input_stanzas
        helper.log_debug("Stanzas: " + str(stanzas))
        for stanza_name in stanzas:
            helper.log_debug(f"Stanza name: {stanza_name}")
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

        helper.log_debug(f"controller: {appd_controller_url} account: {opt_global_account} metrics: {opt_metrics}")
        max_workers = Util.get_max_workers(helper.context_meta["session_key"])

        controller = ControllerService(
            helper=helper,
            global_account=opt_global_account,
            duration=opt_duration,
            session_key=helper.context_meta["session_key"],
            source=helper.get_arg('name')
        )

        splunk = SplunkService(helper, idx, st, ew)

        def get_section_as_list(data):
            # This, this is why i hate python
            if not isinstance(data, list):
                data = [data]  # Force it into a list if it's a single item
            return data

        def get_app_name(application_name):
            return application_name.split('|', 2)[0]

        def get_app_id(application_name):
            return application_name.split('|', 2)[1]

        ''' end of declarations, followed by the actual code'''
        '''The logic is all below here....'''

        if not opt_app_list:
            opt_app_list = []
            for app in get_section_as_list(controller.get_all_app_list()["apmApplications"]):
                if app["active"]:
                    opt_app_list.append(f"{app['name']}|{app['id']}")
        opt_app_list = get_section_as_list(opt_app_list)

        try:
            app_list = []
            for app in opt_app_list:
                app_list.append(get_app_id(app))
        except Exception as e:
            splunk.log_exception(e)
            return

        try:
            if "Application Status" in opt_metrics:
                helper.log_info("Collecting Application Status Metrics")
                if app_list:
                    app_metrics_data = controller.get_application_summary(app_list)
                    if app_metrics_data:
                        for app_metrics in app_metrics_data:
                            splunk.send_data("application_status", app_metrics)
        except Exception as e:
            splunk.log_exception(e)

        def process_remote_services_query(app):
            try:
                remote_services = controller.get_remote_services_status(app)
                for data in remote_services:
                    splunk.send_data("remote_services", data)
            except Exception as e:
                splunk.log_exception(e)
                helper.log_warning("Error fetching Remote Service status for app %s: %s", app, e)

        try:
            if "Remote Services Status" in opt_metrics:
                helper.log_info("Collecting Remote Services Status Metrics")
                if app_list:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        list(executor.map(process_remote_services_query, app_list))
        except Exception as e:
            splunk.log_exception(e)

        def process_tiernode_query(app):
            try:
                tier_data, node_data = controller.get_tier_node_status(app)
                if tier_data:
                    for tier in tier_data:
                        splunk.send_data("tier_status", tier_data[tier])
                if node_data:
                    for node in node_data:
                        splunk.send_data("node_status", node)
            except Exception as e:
                splunk.log_exception(e)
                helper.log_warning("Error fetching Tier Node status for app %s: %s", app, e)

        try:
            if "Tier Node Status" in opt_metrics:
                helper.log_info("Collecting Tier and Node Status Metrics")
                if app_list:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        list(executor.map(process_tiernode_query, app_list))
        except Exception as e:
            splunk.log_exception(e)

        def process_bt_query(app):
            try:
                bt_data = controller.get_application_business_transactions([app])
                if bt_data is not None:
                    for business_transaction in bt_data:
                        splunk.send_data("business_transaction_status", business_transaction)
            except Exception as e:
                splunk.log_exception(e)
                helper.log_warning("Error fetching BT status for app %s: %s", app, e)

        try:
            if "Business Transactions" in opt_metrics:
                helper.log_info("Collecting Business Transaction Status Metrics")
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    list(executor.map(process_bt_query, app_list))
        except Exception as e:
            splunk.log_exception(e)

        try:
            if "Database Status" in opt_metrics:
                helper.log_info("Collecting Database Status Metrics")
                db_data = controller.get_database_summary()
                if db_data:
                    for db in db_data:
                        splunk.send_data("database_status", db)
        except Exception as e:
            splunk.log_exception(e)

        try:
            if "Server Status" in opt_metrics:
                helper.log_info("Collecting Server Status Metrics")
                server_summary = controller.get_server_summary()
                for attribute, value in server_summary.items():
                    splunk.send_data("server_status", value)
        except Exception as e:
            splunk.log_exception(e)

        def process_security_query(app):
            try:
                security_summaries = controller.get_application_security_summary([app])
                for security_summary in security_summaries:
                    splunk.send_data("application_security", security_summary)
            except Exception as e:
                splunk.log_exception(e)
                helper.log_warning("Error fetching secure app status for app %s: %s", app, e)

        try:
            if "Application Security Status" in opt_metrics:
                helper.log_info("Collecting Application Security Status Metrics")
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    list(executor.map(process_security_query, app_list))
        except Exception as e:
            splunk.log_exception(e)

        try:
            if "Web User Experience" in opt_metrics:
                helper.log_info("Collecting DEM Web Status Metrics")
                web_summaries = controller.get_dem_web_summary()
                for web_summary in web_summaries:
                    splunk.send_data("dem_web", web_summary)
        except Exception as e:
            splunk.log_exception(e)

        try:
            if "Mobile User Experience" in opt_metrics:
                helper.log_info("Collecting DEM Mobile Status Metrics")
                mobile_summaries = controller.get_dem_mobile_summary()
                for mobile_summary in mobile_summaries:
                    splunk.send_data("dem_mobile", mobile_summary)
        except Exception as e:
            splunk.log_exception(e)

        splunk.log_events_ingested()
        helper.log_info("Completed Collecting Status Metrics")


if __name__ == "__main__":
    exitcode = ModInputappdynamics_status().run(sys.argv)
    sys.exit(exitcode)