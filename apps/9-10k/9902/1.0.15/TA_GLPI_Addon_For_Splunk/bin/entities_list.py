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
from addonutils import get_proxy
from splunklib import modularinput as smi
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from users_list_helper import stream_events, validate_input

ADDON_NAME = "TA_GLPI_Addon_For_Splunk"


class ENTITIES_LIST(smi.Script):
    def __init__(self):
        super(ENTITIES_LIST, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('entities_list')
        scheme.description = 'Entities List'
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
        app_name = "Avotrix-TA_GLPI_Addon_For_Splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, 'TA_GLPI_Addon_For_Splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_glpi_addon_for_splunk_settings")
        account_conf_file = cfm.get_conf('ta_glpi_addon_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')
        # with open("/opt/splunk/etc/apps/demofile4.txt", "w") as f:
        #     f.write(f"ACT_KEY - {activation_key}")
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
        
        proxy_dict, proxy_enabled = get_proxy.get_proxy(account_conf_file=account_conf_file)
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)

        cfm2 = conf_manager.ConfManager(session_key, 'TA_GLPI_Addon_For_Splunk',
                                        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_glpi_addon_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ta_glpi_addon_for_splunk_account')
        account_name = input_item.get("account")
        GLPI_URL = account_conf_file2.get(account_name).get('glpi_url')
        User_Token = account_conf_file2.get(account_name).get('user_token')
        App_Token = account_conf_file2.get(account_name).get('app_token')

        event_count = 0
        try:
            for input_name, input_item in inputs.inputs.items():

                # Account selected in input
                account_name = input_item.get("account")

                if not account_name:
                    raise Exception("No account selected.")

                # Fetch account details
                GLPI_URL = account_conf_file2.get(account_name).get('glpi_url')
                User_Token = account_conf_file2.get(account_name).get('user_token')
                App_Token = account_conf_file2.get(account_name).get('app_token')

                headers = {
                    "App-Token": App_Token,
                    "Authorization": f"user_token {User_Token}",
                    "Content-Type": "application/json"
                }

                # --------------------------------------------------
                # Step 1: Create Session
                # --------------------------------------------------
                session_url = f"{GLPI_URL.rstrip('/')}/initSession"

                session_response = requests.get(
                    session_url,
                    headers=headers,
                    proxies=proxy_dict if proxy_enabled else None,
                    verify=False,
                    timeout=60
                )

                session_response.raise_for_status()

                session_data = session_response.json()

                session_token = session_data.get("session_token")

                if not session_token:
                    raise Exception("Unable to obtain GLPI session token.")

                # --------------------------------------------------
                # Step 2: Fetch Entities
                # --------------------------------------------------
                entity_headers = {
                    "App-Token": App_Token,
                    "Session-Token": session_token,
                    "Content-Type": "application/json"
                }

                entities_url = f"{GLPI_URL.rstrip('/')}/getMyEntities"

                entities_response = requests.get(
                    entities_url,
                    headers=entity_headers,
                    proxies=proxy_dict if proxy_enabled else None,
                    verify=False,
                    timeout=60
                )

                entities_response.raise_for_status()

                entities = entities_response.json()

                # Handle dict response if GLPI returns wrapped data
                if isinstance(entities, dict):

                    if "myentities" in entities:
                        entities = entities["myentities"]
                    else:
                        entities = [entities]

                # --------------------------------------------------
                # Step 3: Send Events to Splunk (without checkpointing)
                # --------------------------------------------------
                # for entity in entities:

                #     event = smi.Event(
                #         data=json.dumps(entity),
                #         sourcetype="glpi:entities",
                #         source="glpi_entities",
                #         index=input_item.get("index", "default")
                #     )

                #     ew.write_event(event)
                #     event_count += 1

                # --------------------------------------------------
                # Step 3: Send Events to Splunk (only new entities - checkpointed)
                # --------------------------------------------------
                checkpoint = checkpointer.KVStoreCheckpointer(
                    "glpi_entities_checkpoint",
                    session_key,
                    "TA_GLPI_Addon_For_Splunk"
                )

                for entity in entities:
                    entity_id = entity.get("id")
                    checkpoint_key = f"{entity_id}"

                    state = checkpoint.get(checkpoint_key)

                    if state is None:
                        event = smi.Event(
                            data=json.dumps(entity),
                            sourcetype="glpi:entities",
                            source="glpi_entities",
                            index=input_item.get("index", "default")
                        )

                        ew.write_event(event)
                        event_count += 1
                        checkpoint.update(checkpoint_key, "Indexed")


                # --------------------------------------------------
                # Step 4: Kill Session
                # --------------------------------------------------
                try:
                    kill_url = f"{GLPI_URL.rstrip('/')}/killSession"

                    requests.get(
                        kill_url,
                        headers=entity_headers,
                        proxies=proxy_dict if proxy_enabled else None,
                        verify=False,
                        timeout=30
                    )

                except Exception:
                    pass

        except Exception as e:

            error_event = smi.Event(
                data=json.dumps({
                    "status": "error",
                    "message": str(e)
                }),
                sourcetype="glpi:entities:error"
            )

            ew.write_event(error_event)

        status = session_response.status_code
        logsummary.log_summary(
            activation_key,
            meta,
            entities_url,
            status,
            event_count,
            source,
            host,
            version
        )


if __name__ == '__main__':
    exit_code = ENTITIES_LIST().run(sys.argv)
    sys.exit(exit_code)