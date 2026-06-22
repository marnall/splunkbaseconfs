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
from datetime import datetime, timezone,timedelta
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


class BITBUCKET_PULLREQUESTS_ACTIVITY(smi.Script):
    def __init__(self):
        super(BITBUCKET_PULLREQUESTS_ACTIVITY, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('bitbucket_pullrequests_activity')
        scheme.description = 'Pull Requests Activity'
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

        
        dt_utc = datetime.now(timezone.utc)
        dt_utc = dt_utc - timedelta(days=7)
        # Format as ISO 8601 string in UTC with microseconds
        date1 = dt_utc.isoformat(timespec='microseconds')

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
        

        url = "https://api.bitbucket.org/2.0/workspaces"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        if proxy_enabled == "1":
            res = requests.get(url, headers=headers, proxies=proxy_dict)
        else:
            res = requests.get(url, headers=headers)

        r1 = res.json()
        
        size1 = r1['size']

        pagelen = r1['pagelen']

        page = 1

        val = math.ceil(size1 / pagelen)
        slug_list = []

        for i in range(0, val):
            paged_url = f"{url}?page={page}"
            if proxy_enabled == "1":
                res = requests.get(paged_url, headers=headers, proxies=proxy_dict)
            else:
                res = requests.get(paged_url, headers=headers)

            data = res.json()
            for item in data.get("values", []):
                slug = item.get("slug")
                if slug:
                    slug_list.append(slug)
            page += 1
        count = 0
        urls= []

        for i in slug_list:

            url2 = f"https://api.bitbucket.org/2.0/repositories/{i}"
            if proxy_enabled == "1":
                res2 = requests.get(url2, headers=headers, proxies=proxy_dict)
            else:
                res2 = requests.get(url2, headers=headers)

            d = res2.json()
            page2 = 1 
            size2  = d['size']
            
            pagelen2 = d['pagelen']
            val2 = math.ceil(size2/pagelen2)
            for j in range(0,val2):
                paged_url2 = f"{url2}?pagelen=50&page={page2}"
                if proxy_enabled == "1":
                    response2 = requests.get(paged_url2, headers=headers, proxies=proxy_dict)
                else:
                    response2 = requests.get(paged_url2, headers=headers)
                data2 = response2.json()
                page2 = page2+1

                

                for k in data2["values"]:
                    repo = str(k["slug"])
                    url3 = f"https://api.bitbucket.org/2.0/repositories/{i}/{repo}/pullrequests/activity?pagelen=50"

                    urls.append(url3)

                    demo = True
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    output_file = os.path.join(script_dir, "bitbucket_next_urls.txt")
                    # output_file = "bitbucket_next_urls.txt"  # Change to desired location

                    # with open('/opt/splunk/etc/apps/bitbucket_addon_for_splunk/bin/repo.txt',"a") as f:
                    #     f.write(f"{repo}\n")
                    # Save the current URL to a file before requesting it
    
                    while url3:
                        with open(output_file, "a") as f:
                            f.write(url3 + "\n")
                        if proxy_enabled == "1":
                            res3 = requests.get(url3, headers=headers, proxies=proxy_dict)
                        else:
                            res3 = requests.get(url3, headers=headers)
                    
                        d3 = res3.json()
                        stat = res3.status_code
                        # with open('/opt/splunk/etc/apps/bitbucket_addon_for_splunk/bin/repo_data.txt',"a") as f:
                        #     f.write(f"{repo}\n{d3}\n")
                        

                        
                        # # Check if 'next' exists; if not, exit loop

                        for ids in d3['values']:
                            if ids.get('update'):
                                if ids["update"]["date"]<date1:
                                    demo = False
                                    break
                            elif ids.get('comment'):
                                if ids["comment"]["updated_on"]<date1:
                                    demo = False
                                    break
                            elif ids.get('approval'):
                                if ids["approval"]["date"]<date1:
                                    demo = False
                                    break


                            checkpoint = checkpointer.KVStoreCheckpointer(
                                "bitbucket_pulls_new_requests_activities_checkpoint",
                                session_key,
                                "bitbucket_addon_for_splunk"
                            )

                            unique_key = hashlib.md5(json.dumps(ids, sort_keys=True).encode()).hexdigest()
            

                            state = checkpoint.get(unique_key)

                    
                            if state is None:
                                event = smi.Event(
                                    data=json.dumps(ids),
                                    index=input_item.get("index"),
                                    sourcetype='bitbucket:pullrequests_activity',
                                )
                                ew.write_event(event)
                                count = count + 1
                                checkpoint.update(unique_key, "Indexed")
                            #checkpoint.delete(unique_key)

                        if demo==False:
                            break
                        url3 = d3.get('next')


        status = response.status_code
        logsummary.log_summary(activation_key, meta, url, status, count, source, host, version)


if __name__ == '__main__':
    exit_code = BITBUCKET_PULLREQUESTS_ACTIVITY().run(sys.argv)
    sys.exit(exit_code)