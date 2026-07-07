import import_declare_test
import sys
import json
from requests.auth import HTTPBasicAuth
import requests
import logging
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from addonutils import logevent
from addonutils.a_v import A_V
from addonutils import logsummary
from addonutils import getproxy
from splunklib import modularinput as smi
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
import hashlib


ADDON_NAME = "TA-proxmox-add-on-for-splunk"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


class PROXMOX_TASKS(smi.Script):

    def __init__(self):
        super(PROXMOX_TASKS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('proxmox_tasks')
        scheme.description = 'Tasks'
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
                'global_account',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        app_name = "Avotrix-proxmox-add-on-for-splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, 'TA-proxmox-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_proxmox_add_on_for_splunk_settings")
        account_conf_file = cfm.get_conf('ta_proxmox_add_on_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')
        source = os.path.basename(sys.argv[0])
        host = self._input_definition.metadata['server_host']
        meta = self._input_definition.metadata
        try:
            ver = conf_manager.ConfManager(session_key, 'TA-proxmox-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-app")
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
                "Upgrade Required": "Please update to latest Addon version - Visit - https://splunkbase.splunk.com/app/7014 - If you need assistance, contact support@avotrix.com - Thank you, The Avotrix Team"
            }
            logevent.internal_logs(meta, event, ADDON_NAME, host)
            sys.exit(2)

        v = A_V(app_name, activation_key)
        key_validator = v.v_a_k()
        if key_validator:
            logsummary.activation_log_summary(meta, key_validator, "Inactive", source, host)
            sys.exit(2)
        proxy_dict, proxy_enabled = getproxy.get_proxy(account_conf_file=account_conf_file)
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)
        cfm2 = conf_manager.ConfManager(session_key, 'TA-proxmox-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_proxmox_add_on_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ta_proxmox_add_on_for_splunk_account')
        account_name = input_item.get("global_account")
        domain_ip = account_conf_file2.get(account_name).get('domain_ip')
        input_items.append(domain_ip)
        username = account_conf_file2.get(account_name).get('username')
        input_items.append(username)
        password = account_conf_file2.get(account_name).get('password')
        input_items.append(password)
        url = f'https://{domain_ip}/api2/json/nodes'
        url1 = f'https://{domain_ip}/api2/json/access/ticket'

        data = {'username': username, 'password': password}

        if proxy_enabled == "1":

            response = requests.post(url1, data=data, proxies=proxy_dict, verify=True)
            r = response.json()
            tkt = r['data']['ticket']
            tkn = r['data']['CSRFPreventionToken']
            headers = {'Authorization': tkn}
            cookies = {'PVEAuthCookie': tkt}
            response_images = requests.get(url, headers=headers, cookies=cookies, proxies=proxy_dict, verify=True)
            r1 = response_images.json()
            n = r1['data'][0]['node']
            url2 = f'https://{domain_ip}/api2/json/nodes/{n}/tasks'
            response = requests.get(url2, headers=headers, proxies=proxy_dict, cookies=cookies, verify=True)
        else:
            response = requests.post(url1, data=data, verify=True)
            r = response.json()
            tkt = r['data']['ticket']
            tkn = r['data']['CSRFPreventionToken']
            headers = {'Authorization': tkn}
            cookies = {'PVEAuthCookie': tkt}
            response_images = requests.get(url, headers=headers, cookies=cookies, verify=True)
            r1 = response_images.json()
            n = r1['data'][0]['node']
            url2 = f'https://{domain_ip}/api2/json/nodes/{n}/tasks'
            response = requests.get(url2, headers=headers, cookies=cookies, verify=True)

        count = 0
        r2 = response.json()
        checkpoint = checkpointer.KVStoreCheckpointer("TA-proxmox-add-on-for-splunk_checkpoints", session_key, "TA-proxmox-add-on-for-splunk")
        for i in r2['data']:
            checkpoint_key = str(i["starttime"]) + str(i["id"])
            state = checkpoint.get(checkpoint_key)
            if state is None:
                event = smi.Event(
                    data=json.dumps(i, indent=2),
                    index=input_item.get("index"),
                    sourcetype="proxmox_task",
                )
                ew.write_event(event)
                count += 1
                checkpoint.update(checkpoint_key, "Indexed")
            # checkpoint.delete(checkpoint_key)
        status = ("API=" + str(f'https://{domain_ip}/api2/json/nodes') + "| response_code=" + str(response.status_code) + "| number_of_events=" + str(count))
        status = response.status_code
        logsummary.log_summary(activation_key=activation_key, meta=meta, url=url, status=status, count=count, source=source, host=host, version=version)


if __name__ == '__main__':
    exit_code = PROXMOX_TASKS().run(sys.argv)
    sys.exit(exit_code)
