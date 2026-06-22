
import import_declare_test
import hashlib
import sys
import math
import json
from requests.auth import HTTPBasicAuth
import requests
import logging
import os
import base64
import datetime
from datetime import timedelta
from addonutils import logevent
from addonutils.a_v import A_V
from addonutils import logsummary
from addonutils import getproxy
from splunklib import modularinput as smi
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
log.Logs.set_context()
logger = log.Logs().get_logger('USER DETAILS')
ADDON_NAME = "bitbucket_addon_for_splunk" 


class BITBUCKET_WORKSPACE(smi.Script):
    def __init__(self):
        super(BITBUCKET_WORKSPACE, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('bitbucket_workspace')
        scheme.description = 'Workspace'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                'account',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'use_existing_checkpoint',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        app_name = "Avotrix-bitbucket_addon_for_splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, 'bitbucket_addon_for_splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-bitbucket_addon_for_splunk_settings")
        account_conf_file = cfm.get_conf('bitbucket_addon_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')
        logger.debug("activation key" , activation_key)
        
        source = os.path.basename(sys.argv[0])
        host = self._input_definition.metadata['server_host']
        meta = self._input_definition.metadata
        

        v = A_V(app_name, activation_key)
        key_validator = v.v_a_k()
        if key_validator:
            logsummary.activation_log_summary(meta, key_validator, "Inactive", source, host)
            sys.exit(2)
        try:
            ver = conf_manager.ConfManager(session_key, ADDON_NAME, realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-app")
            vers = ver.get_conf('app')
            version = vers.get('id').get('version')
        except Exception:
            event = {
                "Permission Required": "Please ensure that the necessary read permissions are granted for the required files to use - Please contact support@avotrix.com. - Thank you, The Avotrix Team"
            }
            logevent.internal_logs(meta, event, ADDON_NAME, host)
            sys.exit(2)
        m_c = 0
        m_ver = ''
        for m in version:
            if m == '.':
                m_c += 1
            if m_c == 2:
                if m != '.':
                    m_ver += m
        m_ver = int(m_ver)
        if m_ver >= 15:
            pass
        else:
            event = {
                "Upgrade Required": "Please update to latest Addon version - Visit - https://splunkbase.splunk.com/app/7227 - If you need assistance, contact support@avotrix.com - Thank you, The Avotrix Team"
            }
            logevent.internal_logs(meta, event, ADDON_NAME, host)
            sys.exit(2)
        
        proxy_dict, proxy_enabled = getproxy.get_proxy(account_conf_file=account_conf_file)
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)

        cfm2 = conf_manager.ConfManager(session_key, 'bitbucket_addon_for_splunk',
                                        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-bitbucket_addon_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('bitbucket_addon_for_splunk_account')
        account_name = input_item.get("account")
        acc_id = account_conf_file2.get(account_name).get('client_id')
        acc_secret = account_conf_file2.get(account_name).get('client_secret')

        

        acc_refresh_token = account_conf_file2.get(account_name).get('refresh_token')

        url = "https://bitbucket.org/site/oauth2/access_token"
        # headers = {
        #     "Content-Type": "application/x-www-form-urlencoded",
        # }
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": acc_refresh_token
        }

        if proxy_enabled == "1":
            response = requests.post(url, data=payload,auth=HTTPBasicAuth(acc_id, acc_secret), proxies=proxy_dict)
        else:
            response = requests.post(url, data=payload,auth=HTTPBasicAuth(acc_id, acc_secret))

        r = response.json()
        api_token = r["access_token"]
        token = str(api_token)


        url1 = "https://api.bitbucket.org/2.0/workspaces"

        token = api_token
        headers = {
            "Accept": "application/json",
            'Authorization': f'Bearer {token}'
            }
        if proxy_enabled == "1":
            res = requests.get(url1, headers=headers, proxies=proxy_dict)
        else:
            res = requests.get(url1, headers=headers)
        r1 = res.json()
        

        size1 = r1['size']

        pagelen = r1['pagelen']

        val = math.ceil(size1 / pagelen)
        
        page = 1

        count = 0

        for i in range(0, val):
            paged_url = f"{url1}?page={page}"
            
            
            if proxy_enabled == "1":
                response = requests.get(paged_url, headers=headers, proxies=proxy_dict)
            else:
                response = requests.get(paged_url, headers=headers)
                
            data = response.json()
           
            # l1.append(data[])
            page = page + 1
            
            for ids in data["values"]:
                checkpoint = checkpointer.KVStoreCheckpointer(
                    "bitbucket_workspaces_checkpoint",
                    session_key,
                    "bitbucket_addon_for_splunk"
                )
            
                state = checkpoint.get(str(ids["slug"]) + str(ids["created_on"]))

                
                if state is None:
                    event = smi.Event(
                        data=json.dumps(ids),
                        index=input_item.get("index"),
                        sourcetype='bitbucket:workspace',
                    )
                    ew.write_event(event)
                    count = count + 1
                    checkpoint.update(str(ids["slug"]) + str(ids["created_on"]), "Indexed")
                # checkpoint.delete(str(ids["slug"]) + str(ids["created_on"]))
        

        status = response.status_code
        logsummary.log_summary(activation_key, meta, url1, status, count, source, host, version)
if __name__ == '__main__':
    exit_code = BITBUCKET_WORKSPACE().run(sys.argv)
    sys.exit(exit_code)