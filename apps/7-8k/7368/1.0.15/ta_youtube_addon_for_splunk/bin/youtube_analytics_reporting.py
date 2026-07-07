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

ADDON_NAME = "ta_youtube_addon_for_splunk"


class YOUTUBE_ANALYTICS_REPORTING(smi.Script):
    def __init__(self):
        super(YOUTUBE_ANALYTICS_REPORTING, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('youtube_analytics_reporting')
        scheme.description = 'YouTube Analytics Reporting'
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
        scheme.add_argument(
            smi.Argument(
                'metrics',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'dimensions',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'start_date',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'end_date',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'use_existing_checkpoint',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        app_name = "Avotrix-ta_youtube_addon_for_splunk"
        proxy_enabled = 0
        session_key = self._input_definition.metadata["session_key"]
        cfm = conf_manager.ConfManager(session_key, 'ta_youtube_addon_for_splunk', realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_youtube_addon_for_splunk_settings")
        account_conf_file = cfm.get_conf('ta_youtube_addon_for_splunk_settings')
        activation_key = account_conf_file.get('additional_parameters').get('activation_key')
        source = os.path.basename(sys.argv[0])
        host = self._input_definition.metadata['server_host']
        meta = self._input_definition.metadata
        # key_validator = _validate_activation_key(app_name, activation_key)
        # if key_validator:
        #     logsummary.activation_log_summary(meta, key_validator, "Inactive", source, host)
        #     sys.exit(2)

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
                "Upgrade Required": "Please update to latest Addon version - Visit - https://splunkbase.splunk.com/- If you need assistance, contact support@avotrix.com - Thank you, The Avotrix Team"
            }
            logevent.internal_logs(meta, event, ADDON_NAME, host)
            sys.exit(2)

        proxy_dict, proxy_enabled = getproxy.get_proxy(account_conf_file=account_conf_file)
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)
        cfm2 = conf_manager.ConfManager(session_key, 'ta_youtube_addon_for_splunk',
                                        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_youtube_addon_for_splunk_account")
        account_conf_file2 = cfm2.get_conf('ta_youtube_addon_for_splunk_account')
        account_name = input_item.get("account")
        acc_id = account_conf_file2.get(account_name).get('client_id')
        acc_secret = account_conf_file2.get(account_name).get('client_secret')

        acc_refresh_token = account_conf_file2.get(account_name).get('refresh_token')
        # acc_scope = account_conf_file2.get(account_name).get('scope')
        # acc_endpoint = account_conf_file2.get(account_name).get('endpoint')
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)
            dimensions = input_item['dimensions']
            metrics = input_item['metrics']
            try:
                start_date = input_item['start_date']
                end_date = input_item['end_date']
            except KeyError:
                if 'start_date' not in input_item and 'end_date' not in input_item:
                    logging.info("Start date and end date not provided in input_item.")
                    start_date = None
                    end_date = None
                elif 'start_date' not in input_item:
                    logging.info("Start date not provided in input_item.")
                    start_date = None
                    end_date = input_item['end_date']
                elif 'end_date' not in input_item:
                    logging.info("End date not provided in input_item.")
                    start_date = input_item['start_date']
                    end_date = None
        url = "https://oauth2.googleapis.com/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {
            "client_id": acc_id,
            "grant_type": "refresh_token",
            "client_secret": acc_secret,
            "refresh_token": acc_refresh_token
        }
        if proxy_enabled == "1":
            response = requests.request("POST", url, headers=headers, data=payload, proxies=proxy_dict)
        else:
            response = requests.request("POST", url, headers=headers, data=payload)

        r = response.json()
        api_token = r["access_token"]
        token = str(api_token)
        # input_item['final_tok'] = token
        # input_items.append(input_item)
        if (start_date and end_date):
            url1 = f"https://youtubeanalytics.googleapis.com/v2/reports?dimensions={dimensions}&metrics={metrics}&ids=channel==MINE&startDate={start_date}&endDate={end_date}"

        elif (start_date and not end_date):
            today = datetime.datetime.now()
            yesterday = today - timedelta(days=1)
            end1 = yesterday.strftime("%Y-%m-%d")
            url1 = f"https://youtubeanalytics.googleapis.com/v2/reports?dimensions={dimensions}&metrics={metrics}&ids=channel==MINE&startDate={start_date}&endDate={end1}"

        else:
            today = datetime.datetime.now()
            yesterday = today - timedelta(days=1)
            end2 = yesterday.strftime("%Y-%m-%d")
            yesterday1 = today - timedelta(days=7)
            start2 = yesterday1.strftime("%Y-%m-%d")
            url1 = f"https://youtubeanalytics.googleapis.com/v2/reports?dimensions={dimensions}&metrics={metrics}&ids=channel==MINE&startDate={start2}&endDate={end2}"
        token = api_token
        headers = {'Authorization': f'Bearer {token}'}
        if proxy_enabled == "1":
            response = requests.request("GET", url1, headers=headers, proxies=proxy_dict)
        else:
            response = requests.request("GET", url1, headers=headers)
        r1 = response.json()
        head = r1['columnHeaders']
        rows = r1['rows']
        # print(head)
        # print(rows)

        count = 0

        # Replace with the appropriate app name
        checkpoint = checkpointer.KVStoreCheckpointer(
            "ta_youtube_addon_for_splunk_checkpoints", session_key,
            "ta_youtube_addon_for_splunk"
        )
        for i in rows:
            dict_test = {}
            for j in range(len(i)):
                dict_test[head[j]["name"]] = i[j]

            # Generate a unique key for the checkpoint (hash of the event data)
            unique_key = hashlib.md5(json.dumps(dict_test, sort_keys=True).encode()).hexdigest()

            try:
                # Check if the event is already processed
                state = checkpoint.get(unique_key)

                if state is None:
                    # Process and write the event if not already checkpointed
                    event = smi.Event(
                        data=json.dumps(dict_test),
                        sourcetype='youtube_analytics_reporting',
                        index=input_item.get("index"),  # Use the appropriate index
                    )
                    ew.write_event(event)
                    count += 1

                    # Update the checkpoint
                    checkpoint.update(unique_key, "Indexed")
                # checkpoint.delete(unique_key)
            except Exception as e:
                print(f"Error processing event: {e}")
                pass

        # Log status
        status = response.status_code
        logsummary.log_summary(
            activation_key=activation_key,
            meta=meta,
            url=url1,
            status=status,
            count=count,
            source=source,
            host=host,
            version=version
        )


if __name__ == '__main__':
    exit_code = YOUTUBE_ANALYTICS_REPORTING().run(sys.argv)
    sys.exit(exit_code)
