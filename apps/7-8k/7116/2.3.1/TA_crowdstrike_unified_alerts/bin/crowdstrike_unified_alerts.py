# encoding = utf-8

import import_declare_test

import os
from os import path

import sys
import time
from datetime import datetime, timedelta
import json

import traceback
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput as base_mi
import random

bin_dir = os.path.basename(__file__)

#CrowdStrike Specific Imports:
import crowdstrike_constants as const
from dia_ta_alerts import Alerts
from falconpy import APIHarnessV2

class ModInputcrowdstrike_unified_alerts(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputcrowdstrike_unified_alerts, self).__init__("ta_crowdstrike_unified_alerts_technical_add_on", "crowdstrike_unified_alerts", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputcrowdstrike_unified_alerts, self).get_scheme()
        scheme.title = ("CrowdStrike Unified Alerts")
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
        scheme.add_argument(smi.Argument("account", title="Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("cloud", title="Select Cloud Environment",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("product", title="Alert Sources",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("start_date", title="Optional Filter: Start Date",
                                         description="",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA_crowdstrike_unified_alerts"

    def validate_input(helper, definition):
        start_date  = definition.parameters.get('start_date')
        products = definition.parameters.get('product')
        #validate date format is correct
        if start_date != None:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Incorrect data format, should be YYYY-MM-DD")

        new_products = products.split(',')
        num_products = len(new_products)

        if num_products > 1:
            if 'all' in products:
                raise ValueError(f"Cannot selected specific Alert Sources if All has been selected")
            
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
        log_label = f"CrowdStrike Unified Alerts TA - {version} {stanza_name} "

        helper.log_info(f"{log_label}: Configuration - Logging level is currently set to: {loglevel}")
        helper.log_info(f"{log_label}: Configuration - Input Name: {stanza_name}")
        
        #configure useragent value for API calls
        user_agent = f"Splunk_TA_UA_v{version}"
        
        #create checkpoint ID
        stanza_checkpoint = f"updated_timestamp_{stanza_name}"

        #Check for checkpoint data
        try:
            checkpoint_raw = helper.get_check_point(stanza_checkpoint)
            checkpoint = checkpoint_raw['updated_timestamp']
            helper.log_info(f"{log_label}: Checkpoint data retrieved: {checkpoint}")

        except:
            helper.log_info(f"{log_label}: No checkpoint data was found.")
            checkpoint = ''

        #get optional start time but only apply if there's no checkpoint
        start_date = helper.get_arg('start_date')
        
        if checkpoint != '':
            helper.log_info(f"{log_label}: Configuration - Start date is from checkpoint data: {checkpoint}")
            chkpt_value = True
        elif start_date:
            checkpoint = f"{start_date}T00:00:00Z"
            helper.log_info(f"{log_label}: Configuration - Start date is from configuration: {checkpoint}")
            chkpt_value = False
        else:
            start_date = f"{(datetime.utcnow() - timedelta(days = 30)).isoformat(timespec='seconds')}Z"
            checkpoint = start_date
            helper.log_info(f"{log_label}: Configuration - A start date was not configured using default: {checkpoint}")
            chkpt_value = False

        #Get Cloud Environment Setting
        api_endpoint = helper.get_arg('cloud')
        helper.log_info(f"{log_label}: Configuration - Cloud environment selected is: {api_endpoint}")

        if api_endpoint == 'us_commercial':
            cs_base_url = const.us_commercial_base
            
        elif api_endpoint == 'govcloud':
            cs_base_url = const.govcloud_base

        elif api_endpoint == 'eucloud':
            cs_base_url = const.eucloud_base

        elif api_endpoint == 'us_commercial2':
            cs_base_url = const.us_commercial2_base

        #get Credentials
        global_account = helper.get_arg('account')
        clientid = global_account['username']
        secret= global_account['password']

        #get proxy setting configuration
        proxy = helper.get_proxy()

        #configure proper proxy syntax for use with FalconPy SDK calls
        if proxy:
            helper.log_info(f"{log_label}: Configuration - Proxy is Set")
            proxy_type = str(proxy['proxy_type'])
            proxy_url = str(proxy['proxy_url'])
            proxy_port = str(proxy['proxy_port'])
            proxy_username = str(proxy['proxy_username'])
            proxy_password = str(proxy['proxy_password'])
            helper.log_debug(f"{log_label}: Configuration - Proxy Type: {proxy_type} Proxy URL: {proxy_url} Proxy Port: {proxy_port}")
            
            if proxy['proxy_username']:
                helper.log_info(f"{log_label}: Configuration - Proxy is configured with authentication.")
                proxy_string = f'{proxy_type}://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}'

            else:
                helper.log_info(log_label + ': Configuration: Proxy is configured without authentication')
                proxy_string = f'{proxy_type}://{proxy_url}:{proxy_port}'

            if proxy_type == 'https':
                proxy_settings = {proxy_type:proxy_string}
            
            elif proxy_type == 'http':
                proxy_settings = {'http':proxy_string, 'https':proxy_string}

        else:
            helper.log_info(f"{log_label}: Configuration - Proxy is not set.")    
            proxy_settings = proxy

        falcon = APIHarnessV2(client_id=clientid,client_secret=secret, base_url=cs_base_url, proxy=proxy_settings)
        
        #get product(s)
        products =  helper.get_arg('product')
        
        ta_data = {"Cloud_environment":api_endpoint, "Input":stanza_name, "TA_version":version, "Products":str(products), "Start_date":checkpoint}

        Alerts.get_alert_ids(checkpoint, stanza_checkpoint, chkpt_value, user_agent, log_label, falcon, proxy_settings, cs_base_url, ta_data, helper, ew)

    def get_account_fields(self):
        account_fields = []
        account_fields.append("account")
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

if __name__ == "__main__":
    exitcode = ModInputcrowdstrike_unified_alerts().run(sys.argv)
    sys.exit(exitcode)
