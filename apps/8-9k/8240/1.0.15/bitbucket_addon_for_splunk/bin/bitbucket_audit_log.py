
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
from datetime import datetime, timezone
from solnlib import conf_manager, log
import time
from datetime import datetime
from solnlib.modular_input import checkpointer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
log.Logs.set_context()
logger = log.Logs().get_logger('USER DETAILS')
ADDON_NAME = "bitbucket_addon_for_splunk" 


class BITBUCKET_AUDIT_LOG(smi.Script):
    def __init__(self):
        super(BITBUCKET_AUDIT_LOG, self).__init__()
    def get_scheme(self):
        scheme = smi.Scheme('bitbucket_audit_log')
        scheme.description = 'Audit Log'
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
                'api_key',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'org_id',
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
        # account_conf_file2 = cfm2.get_conf('bitbucket_addon_for_splunk_account')
        account_name = input_item.get("account")
        api_key = input_item.get("api_key")
        org_id = input_item.get("org_id")

        try:
            start_date = input_item.get("start_date")
            if start_date != None:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                dt_utc = dt - timedelta(hours=5, minutes=30)
                dt_str = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                start_date1 = int(dt.timestamp() * 1000)
            else:
                start_date1 = None
        except KeyError:
            start_date1 = None
        try:
            end_date = input_item.get("end_date")
            if end_date != None:
                dt = datetime.strptime(end_date, "%Y-%m-%d")
                dt_utc = dt - timedelta(hours=5, minutes=30)
                dt_str = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                end_date1 = int(dt.timestamp() * 1000)
            else:
                end_date1 = None
        except KeyError:
            end_date1 = None
        if (start_date1 and end_date1):
            url2 = f"https://api.atlassian.com/admin/v1/orgs/{org_id}/events?from={start_date1}&to={end_date1}&limit=500"
        elif (start_date1 and not end_date1):
            IST = timezone(timedelta(hours=5, minutes=30))
            now = datetime.now(IST) 
            utc_now = now.astimezone(timezone.utc)
            dt_str = utc_now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            end_date1 = int(dt.timestamp() * 1000)
            url2 = f"https://api.atlassian.com/admin/v1/orgs/{org_id}/events?from={start_date1}&to={end_date1}&limit=500"
        else:
            IST = timezone(timedelta(hours=5, minutes=30))
            now = datetime.now(IST)  # get current IST time
            # Convert to UTC
            utc_now = now.astimezone(timezone.utc)
            dt_str = utc_now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            end_date1 = int(dt.timestamp() * 1000)
            seven_days_ago_utc = utc_now - timedelta(days=7)
            dt_str = seven_days_ago_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            start_date1 = int(dt.timestamp() * 1000)
            url2 = f"https://api.atlassian.com/admin/v1/orgs/{org_id}/events?from={start_date1}&to={end_date1}&limit=500"


        url=url2
        params = {
            'product': 'bitbucket'
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }
        count = 0
        while url:
            if proxy_enabled == "1":
                res = requests.get(url,params=params,headers=headers, proxies=proxy_dict)
            else:
                res = requests.get(url, params=params, headers=headers)
            
            data2 = res.json()

            for ids in data2["data"]:
                checkpoint = checkpointer.KVStoreCheckpointer(
                    "bitbucket_audits_logs_checkpoint",
                    session_key,
                    "bitbucket_addon_for_splunk"
                )
        
                state = checkpoint.get(str(ids["id"]) + str(ids["attributes"]["time"]))
                
                if state is None:
                    event = smi.Event(
                        data=json.dumps(ids),
                        index=input_item.get("index"),
                        sourcetype='bitbucket:audit log',
                    )
                    ew.write_event(event)
                    count = count + 1
                    checkpoint.update(str(ids["id"]) + str(ids["attributes"]["time"]), "Indexed")
                # checkpoint.delete(str(ids["id"]) + str(ids["attributes"]["time"]))
            url = data2["links"].get("next")
        
        status = res.status_code
        logsummary.log_summary(activation_key, meta, url2, status, count, source, host, version)

if __name__ == '__main__':
    exit_code = BITBUCKET_AUDIT_LOG().run(sys.argv)
    sys.exit(exit_code)
