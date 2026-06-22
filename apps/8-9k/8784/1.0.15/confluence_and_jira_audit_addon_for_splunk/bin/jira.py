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
from confluence_logs_helper import stream_events, validate_input

import pytz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

ADDON_NAME = "confluence_and_jira_audit_addon_for_splunk"


class JIRA(smi.Script):
    def __init__(self):
        super(JIRA, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('jira')
        scheme.description = 'Jira'
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
                'from',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'to',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'account',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):

        app_name = "Avotrix-confluence_and_jira_audit_addon_for_splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, 'confluence_and_jira_audit_addon_for_splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-confluence_and_jira_audit_addon_for_splunk_settings")
        account_conf_file = cfm.get_conf('confluence_and_jira_audit_addon_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')
        # helper.log_info(f"Activation Key is {activation_key}")
        # logger.debug("activation key" , activation_key)

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

        cfm2 = conf_manager.ConfManager(session_key, 'confluence_and_jira_audit_addon_for_splunk',
                                        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-confluence_and_jira_audit_addon_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('confluence_and_jira_audit_addon_for_splunk_account')
        account_name = input_item.get("account")
        domain = account_conf_file2.get(account_name).get('domain_name')
        api_key = account_conf_file2.get(account_name).get('api_token')
        email = account_conf_file2.get(account_name).get('email_address')

        try:
            start_date = input_item.get("from")
            if start_date != None:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                dt_utc = dt - timedelta(hours=5, minutes=30)
                start_date1 = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            else:
                start_date1 = None
        except KeyError:
            start_date1 = None

        try:
            end_date = input_item.get("to")
            if end_date != None:
                dt = datetime.strptime(end_date, "%Y-%m-%d")
                dt_utc = dt - timedelta(hours=5, minutes=30)
                end_date1 = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            else:
                end_date1 = None
        except KeyError:
            end_date1 = None
        
        

        if (start_date1 and end_date1):
            pass
        elif (start_date1 and not end_date1):
            # today = datetime.now()
            # end_1 = int(today.timestamp() * 1000)
            IST = timezone(timedelta(hours=5, minutes=30))
            now = datetime.now(IST)  # get current IST time
            # Convert to UTC
            utc_now = now.astimezone(timezone.utc)
            # Format as yyyy-MM-dd'T'HH:mm:ss.SSS'Z'
            end_date1 = utc_now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'

            
        else:
            # today = datetime.now()
            # end_1 = int(today.timestamp() * 1000)
            # s = today - timedelta(days=7)
            # start_date2 = int(s.timestamp() * 1000)

            IST = timezone(timedelta(hours=5, minutes=30))
            now = datetime.now(IST)  # get current IST time
            # Convert to UTC
            utc_now = now.astimezone(timezone.utc)
            # Format as yyyy-MM-dd'T'HH:mm:ss.SSS'Z'
            end_date1 = utc_now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
            seven_days_ago_utc = utc_now - timedelta(days=7)
            # Format as yyyy-MM-dd'T'HH:mm:ss.SSS'Z'
            start_date1 = seven_days_ago_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'

            
            

        url2 = f"https://{domain}/rest/api/3/auditing/record"

        url = url2

        count = 0

        auth = (email,api_key)

        headers = {
            'Accept': 'application/json'
        }
        offset = 0
        limit = 100
        params = {
            'from': start_date1,
            'to': end_date1,
            'limit': limit,
            'offset':offset
        }

        if proxy_enabled == "1":
            res2 = requests.get(url,params=params,headers=headers,auth=auth,proxies=proxy_dict)
        else:
            res2 = requests.get(url,params=params,headers=headers,auth=auth)
        
        if res2.status_code != 200 or not res2.text.strip():
            logevent.internal_logs(meta, {"error": "Jira API error", "status_code": res2.status_code, "response": res2.text[:500]}, ADDON_NAME, host)
            return        


        data3 = res2.json()
        
        total = data3.get("total")

        while offset<total:
            params = {
                'from': start_date1,
                'to': end_date1,
                'limit': limit,
                'offset':offset
            }
            if proxy_enabled == "1":
                res = requests.get(url,params=params,headers=headers,auth=auth,proxies=proxy_dict)
            else:
                res = requests.get(url,params=params,headers=headers,auth=auth)

            data2 = res.json()

            for ids in data2["records"]:
                checkpoint = checkpointer.KVStoreCheckpointer(
                    "jira_checkpoint_audits_new",
                    session_key,
                    "confluence_and_jira_audit_addon_for_splunk"
                )

                unique_key = hashlib.md5(json.dumps(ids, sort_keys=True).encode()).hexdigest()
        
                state = checkpoint.get(unique_key)
                
                if state is None:
                    event = smi.Event(
                        data=json.dumps(ids),
                        index=input_item.get("index"),
                        sourcetype='Jira:audit log',
                    )
                    ew.write_event(event)
                    count = count + 1
                    checkpoint.update(unique_key, "Indexed")

            offset = offset + limit


        status = res.status_code
        logsummary.log_summary(activation_key, meta, url2, status, count, source, host, version)


if __name__ == '__main__':
    exit_code = JIRA().run(sys.argv)
    sys.exit(exit_code)