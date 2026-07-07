import os
import import_declare_test
import sys
import json
from requests.auth import HTTPBasicAuth
import requests
import logging
import base64
from addonutils import logevent
from addonutils.a_v import A_V
from addonutils import logsummary
from addonutils import getproxy
import datetime
from splunklib import modularinput as smi
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

ADDON_NAME = "TA-twilio-addon-for-splunk"


class TWILIO_MESSAGES(smi.Script):

    def __init__(self):
        super(TWILIO_MESSAGES, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('twilio_messages')
        scheme.description = 'twilio:messages'
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
        app_name = "Avotrix-Twilio Addon For Splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, 'TA-twilio-addon-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_twilio_addon_for_splunk_settings")
        account_conf_file = cfm.get_conf('ta_twilio_addon_for_splunk_settings')
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
            ver = conf_manager.ConfManager(session_key, 'TA-twilio-addon-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-app")
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
        cfm2 = conf_manager.ConfManager(session_key, 'TA-twilio-addon-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_twilio_addon_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ta_twilio_addon_for_splunk_account')
        account_name = input_item.get("global_account")
        account_sid = account_conf_file2.get(account_name).get('account_sid')
        token = account_conf_file2.get(account_name).get('token')

        url = "https://api.twilio.com/2010-04-01/Accounts/" + account_sid + "/Messages.json"
        if proxy_enabled == "1":
            response = requests.get(url, auth=HTTPBasicAuth(account_sid, token), proxies=proxy_dict)
        else:
            response = requests.get(url, auth=HTTPBasicAuth(account_sid, token))
        r = response.json()
        count = 0
        for ids in r["messages"]:
            checkpoint = checkpointer.KVStoreCheckpointer(
                "TA-twilio-addon-for-splunk_checkpoints",
                session_key,
                "TA-twilio-addon-for-splunk"
            )
            state = checkpoint.get(str(ids["sid"]) + str(ids["date_created"]))
            if state is None:

                event = smi.Event(
                    data=json.dumps(ids, indent=2),
                    index=input_item.get("index"),
                    sourcetype='twilio:messages',
                )
                ew.write_event(event)
                count = count + 1
                checkpoint.update(str(ids["sid"]) + str(ids["date_created"]), "Indexed")
            # checkpoint.delete(str(ids["sid"]) + str(ids["date_created"]))

        while r["next_page_uri"] is not None:
            url = 'https://api.twilio.com' + r["next_page_uri"]
            if proxy_enabled == "1":
                response = requests.get(url, auth=HTTPBasicAuth(account_sid, token), proxies=proxy_dict)
            else:
                response = requests.get(url, auth=HTTPBasicAuth(account_sid, token))
            r = response.json()
            for ids in r["messages"]:
                checkpoint = checkpointer.KVStoreCheckpointer(
                    "TA-twilio-addon-for-splunk_checkpoints",
                    session_key,
                    "TA-twilio-addon-for-splunk"
                )
                state = checkpoint.get(str(ids["sid"]) + str(ids["date_created"]))
                if state is None:

                    event = smi.Event(
                        data=json.dumps(ids, indent=2),
                        index=input_item.get("index"),
                        sourcetype='twilio:messages',
                    )
                    ew.write_event(event)
                    count = count + 1
                    checkpoint.update(str(ids["sid"]) + str(ids["date_created"]), "Indexed")
                # checkpoint.delete(str(ids["sid"]) + str(ids["date_created"]))

                if r["next_page_uri"] is None:
                    break
        status = response.status_code
        logsummary.log_summary(activation_key, meta, url, status, count, source, host, version)


if __name__ == '__main__':
    exit_code = TWILIO_MESSAGES().run(sys.argv)
    sys.exit(exit_code)
