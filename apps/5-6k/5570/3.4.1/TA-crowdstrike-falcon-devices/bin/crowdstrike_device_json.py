#!/usr/bin/env python
# encoding = utf-8

import os
import sys
from datetime import datetime
import json

bin_dir = os.path.basename(__file__)

#Splunk Imports
import import_declare_test
from splunklib import modularinput as smi
from splunktaucclib.modinput_wrapper import base_modinput  as base_mi

#CrowdStrike imports
from falconpy import APIHarnessV2
from falconpy import __version__ as falconpy_version
from Get_CS_Devices_Splunk import Get_CS_Devices
import crowdstrike_constants as const

class ModInputcrowdstrike_device_json(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputcrowdstrike_device_json, self).__init__("ta_crowdstrike_falcon_devices", "crowdstrike_device_json", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputcrowdstrike_device_json, self).get_scheme()
        scheme.title = ("CrowdStrike Device JSON")
        scheme.description = ("Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(smi.Argument("cloud", title="Select Cloud Environment",
                                         description="Select the appropriate cloud environment for the Falcon Instance",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("account", title="API Credential",
                                         description="This is an OAuth2 based API credential with a \'hosts read\' scope",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("platform", title="Select Operating System Type",
                                         description="Select a specific operating system if desired",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("start_date", title="Start Date (Optional)",
                                         description="Only collect sensors that have been active on or after this date (used for initial collection only)",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("online_only", title="Online Only (Optional)",
                                         description="Only collect information for sensors that were online since the previous collection",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-crowdstrike-falcon-devices"

    def validate_input(helper, definition):
        # get the optional start time & interval values
        start_date = definition.parameters.get('start_date')
        interval    = definition.parameters.get('interval')
    
        if start_date != None:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Incorrect data format, should be YYYY-MM-DD")
    
        if int(interval) < 300:
            raise ValueError("The interval needs to be greater than 300 seconds (5 minutes)")

    def collect_events(helper, ew):
    
        #collect the TA version from the manifest file
        basepath = os.path.dirname(__file__)
        filepath = os.path.abspath(os.path.join(basepath, "..", "app.manifest"))
        
        with open(filepath, 'r') as manifest:
            manifest_file = json.load(manifest)
            version = manifest_file['info']['id']['version']
            
        #get stanza name
        stanza_name = str(helper.get_input_stanza_names())
        log_label = f'CrowdStrike Device TA {version} {stanza_name} :'

        helper.log_debug(f'{log_label} Configuration Input Name: {stanza_name}')
        helper.log_info(f'{log_label} Configuration: TA Version {version}')

        user_agent = 'Splunk_TA_Devices_v%s' % str(version)

        #Get Cloud Environment Setting
        api_endpoint = helper.get_arg('cloud')
        helper.log_info(f'{log_label} Cloud environment selected is: {api_endpoint}')
    
        cloud_map = {
            'us_commercial': const.us_commercial_base,
            'govcloud': const.govcloud_base,
            'govcloud2': const.govcloud2_base,
            'eucloud': const.eucloud_base,
            'us_commercial2': const.us_commercial2_base,
        }
        base_url = cloud_map.get(api_endpoint)
        if base_url is None:
            helper.log_error(f'{log_label} Unsupported cloud environment: {api_endpoint}')
            raise ValueError(f'Unsupported cloud environment: {api_endpoint}')

        #get Credentials
        global_account = helper.get_arg('account')
        clientid = global_account['username']
        secret= global_account['password']
        
        #get Platform setting
        platform = helper.get_arg('platform')
        helper.log_info(f'{log_label} Configuration: Platform selection {platform}')

        #get and set log level
        loglevel = helper.get_log_level()
        helper.set_log_level(loglevel)
        helper.log_info(f'{log_label} Configuration: Logging level is currently set to: {loglevel}')
    
        #get proxy setting configuration
        proxy = helper.get_proxy()
    
        #configure proper proxy syntax for use with FalconPy SDK calls
        if proxy:
            helper.log_info(f'{log_label} Configuration: Proxy is Set')
            proxy_type = str(proxy['proxy_type'])
            proxy_url = str(proxy['proxy_url'])
            proxy_port = str(proxy['proxy_port'])
            proxy_username = str(proxy['proxy_username'])
            proxy_password = str(proxy['proxy_password'])
            helper.log_debug(f'{log_label} Proxy Type: {proxy_type} Proxy URL: {proxy_url} Proxy Port: {proxy_port}')

            if proxy['proxy_username']:
                helper.log_info(f'{log_label} Configuration: Proxy is configured with authentication.')
                proxy_string = f'{proxy_type}://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}'
                redacted_proxy = f'{proxy_type}://{proxy_username}:***@{proxy_url}:{proxy_port}'
                helper.log_debug(f'{log_label} Proxy configured: {redacted_proxy}')
    
            else:
                helper.log_info(f'{log_label} Configuration: Proxy is configured without authentication')
                proxy_string = f'{proxy_type}://{proxy_url}:{proxy_port}'
    
            if proxy_type == 'https':
                proxy_settings = {proxy_type:proxy_string}
            
            elif proxy_type == 'http':
                proxy_settings = {'http':proxy_string, 'https':proxy_string}

            elif proxy_type in ('socks4', 'socks5'):
                proxy_settings = {'http':proxy_string, 'https':proxy_string}

            else:
                helper.log_error(f'{log_label} Configuration: Unsupported proxy type: {proxy_type}')
                raise ValueError(f'Unsupported proxy type: {proxy_type}')

        else:
            helper.log_info(f'{log_label} Configuration: Proxy is not set.')
            proxy_settings = proxy

        #get optional start time
        start_date = helper.get_arg('start_date')

        if start_date:
            helper.log_info(f'{log_label} Configuration: Start date was configured: {start_date}')

        else:
            helper.log_info(f'{log_label} Configuration: A start date was not configured')
            start_date = None
    
        #get online setting
        online_only = helper.get_arg('online_only')
        helper.log_info(f'{log_label} Configuration: Online only selection - {online_only}')

        #get timestamp selection
        time_stamp = helper.get_arg('timestamp')
        if (time_stamp == 'modified_timestamp') or (time_stamp == 'last_seen'):
            helper.log_debug(f'{log_label} Timestamp selection is present and configured')
        else:
            helper.log_debug(f'{log_label} Configuration: Timestamp selection not present - setting to modified_timestamp')
            time_stamp = 'modified_timestamp'
        helper.log_info(f'{log_label} Configuration: Timestamp: {time_stamp}')
        
        #create checkpoint ID        
        stanza_checkpoint = f'{time_stamp}_{stanza_name}'
    
        #authenticate to CrowdStrike
        helper.log_info(f'{log_label} FalconPy SDK version: {falconpy_version}')

        try:
            falcon = APIHarnessV2(client_id=clientid, client_secret=secret,
                                  base_url=base_url, proxy=proxy_settings,
                                  user_agent=user_agent, timeout=const.timeout,
                                  ssl_verify=True)
        except Exception as e:
            helper.log_error(f'{log_label} Failed to initialize FalconPy client: {type(e).__name__}: {e}')
            raise RuntimeError(f'FalconPy initialization failed: {e}') from e

        try:
            falcon.authenticate()
        except Exception as e:
            helper.log_error(f'{log_label} Authentication request failed: {type(e).__name__}: {e}')
            raise RuntimeError(f'Authentication request failed: {e}') from e

        if not falcon.authenticated():
            status = falcon.token_status
            reason = falcon.token_fail_reason
            if status is None:
                helper.log_error(
                    f'{log_label} Authentication failed — no response from CrowdStrike API. '
                    f'Verify network connectivity, proxy settings, DNS resolution, and firewall rules for {base_url}'
                )
                raise RuntimeError(f'Authentication failed — no response from CrowdStrike API ({base_url})')
            else:
                helper.log_error(
                    f'{log_label} Authentication failed — HTTP {status}: {reason}. '
                    f'Verify client_id, client_secret, API scopes (hosts:read), and cloud environment ({base_url})'
                )
                raise RuntimeError(f'Authentication failed — HTTP {status}: {reason}')

        helper.log_info(f'{log_label} Authentication successful')

        Get_CS_Devices.get_CS_devices(falcon, stanza_checkpoint, platform, online_only,
                              version, stanza_name, time_stamp, api_endpoint, ew,
                              log_label, helper)

    def get_account_fields(self):
        account_fields = []
        account_fields.append("account")
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        checkbox_fields.append("online_only")
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
    exitcode = ModInputcrowdstrike_device_json().run(sys.argv)
    sys.exit(exitcode)
