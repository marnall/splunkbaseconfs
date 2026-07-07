#!/usr/bin/env python
# encoding = utf-8

import os
import sys
import time
from datetime import datetime
import json

import import_declare_test

from splunklib import modularinput as smi
from splunktaucclib.modinput_wrapper import base_modinput  as base_mi

bin_dir = os.path.basename(__file__)

# local CrowdStrike Python imports
from Get_CS_Indicators import Get_CS_Indicators
from Post_to_Splunk import Post_to_Splunk
import crowdstrike_constants as const

class ModInputcrowdstrike_intel_indicators(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputcrowdstrike_intel_indicators, self).__init__("ta_crowdstrike_intel_indicators", "crowdstrike_intel_indicators", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputcrowdstrike_intel_indicators, self).get_scheme()
        scheme.title = ("CrowdStrike_Intel_Indicators")
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
        scheme.add_argument(smi.Argument("credentials", title="API Client",
                                         description="This is an OAuth2 based API credential with a \'Indicators (Falcon X) read\' scope",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("cloud", title="Select Cloud Environment",
                                         description="Select the appropriate cloud environment for the Falcon Instance",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("deleted", title="Include Deleted Indicators ",
                                         description="Include indicators marked as deleted",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("start_date", title="Start Date (Optional)",
                                         description="Enter start date in YYYY-MM-DD format",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-crowdstrike-intel-indicators"

    def validate_input(helper, definition):
        start_date = definition.parameters.get('start_date')
        interval    = definition.parameters.get('interval')

        if start_date is not None:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Incorrect data format, should be YYYY-MM-DD")

        if int(interval) < 300:
            raise ValueError("The interval needs to be greater than 300 seconds (5 Minutes)")

    def collect_events(helper, ew):
        # collect the TA version from the manifest file
        basepath = os.path.dirname(__file__)
        filepath = os.path.abspath(os.path.join(basepath, "..", "app.manifest"))
        
        with open(filepath, 'r') as manifest:
            manifest_file = json.load(manifest)
            version = manifest_file['info']['id']['version']
            
        # get stanza name
        stanza_name = str(helper.get_input_stanza_names())
        log_label = f'CrowdStrike Intel Indicators TA {version} {stanza_name} :'

        helper.log_debug(f'{log_label} Configuration: Input Name: {stanza_name}')
        helper.log_info(f'{log_label} Configuration: TA Version: {version}')
        
        user_agent = f'Splunk_TA_Intel_Ind_v{version}'
        
            # Get Cloud Environment Setting
        api_endpoint = helper.get_arg('cloud')
        helper.log_info(f'{log_label} Configuration: Cloud environment selected is: {api_endpoint}')

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
    
        # get Credentials
        global_account = helper.get_arg('credentials')
        clientid = global_account['username']
        secret= global_account['password']
        
        # get and set log level
        loglevel = helper.get_log_level()
        helper.set_log_level(loglevel)
        helper.log_info(f'{log_label} Configuration: Logging level is currently set to: ' +str(loglevel))
    
        # get proxy setting configuration
        proxy = helper.get_proxy()
    
        # if proxy_config:
        if proxy:
            helper.log_info(f'{log_label} Configuration - Proxy is Set')
            proxy_type = str(proxy['proxy_type'])
            proxy_url = str(proxy['proxy_url'])
            proxy_port = str(proxy['proxy_port'])
            helper.log_debug(f'{log_label} Configuration - Proxy Type: {proxy_type} Proxy URL: {proxy_url} Proxy Port: {proxy_port}')

            if proxy['proxy_username']:
                proxy_username = str(proxy['proxy_username'])
                proxy_password = str(proxy['proxy_password'])
                helper.log_info(f'{log_label} Configuration - Proxy is configured with authentication.')
                proxy_string = f'{proxy_type}://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}'
                redacted_proxy = f'{proxy_type}://{proxy_username}:***@{proxy_url}:{proxy_port}'
                helper.log_debug(f'{log_label} Proxy configured: {redacted_proxy}')

            else:
                helper.log_info(f'{log_label} Configuration - Proxy is configured without authentication')
                proxy_string = f'{proxy_type}://{proxy_url}:{proxy_port}'
            
            if proxy_type == 'https':
                proxy_settings = {proxy_type:proxy_string}
            
            elif proxy_type == 'http':
                proxy_settings = {'http':proxy_string, 'https':proxy_string}
    
        else:
            helper.log_info(f'{log_label} Configuration: Proxy is not set.')    
            proxy_settings = proxy
    
        # get optional flags for deleted and updated entries
        deleted = helper.get_arg('deleted')
        helper.log_debug(f'{log_label} Deleted Entries Selection: {deleted}')
    
        # get optional start time
        start_date = helper.get_arg('start_date')
        
        if start_date:
            helper.log_info(f'{log_label} Configuration - Start date was configured: {start_date}')
        
        else:
            helper.log_info(f'{log_label} Configuration - No start date configured, will use checkpoint or default')
    
        # create checkpoint ID
        stanza_checkpoint = 'Last_Seen_'+str(stanza_name)
    
        # set timeout values
        timeout = const.timeout
        
        # Needs to account for prior checkpoints being timestamp based
        checkpoint = None
        try:
            checkpoint = helper.get_check_point(stanza_checkpoint)
            helper.log_debug(f'{log_label} Configuration - Checkpoint data retrieved: {checkpoint}')
            if 'last_marker' in checkpoint:
                last_marker = checkpoint['last_marker']
                indicator_filter = "_marker:>'" + str(last_marker) + "'"
                splunk_ckpt = last_marker
                helper.log_info(f'{log_label} Configuration - Marker based checkpoint data retrieved')
                chkpt_type = '_marker'
                sort = '_marker|asc'
            elif 'last_updated' in checkpoint:
                last_updated = checkpoint['last_updated']
                indicator_filter = 'last_updated:>' + str(last_updated)
                splunk_ckpt = last_updated
                helper.log_info(f'{log_label} Configuration - Last Updated based checkpoint data retrieved')
                chkpt_type = 'last_updated'
                sort = 'last_updated|asc'
            else:
                helper.log_error(f'{log_label} Unrecognized checkpoint format: {checkpoint}. '
                    f'To recover, search for the last collected indicator: '
                    f'`cs_ii_get_index` | stats max(last_updated) | eval last_updated=strftime(last_updated,"%Y-%m-%d") '
                    f'— then set that date as the start_date on the input.')
                raise RuntimeError(f'Unrecognized checkpoint format — see splunkd.log for recovery steps')
        except Exception as e:
            helper.log_warning(f'{log_label} Configuration - Unable to retrieve checkpoint: {type(e).__name__}: {e}. Starting from configured start_date or default.')
            checkpoint = None
            chkpt_type = '_marker'
            splunk_ckpt = 0
            sort = '_marker|asc'
    
        if checkpoint is None:
            # properly configure the timestamp
            if start_date:
                try:
                    pattern = '%Y-%m-%d %H:%M:%S'
                    start_time = start_date +' 00:00:01'
                    helper.log_debug(f'{log_label} Configuration - Appending start time to manually entered date: {start_time}')
                    epoch = int(time.mktime(time.strptime(start_time,pattern)))
                    pub_date = epoch
                    helper.log_debug(f'{log_label} Publication date - {pub_date}')
    
                except (TypeError, ValueError) as e:
                    helper.log_error(f'{log_label} Unable to parse start_date "{start_date}": {type(e).__name__}: {e}')
                    raise RuntimeError(f'Invalid start_date format "{start_date}": {e}') from e
    
            else:
                helper.log_info(f'{log_label} Using historic start date.')
                pub_date = const.default_start_epoch
            indicator_filter = 'last_updated:>' + str(pub_date)[:10]
            sort = 'last_updated|asc'
            helper.log_debug(f'{log_label} Indicator_filter = {indicator_filter}')
            chkpt_type = '_marker'
            

        # maximum indicator limit & offset value
        limit = const.max_indicators_per_page
        offset = 0
        
        # get intel indicators
        kwargs={'sort':sort, 'indicator_filter':indicator_filter, 'deleted':deleted, 'offset':offset, 'limit':limit, 'proxy':proxy_settings, 'user_agent':user_agent, 'base_url':base_url, 'timeout':timeout, 'api_endpoint':api_endpoint, 'log_label':log_label, 'chkpt_type':chkpt_type, 'splunk_ckpt':splunk_ckpt, 'version':version, 'stanza_name':stanza_name, 'stanza_checkpoint':stanza_checkpoint, 'helper':helper, 'ew':ew, 'clientid':clientid, 'secret':secret}
        
        Get_CS_Indicators.get_CS_indicators(**kwargs)
    
    def get_account_fields(self):
        account_fields = []
        account_fields.append("credentials")
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        checkbox_fields.append("deleted")
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
    exitcode = ModInputcrowdstrike_intel_indicators().run(sys.argv)
    sys.exit(exitcode)
