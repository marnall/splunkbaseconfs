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


class ModInputappdynamics_events(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputappdynamics_events, self).__init__("splunk_ta_appdynamics", "appdynamics_events_policy", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = super(ModInputappdynamics_events, self).get_scheme()
        scheme.title = ("AppDynamics Events")
        scheme.description = ("Events Data for different types of entities in AppDynamics")
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
        scheme.add_argument(smi.Argument("application_list", title="Applications List",
                                         description="select the applications and events you want to ingest",
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
        from oauth_helper import OAuth, BasicAuth
        from controller_service import ControllerService
        from splunk_service import SplunkService
        from ucc_utils import Util
        from appdynamics_utils import normalize_controller_url
        import json
        import time

        helper.log_info("Collecting Events")
        

        #  Process each account input in inputs.conf separately
        #  Get the properties for each input (stanzas in inputs.conf)
        stanzas = helper.input_stanzas
        for stanza_name in stanzas:
            opt_duration = helper.get_arg('duration')
            if type(opt_duration) == dict:
                opt_duration = opt_duration[stanza_name]
            opt_global_account = helper.get_arg('global_account')
            opt_application_list = helper.get_arg('application_list')
            if type(opt_application_list) == dict:
                opt_application_list = opt_application_list[stanza_name]
            opt_event_filter = helper.get_arg('event_filter')
            if type(opt_event_filter) == dict:
                opt_event_filter = opt_event_filter[stanza_name]
            appd_controller_url = normalize_controller_url(opt_global_account['appd_controller_url'])
            idx = Util.get_output_index(helper, stanza_name)
            if type(idx) == dict:
                idx = idx[stanza_name]
            st = helper.get_sourcetype()
            if type(st) == dict:
                st = st[stanza_name]

        helper.log_debug(f"controller: {appd_controller_url} account: {opt_global_account}")
        max_workers = Util.get_max_workers(helper.context_meta["session_key"])
        start_time = time.time()

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

        def flatten_json_event_filter(json_string):
            helper.log_debug(f"event filter: {json_string}")
            data = json.loads(json_string)
            selected_values = []
            for group in data['groups']:
                for item in group['items']:
                    if item['selected']:
                        selected_values.append(item['value'])
            return '~'.join(selected_values)

        '''The logic is all below here....'''
        #opt_event_filter = flatten_json_event_filter(opt_event_filter)
        helper.log_debug(f"event filter: {opt_event_filter}")
        helper.log_debug(f"application list: '{opt_application_list}'")
        if not opt_application_list:
            opt_application_list = []
            applications = controller.get_all_app_list()
            for app in get_section_as_list(applications["apmApplications"]):
                if app["active"]:
                    opt_application_list.append(f"unused|{app['id']}|{app['name']}")

            for app in get_section_as_list(applications["analyticsApplication"]):
                if app["active"]:
                    opt_application_list.append(f"unused|{app['id']}|{app['name']}")

            for app in get_section_as_list(applications["dbMonApplication"]):
                if app["active"]:
                    opt_application_list.append(f"unused|{app['id']}|{app['name']}")

            for app in get_section_as_list(applications["eumWebApplications"]):
                if app["active"]:
                    opt_application_list.append(f"unused|{app['id']}|{app['name']}")

            for app in get_section_as_list(applications["mobileAppContainers"]):
                if app["active"]:
                    opt_application_list.append(f"unused|{app['id']}|{app['name']}")

            for app in get_section_as_list(applications["simApplication"]):
                if app["active"]:
                    opt_application_list.append(f"unused|{app['id']}|{app['name']}")
        app_list = []
        for application in get_section_as_list(opt_application_list):
            app_list.append(get_app_id(application))

        def process_events_query(app):
            try:
                app_events = controller.get_events(opt_event_filter, [app])
                for event in app_events:
                    splunk.send_data("appdynamics_events", event)
            except Exception as e:
                splunk.log_exception(e)
                helper.log_warning("Error fetching events for app %s: %s", app, e)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = executor.map(process_events_query, app_list)
        except Exception as e:
            splunk.log_exception(e)
        splunk.log_events_ingested()
        end_time = time.time()
        helper.log_info(f"Completed Collecting Events, run duration: {end_time - start_time}")


if __name__ == "__main__":
    exitcode = ModInputappdynamics_events().run(sys.argv)
    sys.exit(exitcode)