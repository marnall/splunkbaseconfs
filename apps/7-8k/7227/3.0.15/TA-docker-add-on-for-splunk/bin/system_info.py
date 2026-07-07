import import_declare_test
import sys
import json
from requests.auth import HTTPBasicAuth
import requests
import logging
import os
from addonutils import logevent
from addonutils.a_v import A_V
from addonutils import logsummary
from addonutils import getproxy
from splunklib import modularinput as smi
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

ADDON_NAME = "TA-docker-add-on-for-splunk"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


class SYSTEM_INFO(smi.Script):

    def __init__(self):
        super(SYSTEM_INFO, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('system_info')
        scheme.description = 'System Info'
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
        app_name = "Avotrix-Docker Add-On for Splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, ADDON_NAME, realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_docker_add_on_for_splunk_settings")
        account_conf_file = cfm.get_conf('ta_docker_add_on_for_splunk_settings')
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
        cfm2 = conf_manager.ConfManager(session_key, 'TA-docker-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_docker_addon_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ta_docker_add_on_for_splunk_account')
        account_name = input_item.get("global_account")
        docker_ip = account_conf_file2.get(account_name).get('docker_ip')
        input_items.append(docker_ip)
        docker_port = account_conf_file2.get(account_name).get('docker_port')
        input_items.append(docker_port)
        count = 0
        status = ''
        url_container = f'https://{docker_ip}:{docker_port}/v1.41/info'

        if proxy_enabled == "1":
            response_images = requests.request("GET", url_container, proxies=proxy_dict)
        else:
            response_images = requests.request("GET", url_container)

        result_images = response_images.json()
        status = response_images.status_code
        event = smi.Event(
            data=json.dumps(result_images, indent=2),
            index=input_item.get("index"),
            sourcetype="Docker_container_info",
        )
        ew.write_event(event)
        count += 1

        status = status

        logsummary.log_summary(activation_key=activation_key, meta=meta, url=url_container, status=status, count=count, source=source, host=host, version=version)


if __name__ == '__main__':
    exit_code = SYSTEM_INFO().run(sys.argv)
    sys.exit(exit_code)
