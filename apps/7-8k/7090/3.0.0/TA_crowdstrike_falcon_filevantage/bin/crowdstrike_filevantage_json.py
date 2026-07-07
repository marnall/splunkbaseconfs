import import_declare_test


from datetime import datetime, timedelta, timezone
from os import path
import sys
import json
from splunklib import modularinput as smi
from splunktaucclib.modinput_wrapper import base_modinput  as base_mi

#CrowdStrike local imports
import crowdstrike_constants as const
from CS_FileVantage_Get_IDs import Get_CS_IDs

bin_dir  = path.basename(__file__)

class ModInputCROWDSTRIKE_FILEVANTAGE_JSON(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputCROWDSTRIKE_FILEVANTAGE_JSON, self).__init__("TA_crowdstrike_falcon_filevantage", "crowdstrike_filevantage_json", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputCROWDSTRIKE_FILEVANTAGE_JSON, self).get_scheme()
        scheme.title = ("CrowdStrike Falcon Filevantage")
        scheme.description = ("Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(
            smi.Argument("name", title="Name",description="", required_on_create=True))

        scheme.add_argument(
            smi.Argument('account', required_on_create=True))

        scheme.add_argument(smi.Argument("cloud", title="Select Cloud Environment",
                                         description="Select the appropriate cloud environment for the Falcon Instance",
                                         required_on_create=True,
                                         required_on_edit=False))

        scheme.add_argument(smi.Argument("timestamp_selection", title="Select Timestamp Field",
                                         description="Select the timestamp field to use for events",
                                         required_on_create=True,
                                         required_on_edit=False))

        scheme.add_argument(smi.Argument("severity", title="Select Severity",
                                         description="Select a specific severity (default is All).",
                                         required_on_create=True,
                                         required_on_edit=False))

        scheme.add_argument(smi.Argument("start_date", title="Start Date (optional)",
                                         description="Only collect data published on or after this date.",
                                         required_on_create=False,
                                         required_on_edit=False))

        return scheme

    def validate_input(self, definition):
        start_date  = definition.parameters.get('start_date')

        #validate date format is correct
        if start_date is not None:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Incorrect data format, should be YYYY-MM-DD")

    def get_app_name(self):
        return "TA_crowdstrike_falcon_filevantage"

    def collect_events(helper, ew):
        #collect the TA version from the manifest file
        basepath = path.dirname(__file__)
        filepath = path.abspath(path.join(basepath, "..", "app.manifest"))

        with open(filepath, 'r') as manifest:
            manifest_file = json.load(manifest)
            version = manifest_file['info']['id']['version']

        #get and set log level
        loglevel = helper.get_log_level()
        helper.set_log_level(loglevel)

        #get stanza name
        stanza_name = str(helper.get_input_stanza_names())
        log_label = f"CS FileVantage TA {version} {stanza_name} :"

        helper.log_info(f"{log_label} Configuration - Logging level is currently set to: {loglevel}")
        helper.log_info(f"{log_label} Configuration - Input Name: {stanza_name}")

        #configure useragent value for API calls
        user_agent = f"Splunk_TA_FileVantage_v{version}"

        #set API call limit
        limit = 5000

        #get severity value
        severity = str(helper.get_arg('severity'))
        helper.log_info(f"{log_label} Configuration - Severity selection: {severity}")
        if severity == '1':
            severity_value = 'Low'
        elif severity == '2':
            severity_value = 'Medium'
        elif severity == '3':
            severity_value = 'High'
        elif severity == '4':
            severity_value = 'Critical'
        else:
            severity_value = 'All'

        #get timestamp selection
        time_stamp_select = str(helper.get_arg('timestamp_selection'))
        helper.log_info(f"{log_label} Configuration - Timestamp field selection: {time_stamp_select}")

        #create checkpoint ID
        stanza_checkpoint = f"{time_stamp_select}_{stanza_name}"

        #Check for checkpoint data
        try:
            checkpoint_raw = helper.get_check_point(stanza_checkpoint)
            checkpoint = checkpoint_raw[time_stamp_select]
            helper.log_info(f"{log_label} Checkpoint data retrieved: {checkpoint}")

        except KeyError:
            helper.log_warning(f"{log_label} Checkpoint exists but field '{time_stamp_select}' not found in {list(checkpoint_raw.keys())}. Starting fresh collection.")
            checkpoint = ''
        except Exception as e:
            helper.log_info(f"{log_label} No checkpoint data was found ({type(e).__name__}: {e})")
            checkpoint = ''

        #get optional start time but only apply if there's no checkpoint
        start_date = helper.get_arg('start_date')

        if checkpoint != '':
            helper.log_info(f"{log_label} Configuration - Using checkpoint data: {checkpoint}")
        elif start_date:
            helper.log_info(f"{log_label} Configuration - Start date was configured: {start_date}")
            checkpoint = f"{start_date}T00:00:00Z"
        else:
            start_date = f"{(datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')}Z"
            helper.log_info(f"{log_label} Configuration - A start date was not configured using date 7 days ago: {start_date}")
            checkpoint = start_date

        #Get Cloud Environment Setting
        api_endpoint = helper.get_arg('cloud')
        helper.log_info(f"{log_label} Configuration - Cloud environment selected is: {api_endpoint}")

        if api_endpoint == 'us_commercial':
            cs_base_url = const.us_commercial_base

        elif api_endpoint == 'govcloud':
            cs_base_url = const.govcloud_base

        elif api_endpoint == 'eucloud':
            cs_base_url = const.eucloud_base

        elif api_endpoint == 'us_commercial2':
            cs_base_url = const.us_commercial2_base

        elif api_endpoint == 'govcloud2':
            cs_base_url = const.govcloud2_base

        else:
            helper.log_warning(f"{log_label} Configuration - Unrecognized cloud environment '{api_endpoint}', defaulting to US Commercial")
            cs_base_url = const.us_commercial_base

        #get Credentials
        global_account = helper.get_arg('account')
        client_id = global_account['username']
        client_secret = global_account['password']

        #get proxy setting configuration
        proxy = helper.get_proxy()

        #configure proper proxy syntax for use with FalconPy SDK calls
        if proxy:
            helper.log_info(f"{log_label} Configuration - Proxy is Set")
            proxy_type = str(proxy['proxy_type'])
            proxy_url = str(proxy['proxy_url'])
            proxy_port = str(proxy['proxy_port'])
            proxy_username = str(proxy['proxy_username'])
            proxy_password = str(proxy['proxy_password'])
            helper.log_debug(f"{log_label} Configuration - Proxy Type: {proxy_type} Proxy URL: {proxy_url} Proxy Port: {proxy_port}")

            if proxy['proxy_username']:
                helper.log_info(f"{log_label} Configuration - Proxy is configured with authentication.")
                proxy_string = f'{proxy_type}://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}'
                redacted_proxy = f'{proxy_type}://{proxy_username}:***@{proxy_url}:{proxy_port}'
                helper.log_debug(f"{log_label} Configuration - Proxy string: {redacted_proxy}")

            else:
                helper.log_info(f"{log_label} Configuration - Proxy is configured without authentication")
                proxy_string = f'{proxy_type}://{proxy_url}:{proxy_port}'

            if proxy_type == 'https':
                proxy_settings = {proxy_type:proxy_string}

            elif proxy_type == 'http':
                proxy_settings = {'http':proxy_string, 'https':proxy_string}

        else:
            helper.log_info(f"{log_label} Configuration - Proxy is not set.")
            proxy_settings = proxy

        cs_filter = f"{time_stamp_select}:>'{checkpoint}'"
        if severity_value != 'All':
            cs_filter = cs_filter + f"+severity:'{severity}'"
        sort = f'{time_stamp_select}.asc'
        helper.log_debug(f"{log_label} Configuration - ID filter syntax is {cs_filter}")
        ta_data = {"Cloud_environment":api_endpoint, "Input":stanza_name, "TA_version":version, "Start_date":start_date, "Severity":severity_value, "Timestamp_Field":time_stamp_select, "Timestamp_value":'' }

        api_config = {"client_id":client_id, "client_secret":client_secret, "user_agent":user_agent, "base_url":cs_base_url, "proxy":proxy_settings}
        query_params = {"filter":cs_filter, "limit":limit, "sort":sort}

        try:
            Get_CS_IDs.query_for_ids(api_config, query_params, checkpoint, stanza_checkpoint, log_label, ta_data, helper, ew)
        except SystemExit:
            helper.log_info(f"{log_label} Collection terminated due to unrecoverable error (see above)")
            return

    def get_account_fields(self):
        account_fields = []
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields

if __name__ == '__main__':
    exit_code = ModInputCROWDSTRIKE_FILEVANTAGE_JSON().run(sys.argv)
    sys.exit(exit_code)


