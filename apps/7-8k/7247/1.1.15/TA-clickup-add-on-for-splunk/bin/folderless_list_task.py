import import_declare_test
import sys
import os
import json
import requests
from requests.auth import HTTPBasicAuth
import logging
import base64
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi
from solnlib import conf_manager, log
from addonutils import logevent
from addonutils.a_v import A_V
from addonutils import logsummary
from addonutils import getproxy
import datetime
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

ADDON_NAME = "TA-clickup-add-on-for-splunk"


class FOLDERLESS_LIST_TASK(smi.Script):

    def __init__(self):
        super(FOLDERLESS_LIST_TASK, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('folderless_list_task')
        scheme.description = 'Folderless List Task'
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

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        app_name = "Avotrix-TA-clickup-add-on-for-splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(
            session_key,
            'TA-clickup-add-on-for-splunk',
            realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_clickup_add_on_for_splunk_settings"
        )
        account_conf_file = cfm.get_conf('ta_clickup_add_on_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')
        source = os.path.basename(sys.argv[0])
        host = self._input_definition.metadata['server_host']
        meta = self._input_definition.metadata

        # Activation key check
        v = A_V(app_name, activation_key)
        key_validator = v.v_a_k()
        if key_validator:
            logsummary.activation_log_summary(meta, key_validator, "Inactive", source, host)
            sys.exit(2)

        # Version fetch and compatibility check
        try:
            ver = conf_manager.ConfManager(
                session_key,
                ADDON_NAME,
                realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-app"
            )
            vers = ver.get_conf('app')
            version = vers.get('id').get('version')
        except Exception:
            event = {
                "Permission Required": "Please ensure that the necessary read permissions are granted for the required files to use - Please contact support@avotrix.com. - Thank you, The Avotrix Team"
            }
            proxy_dict, proxy_enabled = getproxy.get_proxy(account_conf_file=account_conf_file)
            logevent.internal_logs(meta, event, ADDON_NAME, host)
            sys.exit(2)

        # Version compatibility check (minor version >= 15)
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
                "Upgrade Required": "Please update to latest Addon version - Visit - https://splunkbase.splunk.com/app/6546 - If you need assistance, contact support@avotrix.com - Thank you, The Avotrix Team"
            }
            logevent.internal_logs(meta, event, ADDON_NAME, host)
            sys.exit(2)

        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)

        cfm2 = conf_manager.ConfManager(
            session_key,
            'TA-clickup-add-on-for-splunk',
            realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_clickup_add_on_for_splunk_account"
        )
        account_conf_file2 = cfm2.get_conf('ta_clickup_add_on_for_splunk_account')
        account_name = input_item.get("global_account")
        name = account_conf_file2.get(account_name).get('name')
        input_items.append(name)
        token = account_conf_file2.get(account_name).get('api_token')
        input_items.append(token)

        # FIX: Proxy tuple unpacking — done once, used everywhere
        proxy_dict, proxy_enabled = getproxy.get_proxy(account_conf_file=account_conf_file)

        # Fetch all teams
        url = 'https://api.clickup.com/api/v2/team'
        headers = {"Authorization": token}

        if proxy_enabled == "1":
            response = requests.get(url, headers=headers, proxies=proxy_dict)
        else:
            response = requests.get(url, headers=headers)

        data = response.json()
        team_id = []
        count = 0

        for team in data["teams"]:
            team_id.append(team["id"])

        # Fetch all spaces
        spaces_id = []
        for tid in team_id:
            url = "https://api.clickup.com/api/v2/team/" + tid + "/space"
            headers = {"Authorization": token}
            if proxy_enabled == "1":
                response = requests.get(url, headers=headers, proxies=proxy_dict)
            else:
                response = requests.get(url, headers=headers)
            data = response.json()
            for space in data["spaces"]:
                spaces_id.append(space["id"])

        # Fetch folderless lists directly from each space
        lists_id = []
        for space_id in spaces_id:
            url = "https://api.clickup.com/api/v2/space/" + space_id + "/list"
            headers = {"Authorization": token}
            if proxy_enabled == "1":
                response = requests.get(url, headers=headers, proxies=proxy_dict)
            else:
                response = requests.get(url, headers=headers)
            data = response.json()
            for lst in data["lists"]:
                lists_id.append(lst["id"])

        # FIX: Checkpoint initialized ONCE outside all loops
        checkpoint = checkpointer.KVStoreCheckpointer(
            "TA-clickup-add-on-for-splunk_checkpoints",
            session_key,
            "TA-clickup-add-on-for-splunk"
        )

        for list_id in lists_id:
            LastPage = False
            page = 0

            while not LastPage:
                # FIX: total_task reset karo har page pe — accumulation bug fixed
                total_task = []

                url = "https://api.clickup.com/api/v2/list/" + list_id + "/task"
                query = {
                    "include_closed": "true",
                    "subtasks": "true",
                    "page": page,
                }
                headers = {"Authorization": token}

                if proxy_enabled == "1":
                    response = requests.get(url, headers=headers, params=query, proxies=proxy_dict)
                else:
                    response = requests.get(url, headers=headers, params=query)

                data = response.json()

                for task in data["tasks"]:
                    checkpoint_key = str(task["id"]) + str(task["name"])
                    state = checkpoint.get(checkpoint_key)
                    if state is None:
                        total_task.append(task)
                        count += 1
                        checkpoint.update(checkpoint_key, "Indexed")

                # FIX: Sirf naye tasks likho, aur sirf tab jab list empty na ho
                if total_task:
                    event = smi.Event(
                        data=json.dumps(total_task, indent=2),
                        index=input_item.get("index"),
                        sourcetype="clickup:folderless_list_task"
                    )
                    event_writer.write_event(event)

                LastPage = data["last_page"]
                page += 1

        status = (
            "API=" + url +
            "| response_code=" + str(response.status_code) +
            "| number_of_events=" + str(count)
        )

        # FIX: Named parameters in logsummary call + version added
        logsummary.log_summary(
            activation_key=activation_key,
            meta=meta,
            url=url,
            status=status,
            count=count,
            source=source,
            host=host,
            version=version
        )


if __name__ == '__main__':
    exit_code = FOLDERLESS_LIST_TASK().run(sys.argv)
    sys.exit(exit_code)