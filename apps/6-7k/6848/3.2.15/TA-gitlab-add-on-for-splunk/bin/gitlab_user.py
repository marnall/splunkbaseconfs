import import_declare_test
import sys
import json
import os
import base64
import requests
import re
import logging
from requests.auth import HTTPBasicAuth
from addonutils import logevent
from addonutils.a_v import A_V
from addonutils import logsummary
from addonutils import getproxy
from splunklib import modularinput as smi
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

ADDON_NAME = "TA-gitlab-add-on-for-splunk"


class GITLAB_USER(smi.Script):

    def __init__(self):
        super(GITLAB_USER, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('gitlab_user')
        scheme.description = 'gitlab:users'
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
                'start_date',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'end_date',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        app_name = "Avotrix-GitLab Add-on for Splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, 'TA-gitlab-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_gitlab_add_on_for_splunk_settings")
        account_conf_file = cfm.get_conf('ta_gitlab_add_on_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')
        source = os.path.basename(sys.argv[0])
        host = self._input_definition.metadata['server_host']
        meta = self._input_definition.metadata
        v = A_V(app_name, activation_key)
        key_validator = v.v_a_k()
        if key_validator:
            logsummary.activation_log_summary(meta, key_validator, "Inactive", source, host)
            sys.exit(2)
        try:
            ver = conf_manager.ConfManager(session_key, 'TA-gitlab-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-app")
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
                "Upgrade Required": "Please update to latest Addon version - Visit - https://splunkbase.splunk.com/app/6848 - If you need assistance, contact support@avotrix.com - Thank you, The Avotrix Team"
            }
            logevent.internal_logs(meta, event, ADDON_NAME, host)
            sys.exit(2)

        proxy_dict, proxy_enabled = getproxy.get_proxy(account_conf_file=account_conf_file)
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)
        cfm2 = conf_manager.ConfManager(session_key, 'TA-gitlab-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_gitlab_add_on_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ta_gitlab_add_on_for_splunk_account')
        account_name = input_item.get("account")
        username = account_conf_file2.get(account_name).get('username')
        password = account_conf_file2.get(account_name).get('password')
        start_date = input_item.get("start_date")
        end_date = input_item.get("end_date")
        if (start_date and end_date):
            url = f"https://{username}/api/v4/users?per_page=100&created_after={start_date}&created_before={end_date}"
            headers = {'Authorization': f'Bearer {password}'}
            if proxy_enabled == "1":
                response = requests.get(url, headers=headers, proxies=proxy_dict)
            else:
                response = requests.get(url, headers=headers)
            headers = {'Authorization': f'Bearer {password}'}
            response1 = requests.head(url, headers=headers)
            r = response.json()
            count = 0
            for i in r:
                try:
                    checkpoint = checkpointer.KVStoreCheckpointer("TA-gitlab-add-on-for-splunk_checkpoints", session_key, "TA-gitlab-add-on-for-splunk")
                    state = checkpoint.get(str(i["id"]) + str(i["username"]))
                    if state is None:
                        event = smi.Event(data=json.dumps(i, indent=2), index=input_item.get("index"), sourcetype='gitlab:users')
                        ew.write_event(event)
                        count = count + 1
                        checkpoint.update(str(i["id"]) + str(i["username"]), "Indexed")
                except Exception:
                    pass
            while (True):
                try:
                    abc = (response1.headers["Link"])
                    abc1 = re.findall(r'[\<\>\w:\/\d\.\?\s\+\=&\-\%]*;\srel=\"next\"', abc)
                    abcd = (" ".join(map(str, abc1)))
                    abc2 = re.findall(r'api[\w:\/\d\.\?\s\+\=&\-\%]*false[|&\w\d\=\-\%]*', abcd)
                    abc3 = (" ".join(map(str, abc2)))
                    if (abc3 == ""):
                        break
                    url1 = f"https://{username}/{abc3}; rel=next"
                    headers = {'Authorization': f'Bearer {password}'}
                    if proxy_enabled == "1":
                        response12 = requests.get(url, headers=headers, proxies=proxy_dict)
                    else:
                        response12 = requests.get(url, headers=headers)
                    response1 = requests.head(url1, headers=headers)
                    r1 = response12.json()
                    for i in r1:
                        try:
                            checkpoint = checkpointer.KVStoreCheckpointer("TA-gitlab-add-on-for-splunk_checkpoints", session_key, "TA-gitlab-add-on-for-splunk")
                            state = checkpoint.get(str(i["id"]) + str(i["username"]))
                            if state is None:
                                event = smi.Event(data=json.dumps(i, indent=2), index=input_item.get("index"), sourcetype='gitlab:users')
                                ew.write_event(event)
                                count = count + 1
                                checkpoint.update(str(i["id"]) + str(i["username"]), "Indexed")
                        except Exception:
                            pass
                except (KeyError):
                    break
        else:
            today = datetime.now()
            yesterday1 = today - timedelta(days=1)
            start_date = yesterday1.strftime("%Y-%m-%d")
            yesterday2 = today
            end_date = yesterday2.strftime("%Y-%m-%d")
            url = f"https://{username}/api/v4/users?per_page=100&created_after={start_date}&created_before={end_date}"
            headers = {'Authorization': f'Bearer {password}'}
            if proxy_enabled == "1":
                response = requests.get(url, headers=headers, proxies=proxy_dict)
            else:
                response = requests.get(url, headers=headers)

            response1 = requests.head(url, headers=headers)
            r = response.json()
            count = 0
            for i in r:
                try:
                    checkpoint = checkpointer.KVStoreCheckpointer("TA-gitlab-add-on-for-splunk_checkpoints", session_key, "TA-gitlab-add-on-for-splunk")
                    state = checkpoint.get(str(i["id"]) + str(i["username"]))
                    if state is None:
                        event = smi.Event(data=json.dumps(i, indent=2), index=input_item.get("index"), sourcetype='gitlab:users')
                        ew.write_event(event)
                        count = count + 1
                        checkpoint.update(str(i["id"]) + str(i["username"]), "Indexed")
                except Exception:
                    pass
            while (True):
                try:
                    abc = (response1.headers["Link"])
                    abc1 = re.findall(r'[\<\>\w:\/\d\.\?\s\+\=&\-\%]*;\srel=\"next\"', abc)
                    abcd = (" ".join(map(str, abc1)))
                    abc2 = re.findall(r'api[\w:\/\d\.\?\s\+\=&\-\%]*false[|&\w\d\=\-\%]*', abcd)
                    abc3 = (" ".join(map(str, abc2)))
                    if (abc3 == ""):
                        break
                    url1 = f"https://{username}/{abc3}; rel=next"
                    headers = {'Authorization': f'Bearer {password}'}
                    if proxy_enabled == "1":
                        response12 = requests.get(url, headers=headers, proxies=proxy_dict)
                    else:
                        response12 = requests.get(url, headers=headers)
                    response1 = requests.head(url1, headers=headers)
                    r1 = response12.json()
                    for i in r1:
                        try:
                            checkpoint = checkpointer.KVStoreCheckpointer("TA-gitlab-add-on-for-splunk_checkpoints", session_key, "TA-gitlab-add-on-for-splunk")
                            state = checkpoint.get(str(i["id"]) + str(i["username"]))
                            if state is None:
                                event = smi.Event(data=json.dumps(i, indent=2), index=input_item.get("index"), sourcetype='gitlab:users')
                                ew.write_event(event)
                                count = count + 1
                                checkpoint.update(str(i["id"]) + str(i["username"]), "Indexed")
                        except Exception:
                            pass
                except (KeyError):
                    break
        status = response.status_code
        logsummary.log_summary(activation_key, meta, url, status, count, source, host, version)


if __name__ == '__main__':
    exit_code = GITLAB_USER().run(sys.argv)
    sys.exit(exit_code)
