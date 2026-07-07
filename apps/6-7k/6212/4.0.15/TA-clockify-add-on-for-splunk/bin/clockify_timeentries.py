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
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi
ADDON_NAME = "TA-clockify-add-on-for-splunk"


class CLOCKIFY_TIMEENTRIES(smi.Script):

    def __init__(self):
        super(CLOCKIFY_TIMEENTRIES, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('clockify_timeentries')
        scheme.description = 'Clockify TimeEntries'
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
        app_name = "Avotrix-Clockify Add-On for Splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, 'TA-clockify-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_clockify_add_on_for_splunk_settings")
        account_conf_file = cfm.get_conf('ta_clockify_add_on_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')
        source = os.path.basename(sys.argv[0])
        host = self._input_definition.metadata['server_host']
        meta = self._input_definition.metadata

        try:
            ver = conf_manager.ConfManager(session_key, 'TA-clockify-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-app")
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
                "Upgrade Required": "Please update to latest Addon version - Visit - https://splunkbase.splunk.com/app/6212 - If you need assistance, contact support@avotrix.com - Thank you, The Avotrix Team"
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
            cfm2 = conf_manager.ConfManager(session_key, 'TA-clockify-add-on-for-splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_clockify_add_on_for_splunk_account")
            account_conf_file2 = cfm2.get_conf('ta_clockify_add_on_for_splunk_account')
            account_name = input_item.get("global_account")
            api_key = account_conf_file2.get(account_name).get('api_key')
            input_items.append(api_key)

        headers = {'X-Api-Key': api_key}
        url_workspace = 'https://api.clockify.me/api/v1/workspaces'
        if proxy_enabled == "1":
            response_workspace = requests.request("GET", url_workspace, headers=headers, proxies=proxy_dict)
        else:
            response_workspace = requests.request("GET", url_workspace, headers=headers)

        result_workspaces = response_workspace.json()
        workspace_id = []

        for i in result_workspaces:
            workspace_id.append(i['id'])
        count = 0
        for id in workspace_id:
            user_url = f'https://api.clockify.me/api/v1/workspaces/{id}/users?page=1&page-size=500'
            if proxy_enabled == "1":
                response_user = requests.request("GET", user_url, headers=headers, proxies=proxy_dict)
            else:
                response_user = requests.request("GET", user_url, headers=headers)

            result_user = response_user.json()
            user_id = []

            for user in result_user:
                user_id.append(user['id'])
            no = 2
            while result_user != []:
                url_user = f'https://api.clockify.me/api/v1/workspaces/{id}/users?page={no}&page-size=500'
                if proxy_enabled == "1":
                    response_user = requests.request("GET", url_user, headers=headers, proxies=proxy_dict)
                else:
                    response_user = requests.request("GET", url_user, headers=headers)

                result_user = response_user.json()
                no += 1
                for user in result_user:
                    user_id.append(user['id'])

            for userid in user_id:
                timeentry_url = f'https://api.clockify.me/api/v1/workspaces/{id}/user/{userid}/time-entries?page=1&page-size=500'
                if proxy_enabled == "1":
                    response_time = requests.request("GET", timeentry_url, headers=headers, proxies=proxy_dict)
                else:
                    response_time = requests.request("GET", timeentry_url, headers=headers)

                result_time = response_time.json()
                status = response_time.status_code

                if result_time:
                    for time in result_time:
                        checkpoint = checkpointer.KVStoreCheckpointer(
                            "TA-clockify-add-on-for-splunk_checkpoints",
                            session_key,
                            "TA-clockify-add-on-for-splunk"
                        )
                        state = checkpoint.get(time["id"])

                        if state is None:
                            event = smi.Event(
                                data=json.dumps(time),
                                index=input_item.get("index"),
                                sourcetype="Clockify:TimeEntries",
                            )
                            ew.write_event(event)
                            count = count + 1
                            checkpoint.update(str(time["id"]), "Indexed")

                no = 2
                while result_time != []:
                    url_time = f'https://api.clockify.me/api/v1/workspaces/{id}/user/{userid}/time-entries?page={no}&page-size=500'
                    if proxy_enabled == "1":
                        response_time = requests.request("GET", url_time, headers=headers, proxies=proxy_dict)
                    else:
                        response_time = requests.request("GET", url_time, headers=headers)
                    result_time = response_time.json()
                    no += 1
                    if result_time:
                        for time in result_time:
                            state = checkpoint.get(time["id"])
                            if state is None:
                                event = smi.Event(
                                    data=json.dumps(time),
                                    index=input_item.get("index"),
                                    sourcetype="Clockify:TimeEntries",
                                )
                                ew.write_event(event)
                                count = count + 1
                                checkpoint.update(str(time["id"]), "Indexed")

        status = "API=" + str('https://api.clockify.me/api/v1/workspaces/{id}/user/{userid}/time-entries?page={no}&page-size=500') + "| response_code=" + str(status) + "| number_of_events=" + str(count)

        logsummary.log_summary(activation_key=activation_key, meta=meta, url='https://api.clockify.me/api/v1/workspaces/{id}/user/{userid}/time-entries?page={no}&page-size=500', status=status, count=count, source=source, host=host, version=version)


if __name__ == '__main__':
    exit_code = CLOCKIFY_TIMEENTRIES().run(sys.argv)
    sys.exit(exit_code)
