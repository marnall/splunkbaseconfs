import import_declare_test
import sys
import json
from requests.auth import HTTPBasicAuth
import requests
import logging
import os
import base64
import datetime
from addonutils import logevent
from addonutils.activation_key import _validate_activation_key
from addonutils import logsummary
from addonutils import eventdata
from addonutils import getproxy
from splunklib import modularinput as smi
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

ADDON_NAME = "TA-bitwarden-add-on-for-splunk"


# def logger_for_input(input_name: str) -> logging.Logger:
# return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


class COLLECTION(smi.Script):

    def __init__(self):
        super(COLLECTION, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('collection')
        scheme.description = 'Collection'
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

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        app_name = "Bitwarden"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, 'TA-bitwarden-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_bitwarden_add_on_for_splunk_settings")
        account_conf_file = cfm.get_conf('ta_bitwarden_add_on_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')
        source = os.path.basename(sys.argv[0])
        host = self._input_definition.metadata['server_host']
        meta = self._input_definition.metadata
        key_validator = _validate_activation_key(app_name, activation_key)
        if key_validator:
            logsummary.activation_log_summary(meta, key_validator, "Inactive", source, host)
            sys.exit(2)
        proxy_enabled = account_conf_file.get('proxy').get('proxy_enabled')
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)
        cfm2 = conf_manager.ConfManager(session_key, 'TA-bitwarden-add-on-for-splunk',
                                        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_bitwarden_add_on_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ta_bitwarden_add_on_for_splunk_account')
        account_name = input_item.get("account")
        acc_username = account_conf_file2.get(account_name).get('username')
        acc_password = account_conf_file2.get(account_name).get('password')
        acc_domain = account_conf_file2.get(account_name).get('domain')
        dom = f'https://{acc_domain}'
        payload = {
            'scope': 'api.organization',
            'grant_type': 'client_credentials',
            'client_id': acc_username,
            'client_secret': acc_password
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        client_url = f'{dom}' + "/identity/connect/token"
        proxy_dict = getproxy.get_proxy(activation_key, account_conf_file)
        index = input_item.get("index")
        src = 'bitwarden:groups'
        ckp = 'id'
        data_url = f'https://{acc_domain}/api/public/groups'
        status, url, count = eventdata.event_data(proxy_enabled, client_url, headers, payload, proxy_dict, acc_domain, session_key, ew, index, src, ckp, data_url)
        logsummary.log_summary(activation_key, meta, url, status, count, source, host)


if __name__ == '__main__':
    exit_code = COLLECTION().run(sys.argv)
    sys.exit(exit_code)
