import import_declare_test
import app_common

import copy
import os
import sys
import json
from solnlib import utils as sutils

from splunktaucclib.global_config import GlobalConfig, GlobalConfigSchema

import splunktaucclib.modinput_wrapper.base_modinput as modinput_wrapper
from splunklib import modularinput as smi


bin_dir = os.path.basename(__file__)


class ModInputtrendmicro_init(modinput_wrapper.BaseModInput):

    def __init__(self):

        use_single_instance = False
        super(ModInputtrendmicro_init, self).__init__(
            "xdr_splunk", "trend_init", use_single_instance)
        self.global_checkbox_fields = None
        app_common.set_helper(self)
        self._global_config = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputtrendmicro_init, self).get_scheme()
        scheme.title = ("init")
        scheme.description = "init"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        return scheme

    def get_app_name(self):
        return "xdr_splunk"

    def validate_input(self, definition):
        """validate the input stanza"""
        return 0

    def collect_events(self, ew):
        """write out the events"""
        return

    def get_account_fields(self):
        account_fields = []
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(
                bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error(
                    'Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields

    def _parse_input_args_from_global_config(self, inputs):
        """Parse input arguments from global configuration.
        :param inputs:
        """
        # dirname at this point will be <splunk_home>/etc/apps/<ta-name>/lib/splunktaucclib/modinput_wrapper, go up 3 dirs from this file to find the root TA directory
        dirname = os.path.dirname
        config_path = os.path.join(
            dirname(dirname((__file__))),
            "appserver",
            "static",
            "js",
            "build",
            "globalConfig.json",
        )
        with open(config_path) as f:
            schema_json = "".join([l for l in f])
        end_point_field = {
            "field": "endpoint",
            "label": "Endpoint URL",
            "type": "text",
            "help": "URL to send the HTTPS GET request to",
            "required": True,
            "defaultValue": "",
                            "validators": [
                                {
                                    "type": "regex",
                                    "pattern": "(https)://([\\w.]+/?)\\S*",
                                    "errorMsg": "Endpoint URL must use HTTPS protocol"
                                }
                            ]
        }
        token_field = {
            "field": "token",
            "label": "Authentication Token",
            "type": "text",
            "help": "Token used to authenticate your Splunk connector",
            "required": True,
            "encrypted": True,
            "defaultValue": ""
        }
        schema = json.loads(schema_json)
        tabs = schema["pages"]["configuration"]["tabs"]
        for item in tabs:
            if item["name"] == "additional_parameters":
                item["entity"].append(end_point_field)
                item["entity"].append(token_field)

        global_schema = GlobalConfigSchema(schema)

        uri = inputs.metadata["server_uri"]
        session_key = inputs.metadata["session_key"]
        global_config = GlobalConfig(uri, session_key, global_schema)
        self._global_config = global_config
        ucc_inputs = global_config.inputs.load(input_type=self.input_type)
        accounts = self._global_config.configs.load("accounts")
        self.log_info(f"accounts : {accounts}")
        for account in accounts["accounts"]:
            if account["name"] == "default_account":
                endpoint = account["endpoint"]
                token = account["token"]
                self.log_info(f"endpoint : {endpoint}")
                if endpoint != "" and token != "":
                    return
                break

        endpoint = self.get_global_setting("endpoint")
        token = self.get_global_setting("token")
        self.log_info(f"global endpoint: {endpoint}")
        self.log_info(f"global token: {token}")
        if endpoint is None or len(endpoint) == 0:
            return
        payload = {
            "accounts": [
                {
                    "name": "default_account",
                    "token": token,
                    "endpoint": endpoint
                }
            ]
        }
        self._global_config.save(payload)

        all_stanzas = ucc_inputs.get(self.input_type, {})

        if not all_stanzas:
            # for single instance input. There might be no input stanza.
            # Only the default stanza. In this case, modinput should exit.
            self.log_warning(
                "No stanza found for input type: " + self.input_type)
            sys.exit(0)

        account_fields = self.get_account_fields()
        checkbox_fields = self.get_checkbox_fields()
        self.input_stanzas = {}
        for stanza in all_stanzas:
            full_stanza_name = "{}://{}".format(
                self.input_type, stanza.get("name"))
            if full_stanza_name in inputs.inputs:
                if stanza.get("disabled", False):
                    raise RuntimeError("Running disabled data input!")
                stanza_params = {}
                for k, v in stanza.items():
                    if k in checkbox_fields:
                        stanza_params[k] = sutils.is_true(v)
                    elif k in account_fields:
                        stanza_params[k] = copy.deepcopy(v)
                    else:
                        stanza_params[k] = v
                self.input_stanzas[stanza.get("name")] = stanza_params

    def parse_input_args(self, input_definition):
        """Override base method to provide user-friendly error handling."""
        try:
            # Call parent method to do the actual parsing
            super(ModInputtrendmicro_init, self).parse_input_args(input_definition)
        except AssertionError:
            # Check for common configuration issues and provide helpful messages
            accounts = self._global_config.configs.load("accounts") if self._global_config else {"accounts": []}
            
            # Check if default_account exists and is configured
            default_account = None
            for account in accounts.get("accounts", []):
                if account["name"] == "default_account":
                    default_account = account
                    break
            
            if not default_account:
                self.log_warning(
                    "Configuration Warning: No 'default_account' found. "
                    "Please create an account named 'default_account' in the Configuration page, "
                    "or update your inputs.conf to reference an existing account."
                )
            elif not default_account.get("endpoint") or not default_account.get("token"):
                self.log_warning(
                    "Configuration Warning: The 'default_account' exists but is not properly configured. "
                    "Please ensure both 'endpoint' and 'token' are set in the Configuration page."
                )
            else:
                self.log_warning(
                    "Configuration Warning: Input initialization failed. "
                    "Please check that your inputs are properly configured and reference valid accounts."
                )
            
            # Exit gracefully instead of crashing with technical error
            self.log_info("Trend Micro XDR initialization skipped due to configuration issues.")
            sys.exit(0)


if __name__ == "__main__":
    exitcode = ModInputtrendmicro_init().run(sys.argv)
    sys.exit(exitcode)
