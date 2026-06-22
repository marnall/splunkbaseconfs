import import_declare_test
import hashlib
import sys
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
from listsectors_helper import validate_input

ADDON_NAME = "ransomware_addon_for_splunk"


class LISTSECTORS(smi.Script):
    def __init__(self):
        super(LISTSECTORS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('listsectors')
        scheme.description = 'Listsectors'
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

        cfm = conf_manager.ConfManager(session_key, ADDON_NAME, realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ransomware_addon_for_splunk_settings")
        account_conf_file = cfm.get_conf('ransomware_addon_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')

        # Validate activation key
        v = A_V(app_name, activation_key)
        key_validator = v.v_a_k()
        if key_validator:
            logsummary.activation_log_summary(meta, key_validator, "Inactive", source, host)
            sys.exit(2)

        # Version check
        try:
            ver = conf_manager.ConfManager(session_key, ADDON_NAME, realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-app")
            vers = ver.get_conf('app')
            version = vers.get('id').get('version')
        except Exception:
            logevent.internal_logs(meta, {
                "Permission Required": "Please ensure that the necessary read permissions are granted for the required files to use - Please contact support@avotrix.com."
            }, ADDON_NAME, host)
            sys.exit(2)

        m_ver = int("".join(version.split(".")[:3]).replace(".", "")[:3])
        if m_ver < 15:
            logevent.internal_logs(meta, {
                "Upgrade Required": "Please update to latest Addon version - Visit - https://splunkbase.splunk.com/app/7227"
            }, ADDON_NAME, host)
            sys.exit(2)

        proxy_dict, proxy_enabled = getproxy.get_proxy(account_conf_file=account_conf_file)

        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)

        cfm2 = conf_manager.ConfManager(session_key, ADDON_NAME,
                                        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ransomware_addon_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ransomware_addon_for_splunk_account')
        account_name = input_item.get("account")
        api_key = account_conf_file2.get(account_name).get('api_key')

        count = 0
        headers = {
            "accept": "application/json",
            "X-API-KEY": f"{api_key}"
        }

        url = "https://api-pro.ransomware.live/listsectors"

        try:
            if proxy_enabled == "1":
                response = requests.get(url, headers=headers, proxies=proxy_dict)
            else:
                response = requests.get(url, headers=headers)
            sector_data = response.json()
        except Exception:
            sector_data = {}

        checkpoint = checkpointer.KVStoreCheckpointer(
            "ransomware_addon_listsectors_checkpoints",
            session_key,
            ADDON_NAME
        )

        formatted_event = sector_data
        unique_key = hashlib.md5(json.dumps(formatted_event, sort_keys=True).encode()).hexdigest()
        state = checkpoint.get(unique_key)
        if state is None:
            event = smi.Event(
                data=json.dumps(formatted_event),
                index=input_item.get("index"),
                sourcetype="ransomware:listsectors",
                source="ransomware_api://listsectors"
            )
            ew.write_event(event)
            checkpoint.update(unique_key, "Indexed")
            count += 1

        # Final log summary
        status = response.status_code
        logsummary.log_summary(activation_key, meta, url, status, count, source, host, version)


if __name__ == '__main__':
    exit_code = LISTSECTORS().run(sys.argv)
    sys.exit(exit_code)
