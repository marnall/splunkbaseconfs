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
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
ADDON_NAME = "ransomware_addon_for_splunk"


class PRESSALL(smi.Script):
    def __init__(self):
        super(PRESSALL, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('press_recent')
        scheme.description = 'Press Recent'
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
                required_on_create=True
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        app_name = "Avotrix-ransomware_addon_for_splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, ADDON_NAME, realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ransomware_addon_for_splunk_settings")
        account_conf_file = cfm.get_conf('ransomware_addon_for_splunk_settings')
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
        if m_ver < 15:
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

        cfm2 = conf_manager.ConfManager(session_key, ADDON_NAME, realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ransomware_addon_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ransomware_addon_for_splunk_account')
        account_name = input_item.get("account")
        api_key = account_conf_file2.get(account_name).get('api_key')

        headers = {
            "accept": "application/json",
            "X-API-KEY": f"{api_key}"
        }

        country_codes = [
            "AF", "AL", "DZ", "AD", "AO", "AG", "AR", "AM", "AU", "AT", "AZ",
            "BS", "BH", "BD", "BB", "BY", "BE", "BZ", "BJ", "BT", "BO", "BA",
            "BW", "BR", "BN", "BG", "BF", "BI", "CV", "KH", "CM", "CA", "CF",
            "TD", "CL", "CN", "CO", "KM", "CG", "CD", "CK", "CR", "CI", "HR",
            "CU", "CY", "CZ", "DK", "DJ", "DM", "DO", "EC", "EG", "SV", "GQ",
            "ER", "EE", "SZ", "ET", "FJ", "FI", "FR", "GA", "GM", "GE", "DE",
            "GH", "GR", "GD", "GT", "GN", "GW", "GY", "HT", "HN", "HU", "IS",
            "IN", "ID", "IR", "IQ", "IE", "IL", "IT", "JM", "JP", "JO", "KZ",
            "KE", "KI", "KP", "KR", "KW", "KG", "LA", "LV", "LB", "LS", "LR",
            "LY", "LI", "LT", "LU", "MG", "MW", "MY", "MV", "ML", "MT", "MH",
            "MR", "MU", "MX", "FM", "MD", "MC", "MN", "ME", "MA", "MZ", "MM",
            "NA", "NR", "NP", "NL", "NZ", "NI", "NE", "NG", "MK", "NO", "OM",
            "PK", "PW", "PA", "PG", "PY", "PE", "PH", "PL", "PT", "QA", "RO",
            "RU", "RW", "KN", "LC", "VC", "WS", "SM", "ST", "SA", "SN", "RS",
            "SC", "SL", "SG", "SK", "SI", "SB", "SO", "ZA", "SS", "ES", "LK",
            "SD", "SR", "SE", "CH", "SY", "TW", "TJ", "TZ", "TH", "TL", "TG",
            "TO", "TT", "TN", "TR", "TM", "TV", "UG", "UA", "AE", "GB", "US",
            "UY", "UZ", "VU", "VA", "VE", "VN", "YE", "ZM", "ZW"
        ]

        checkpoint = checkpointer.KVStoreCheckpointer(
            "ransomware_addon_press_recent_checkpoints",
            session_key,
            ADDON_NAME
        )

        count = 0
        url = ""
        for country in country_codes:
            url = f"https://api-pro.ransomware.live/press/recent?country={country}"
            try:
                response = requests.get(url, headers=headers, proxies=proxy_dict if proxy_enabled == "1" else None)
                data = response.json()
                press_results = data.get("results", [])

                for result in press_results:
                    unique_key = hashlib.md5(json.dumps(result, sort_keys=True).encode()).hexdigest()
                    state = checkpoint.get(unique_key)
                    if state is None:
                        event = smi.Event(
                            data=json.dumps(result),
                            index=input_item.get("index"),
                            sourcetype="ransomware:press_recent",
                            source="press_ransomware://press_recent"
                        )
                        ew.write_event(event)
                        checkpoint.update(unique_key, "Indexed")
                        count += 1

            except Exception as e:
                logging.error(f" Failed fetching /press/recent for {country}: {e}")
                continue

        status = response.status_code if 'response' in locals() else 500
        logsummary.log_summary(activation_key, meta, url, status, count, source, host, version)


if __name__ == '__main__':
    exit_code = PRESSALL().run(sys.argv)
    sys.exit(exit_code)
