import import_declare_test
import hashlib
import sys
import math
import json
import re
import html as html_lib
from html.parser import HTMLParser
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
from ticket_details_helper import stream_events, validate_input

ADDON_NAME = "TA_GLPI_Addon_For_Splunk"


# NEW: strips HTML tags/attributes (and decodes entities like &amp;) from
# GLPI's rich-text followup content, leaving just the plain text a human typed.
class _TagStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return "".join(self.parts)


def strip_html(raw):
    if not raw:
        return raw
    stripper = _TagStripper()
    try:
        stripper.feed(raw)
        text = stripper.get_text()
    except Exception:
        # fall back to a regex strip if the parser chokes on malformed markup
        text = re.sub(r"<[^>]+>", " ", raw)
    text = html_lib.unescape(text)
    # collapse repeated whitespace/newlines left behind by block tags
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def clean_followup_content(followups):
    for f in followups:
        content = f.get("content")
        if isinstance(content, list):
            f["content"] = [strip_html(c) for c in content]
        elif isinstance(content, str):
            f["content"] = strip_html(content)
    return followups


# NEW: fetches followups/comments for a single ticket. Returns [] on any
# failure so one bad ticket can't abort the whole run.
def get_ticket_followups(base_url, headers, ticket_id, proxy_dict, proxy_enabled):
    url = f"{base_url.rstrip('/')}/Ticket/{ticket_id}/ITILFollowup/"
    try:
        resp = requests.get(
            url,
            headers=headers,
            proxies=proxy_dict if proxy_enabled else None,
            verify=False,
            timeout=60
        )
        if resp.status_code == 200:
            data = resp.json()
            data = data if isinstance(data, list) else []
            return clean_followup_content(data)
        return []
    except Exception:
        return []


class TICKET_DETAILS(smi.Script):
    def __init__(self):
        super(TICKET_DETAILS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('ticket_details')
        scheme.description = 'Ticket Details'
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

        # NEW: threshold timestamp - only tickets modified on/after this will be ingested
        seven_days_ago = datetime.datetime.now() - timedelta(days=7)

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
                # Step 2: Fetch Tickets (paginated, all accessible)
                # --------------------------------------------------
                ticket_headers = {
                    "App-Token": App_Token,
                    "Session-Token": session_token,
                    "Content-Type": "application/json"
                }
 
                # Stripping any trailing slash to ensure clean query appending
                base_tickets_url = f"{GLPI_URL.rstrip('/')}/Ticket"
 
                page_size = 50
                start = 0
                tickets = []
 
                while True:
                    # CHANGE 1: Append range directly to URL query parameters instead of custom headers
                    tickets_url = f"{base_tickets_url}?range={start}-{start + page_size - 1}"
 
                    tickets_response = requests.get(
                        tickets_url,
                        headers=ticket_headers,
                        proxies=proxy_dict if proxy_enabled else None,
                        verify=False,
                        timeout=60
                    )

                    if tickets_response.status_code not in (200, 206):
                        tickets_response.raise_for_status()
 
                    batch = tickets_response.json()

                    # CHANGE 2: Safeguard against GLPI out-of-bounds dictionary warnings (e.g., {"0": "No item found"})
                    if isinstance(batch, dict):
                        if "message" in batch or "0" in batch:
                            break
                        batch = [batch]
 
                    if not batch:
                        break
 
                    tickets.extend(batch)
 
                    # Content-Range header looks like "0-49/4253"; stop once everything is fetched
                    content_range = tickets_response.headers.get("Content-Range", "")
                    if "/" in content_range:
                        try:
                            total = int(content_range.split("/")[-1])
                            if start + page_size >= total:
                                break
                        except ValueError:
                            pass
                    else:
                        break  # No more pages indicated
 
                    start += page_size

 
                

                # --------------------------------------------------
                # Step 3: Send Events to Splunk (only changed tickets)
                # --------------------------------------------------
                    
    #                 with open("/opt/splunk/etc/glpi.txt", "a") as log_file:
    #                     log_file.write(
    #                     # f"Ticket={tickets_url}, "
    #                     f"Status Code={ticket}\n"
    # )         
                # for ticket in tickets:
                #     event = smi.Event(
                #         data=json.dumps(ticket),
                #         sourcetype="glpi:tickets",
                #         source="glpi_ticket_details",
                #         index=input_item.get("index", "default")
                #     )

                #     ew.write_event(event)
                #     event_count += 1


                checkpoint = checkpointer.KVStoreCheckpointer(
                    "glpi_ticket_details_checkpoint",
                    session_key,
                    "TA_GLPI_Addon_For_Splunk"
                )

                for ticket in tickets:
                    ticket_id = ticket.get("id")
                    date_mod = ticket.get("date_mod")
                    checkpoint_key = f"{ticket_id}_{date_mod}"

                    # NEW: only ingest tickets modified within the last 7 days; older tickets are skipped before checkpointing runs
                    if date_mod:
                        try:
                            ticket_date = datetime.datetime.strptime(date_mod, "%Y-%m-%d %H:%M:%S")
                            if ticket_date < seven_days_ago:
                                continue
                        except ValueError:
                            pass
                    # END NEW

                    state = checkpoint.get(checkpoint_key)

                    if state is None:
                        # NEW: attach followups/comments only for tickets that will actually be indexed
                        ticket["followups"] = get_ticket_followups(
                            GLPI_URL, ticket_headers, ticket_id, proxy_dict, proxy_enabled
                        )

                        event = smi.Event(
                            data=json.dumps(ticket),
                            sourcetype="glpi:tickets",
                            source="glpi_ticket_details",
                            index=input_item.get("index", "default")
                        )

                        ew.write_event(event)
                        event_count += 1
                        checkpoint.update(checkpoint_key, "Indexed")
                    # checkpoint.delete(checkpoint_key)
 
                # --------------------------------------------------
                # Step 4: Kill Session
                # --------------------------------------------------
                try:
                    kill_url = f"{GLPI_URL.rstrip('/')}/killSession"
 
                    requests.get(
                        kill_url,
                        headers=ticket_headers,
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
                sourcetype="glpi:tickets:error"
            )
 
            ew.write_event(error_event)
 
        status = session_response.status_code
        logsummary.log_summary(
            activation_key,
            meta,
            base_tickets_url,
            status,
            event_count,
            source,
            host,
            version
        )

if __name__ == '__main__':
    exit_code = TICKET_DETAILS().run(sys.argv)
    sys.exit(exit_code)