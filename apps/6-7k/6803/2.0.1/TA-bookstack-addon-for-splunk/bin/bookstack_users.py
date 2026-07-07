import import_declare_test
import logging
import sys
import json
from requests.auth import HTTPBasicAuth
import requests
import os
import base64
import hashlib
import datetime
from splunklib import modularinput as smi
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from addonutils import logevent
from addonutils.activation_key import _validate_activation_key
from addonutils import logsummary
from addonutils import getproxy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

ADDON_NAME = "TA-bookstack-addon-for-splunk"


class BOOKSTACK_USERS(smi.Script):

    def __init__(self):
        super(BOOKSTACK_USERS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('bookstack_users')
        scheme.description = 'bookstack:users'
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
        app_name = "Bookstack addon for splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, 'TA-bookstack-addon-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_bookstack_addon_for_splunk_settings")
        account_conf_file = cfm.get_conf('ta_bookstack_addon_for_splunk_settings')
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
        cfm2 = conf_manager.ConfManager(session_key, 'TA-bookstack-addon-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_bookstack_addon_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ta_bookstack_addon_for_splunk_account')
        account_name = input_item.get('global_account')
        domain = account_conf_file2.get(account_name).get('domain')
        token_id = account_conf_file2.get(account_name).get('token_id')
        token_secret = account_conf_file2.get(account_name).get('token_secret')
        proxy_dict = getproxy.get_proxy(activation_key, account_conf_file)
        off = 0
        count = 0
        url1 = f"https://bookstack.{domain}/api/users"

        headers = {'Authorization': f'Token {token_id}:{token_secret}'}
        if proxy_enabled == "1":
            response = requests.get(url1, headers=headers, proxies=proxy_dict)
        else:
            response = requests.get(url1, headers=headers)
        response = requests.get(url1, headers=headers)
        r_json = response.json()
        Tot = r_json["total"]
        while Tot >= off:
            url = f"https://bookstack.{domain}/api/users?offset={off}&count=500"

            headers = {'Authorization': f'Token {token_id}:{token_secret}'}
            if proxy_enabled == "1":
                response = requests.get(url, headers=headers, proxies=proxy_dict)
            else:
                response = requests.get(url, headers=headers)

            r_json = response.json()
            for book in r_json["data"]:
                checkpoint = checkpointer.KVStoreCheckpointer(
                    "TA-bookstack-addon-for-splunk_checkpoints",
                    session_key,
                    "TA-bookstack-addon-for-splunk"
                )
                state = checkpoint.get(str(book["updated_at"]) + str(book["id"]))
                if state is None:
                    event = smi.Event(
                        data=json.dumps(book),
                        index=input_item.get("index"),
                        sourcetype="bookstack_users",
                    )
                    ew.write_event(event)
                    count = count + 1
                    checkpoint.update(str(book["updated_at"]) + str(book["id"]), "Indexed")
                # checkpoint.delete(str(book["updated_at"]) + str(book["id"]))
            off = off + 500

        status = response.status_code

        logsummary.log_summary(activation_key, meta, url, status, count, source, host)


if __name__ == '__main__':
    exit_code = BOOKSTACK_USERS().run(sys.argv)
    sys.exit(exit_code)
