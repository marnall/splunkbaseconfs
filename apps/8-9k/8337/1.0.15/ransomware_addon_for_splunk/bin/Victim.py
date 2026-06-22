import import_declare_test
import hashlib
import sys
import json
import requests
import logging
import os
import datetime
from addonutils import logevent
from addonutils.a_v import A_V
from addonutils import logsummary
from addonutils import getproxy
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib.modular_input import checkpointer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from victim_helper import validate_input

ADDON_NAME = "ransomware_addon_for_splunk"


class VICTIM(smi.Script):
    def __init__(self):
        super(VICTIM, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('Victim')
        scheme.description = 'Victim'
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
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        app_name = "Avotrix-ransomware_addon_for_splunk"
        session_key = self._input_definition.metadata["session_key"]
        host = self._input_definition.metadata['server_host']
        meta = self._input_definition.metadata
        source = os.path.basename(sys.argv[0])
        # Activation Key Check
        cfm = conf_manager.ConfManager(session_key, ADDON_NAME, realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ransomware_addon_for_splunk_settings")
        account_conf_file = cfm.get_conf('ransomware_addon_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')
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
            logevent.internal_logs(meta, {"error": "Cannot read addon version config"}, ADDON_NAME, host)
            sys.exit(2)

        proxy_dict, proxy_enabled = getproxy.get_proxy(account_conf_file=account_conf_file)

        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)
        cfm2 = conf_manager.ConfManager(session_key, ADDON_NAME, realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ransomware_addon_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ransomware_addon_for_splunk_account')
        account_name = input_item.get("account")
        api_key = account_conf_file2.get(account_name).get('api_key')

        count = 0
        headers = {
            "accept": "application/json",
            "X-API-KEY": f"{api_key}"
        }
        url = "https://api-pro.ransomware.live/victims/recent?order=attacked"

        try:
            if proxy_enabled == "1":
                response = requests.get(url, headers=headers, proxies=proxy_dict, timeout=10)
            else:
                response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            victims = data.get("victims", [])
        except Exception:
            victims = []

        checkpoint = checkpointer.KVStoreCheckpointer(
            "ransomware_addon_victims_checkpoints",
            session_key,
            ADDON_NAME
        )

        for v in victims:
            formatted_event = v
            unique_key = hashlib.md5(json.dumps(formatted_event, sort_keys=True).encode()).hexdigest()
            state = checkpoint.get(unique_key)
            if state is None:
                event = smi.Event(
                    data=json.dumps(formatted_event, ensure_ascii=False),
                    index=input_item.get("index"),
                    sourcetype="ransomware:ransomware_victims",
                    source="ransomware_api://victims_ransomware"
                )
                ew.write_event(event)
                checkpoint.update(unique_key, "Indexed")
                count += 1

        status = response.status_code
        logsummary.log_summary(activation_key, meta, status, count, source, host, version)


if __name__ == '__main__':
    exit_code = VICTIM().run(sys.argv)
    sys.exit(exit_code)
