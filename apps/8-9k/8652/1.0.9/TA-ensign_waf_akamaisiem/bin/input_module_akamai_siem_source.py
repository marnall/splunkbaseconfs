# encoding = utf-8

"""
Akamai SIEM Modular Input - Core Business Logic
================================================
This module contains the data collection logic for fetching
Akamai SIEM security events via the Akamai SIEM API v1.

Migrated from 7 identical scripted inputs into a single,
configurable modular input powered by UCC framework.
"""

import os
import sys
import json
import base64
import re
import datetime
import urllib.parse
import requests
from urllib.parse import unquote

# EdgeGrid auth — bundled in lib/
from akamai.edgegrid import EdgeGridAuth


# ==========================================
# OFFSET STATE MANAGER
# ==========================================
class OffsetStateManager:
    """
    Manages file-based offset (cursor) checkpointing for Akamai SIEM API.
    Each input stanza gets its own offset file under:
        <TA_ROOT>/collection/<stanza_name>/akamai_offset.txt
    """

    def __init__(self, stanza_name, helper):
        self.helper = helper
        self.stanza_name = stanza_name

        bin_dir = os.path.dirname(os.path.abspath(__file__))
        ta_root = os.path.dirname(bin_dir)

        safe_name = re.sub(r'[<>:"/\\|?*]', '_', stanza_name)
        self.collection_dir = os.path.join(ta_root, "collection", safe_name)
        self.offset_file = os.path.join(self.collection_dir, "akamai_offset.txt")
        self._ensure_dir()

    def _ensure_dir(self):
        if not os.path.exists(self.collection_dir):
            try:
                os.makedirs(self.collection_dir, exist_ok=True)
                self.helper.log_info(
                    f"[+] Collection dir created for '{self.stanza_name}': "
                    f"{self.collection_dir}"
                )
            except OSError as e:
                self.helper.log_error(
                    f"[-] Failed to create collection dir: {str(e)}"
                )
                raise

    def read_offset(self):
        if os.path.isfile(self.offset_file):
            try:
                with open(self.offset_file, "r") as f:
                    offset = f.read().strip()
                    if offset:
                        return offset
            except Exception as e:
                self.helper.log_error(
                    f"[-] Failed to read offset file: {str(e)}"
                )
        return None

    def write_offset(self, offset):
        try:
            with open(self.offset_file, "w") as f:
                f.write(str(offset))
        except Exception as e:
            self.helper.log_error(
                f"[-] Failed to write offset file: {str(e)}"
            )


# ==========================================
# EVENT TRANSFORMATION HELPERS
# ==========================================
def split_headers(header_str):
    """Parse raw header string into dict."""
    headers = {}
    for line in header_str.split('\n'):
        line = line.strip()
        if not line:
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
        else:
            headers[line.strip()] = ""
    return headers


def recursive_decode(obj):
    """Recursively URL-decode all string values in a nested structure."""
    if isinstance(obj, dict):
        return {k: recursive_decode(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [recursive_decode(item) for item in obj]
    elif isinstance(obj, str):
        decoded = unquote(obj)
        decoded = decoded.replace('\r\n', '\n').replace('\r', '\n')
        return decoded
    else:
        return obj


def try_base64_decode(val):
    """Attempt base64-decode; return original value on failure."""
    if not val:
        return ""
    try:
        return base64.b64decode(val + '=' * (-len(val) % 4)).decode('utf-8')
    except Exception:
        return val


def combine_rules_fields(attack_data):
    """
    Combine semicolon-separated base64-encoded rule fields into
    a structured list of rule objects.
    """
    rule_ids       = [try_base64_decode(x) for x in attack_data.get("rules", "").split(";") if x]
    rule_actions   = [try_base64_decode(x) for x in attack_data.get("ruleActions", "").split(";") if x]
    rule_tags      = [try_base64_decode(x) for x in attack_data.get("ruleTags", "").split(";") if x]
    rule_data      = [try_base64_decode(x) for x in attack_data.get("ruleData", "").split(";") if x]
    rule_msgs      = [try_base64_decode(x) for x in attack_data.get("ruleMessages", "").split(";") if x]
    rule_versions  = [try_base64_decode(x) for x in attack_data.get("ruleVersions", "").split(";") if x]
    rule_selectors = [try_base64_decode(x) for x in attack_data.get("ruleSelectors", "").split(";") if x]

    max_len = max(
        len(rule_ids), len(rule_actions), len(rule_tags),
        len(rule_data), len(rule_msgs), len(rule_versions),
        len(rule_selectors), 1
    )

    def get(lst, idx):
        return lst[idx] if idx < len(lst) else ""

    rules_list = []
    for i in range(max_len):
        rules_list.append({
            "action":   get(rule_actions, i),
            "data":     get(rule_data, i),
            "id":       get(rule_ids, i),
            "message":  get(rule_msgs, i),
            "selector": get(rule_selectors, i),
            "tag":      get(rule_tags, i),
            "version":  get(rule_versions, i)
        })
    return rules_list


def decode_attackdata_fields(event):
    """Decode attackData rule fields from base64 to structured objects."""
    attack_data = event.get("attackData", {})
    if "rules" in attack_data:
        attack_data["rules"] = combine_rules_fields(attack_data)
        for key in ["ruleActions", "ruleTags", "ruleData",
                     "ruleMessages", "ruleVersions", "ruleSelectors"]:
            if key in attack_data:
                del attack_data[key]
    event["attackData"] = attack_data
    return event


def transform_headers_in_event(event):
    """Decode URL-encoded fields and parse HTTP headers into dicts."""
    event = recursive_decode(event)
    http_msg = event.get("httpMessage", {})
    for key in ["requestHeaders", "responseHeaders"]:
        if key in http_msg and http_msg[key]:
            http_msg[key] = split_headers(http_msg[key])
    event["httpMessage"] = http_msg
    return event


# ==========================================
# INPUT VALIDATION BEFORE SAVING
# ==========================================
def validate_input(helper, definition):
    """Validate the input stanza configuration before save."""
    config_id = definition.parameters.get('config_id', None)
    if config_id:
        if not re.match(r'^\d+$', str(config_id).strip()):
            raise ValueError(
                "[-] Validation Error: Config ID must be a numeric value."
            )

    limit_num = definition.parameters.get('limit_num', None)
    if limit_num:
        if not re.match(r'^\d+$', str(limit_num).strip()):
            raise ValueError(
                "[-] Validation Error: API Limit must be a numeric value."
            )


# ==========================================
# DATA COLLECTION ROUTINE
# ==========================================
def collect_events(helper, ew):
    """Main data collection logic for Akamai SIEM events."""

    # ── 1. READ INPUT PARAMETERS ─────────────────────────────────────────────
    opt_akamai_account = helper.get_arg('akamai_account')
    opt_config_id      = helper.get_arg('config_id')
    opt_limit_num      = helper.get_arg('limit_num') or "600000"
    opt_proxy_server   = helper.get_arg('proxy_server')
    opt_sourcetype     = helper.get_arg('custom_sourcetype') or "ensign_akamaisiem"

    stanza_name_dict = helper.get_input_stanza()
    stanza_name_raw = list(stanza_name_dict.keys())[0] if stanza_name_dict else opt_config_id
    stanza_name = stanza_name_raw.split("://")[-1] if "://" in stanza_name_raw else stanza_name_raw
    safe_stanza_name = re.sub(r'[<>:"/\\|?*]', '_', stanza_name)

    # ── 2. RESOLVE AKAMAI ACCOUNT CREDENTIALS ────────────────────────────────
    try:
        uri = (
            f"{helper.context_meta.get('server_uri')}/servicesNS/nobody/"
            f"TA-ensign_waf_akamaisiem/"
            f"TA_ensign_waf_akamaisiem_akamai_accounts/"
            f"{urllib.parse.quote(opt_akamai_account)}?output_mode=json&--cred--=1"
        )
        splunk_headers = {
            "Authorization": f"Splunk {helper.context_meta.get('session_key')}"
        }
        response = helper.send_http_request(
            uri, "GET",
            parameters=None, payload=None,
            headers=splunk_headers, cookies=None,
            verify=False, cert=None, timeout=None, use_proxy=False
        )

        if response.status_code != 200:
            helper.log_error(
                f"[-] FATAL: Failed to read Akamai account '{opt_akamai_account}'. "
                f"HTTP Status: {response.status_code}"
            )
            return

        account_data = response.json().get('entry', [])[0].get('content', {})

        # Check if account is enabled
        account_enabled_raw = account_data.get('account_enabled', '1')
        account_enabled = str(account_enabled_raw).lower() in ['1', 'true', 'yes']
        if not account_enabled:
            helper.log_warning(
                f"[!] SKIPPED: Akamai account '{opt_akamai_account}' is DISABLED. "
                f"Enable it in Configuration → Akamai Accounts, or select a different account."
            )
            return

        akamai_host   = account_data.get('akamai_host')
        client_token  = account_data.get('client_token')
        client_secret = account_data.get('client_secret')
        access_token  = account_data.get('access_token')

        # SSL configuration
        disable_ssl_raw = account_data.get('disable_ssl', '0')
        disable_ssl = str(disable_ssl_raw).lower() in ['1', 'true', 'yes']
        cert_location = account_data.get('cert_location', '').strip()

    except Exception as e:
        helper.log_error(
            f"[-] FATAL: Error reading Akamai account '{opt_akamai_account}': {str(e)}"
        )
        return

    # ── 3. RESOLVE PROXY ─────────────────────────────────────────────────────
    # Check if there are enabled proxies available; if so, one must be selected
    proxy_dict = None
    try:
        all_proxies_uri = (
            f"{helper.context_meta.get('server_uri')}/servicesNS/nobody/"
            f"TA-ensign_waf_akamaisiem/"
            f"TA_ensign_waf_akamaisiem_proxy_servers?output_mode=json&count=0"
        )
        all_proxies_resp = helper.send_http_request(
            all_proxies_uri, "GET",
            parameters=None, payload=None,
            headers=splunk_headers, cookies=None,
            verify=False, cert=None, timeout=None, use_proxy=False
        )

        enabled_proxies = []
        if all_proxies_resp.status_code == 200:
            for entry in all_proxies_resp.json().get('entry', []):
                pc = entry.get('content', {})
                pe = str(pc.get('proxy_enabled', '0')).lower() in ['1', 'true', 'yes']
                if pe:
                    enabled_proxies.append(entry.get('name', 'unknown'))

        if enabled_proxies and not opt_proxy_server:
            helper.log_error(
                f"[-] FATAL: There are {len(enabled_proxies)} enabled proxy server(s) "
                f"({', '.join(enabled_proxies)}), but no proxy is selected for this input. "
                f"Please edit this input and select a proxy server."
            )
            return

    except Exception as e:
        helper.log_debug(
            f"[*] Could not enumerate proxy servers: {str(e)}. Continuing."
        )

    if opt_proxy_server:
        try:
            proxy_uri = (
                f"{helper.context_meta.get('server_uri')}/servicesNS/nobody/"
                f"TA-ensign_waf_akamaisiem/"
                f"TA_ensign_waf_akamaisiem_proxy_servers/"
                f"{urllib.parse.quote(opt_proxy_server)}?output_mode=json&--cred--=1"
            )
            proxy_resp = helper.send_http_request(
                proxy_uri, "GET",
                parameters=None, payload=None,
                headers=splunk_headers, cookies=None,
                verify=False, cert=None, timeout=None, use_proxy=False
            )

            if proxy_resp.status_code == 200:
                proxy_data = proxy_resp.json().get('entry', [])[0].get('content', {})
                proxy_enabled = str(proxy_data.get('proxy_enabled', '0')).lower() in ['1', 'true', 'yes']

                if proxy_enabled:
                    proxy_type = proxy_data.get('proxy_type', 'http').lower()
                    proxy_url  = proxy_data.get('proxy_url', '')
                    proxy_port = proxy_data.get('proxy_port', '8080')
                    proxy_user = proxy_data.get('proxy_username', '')
                    proxy_pass = proxy_data.get('proxy_password', '')

                    auth_str = ""
                    if proxy_user and proxy_pass:
                        safe_user = urllib.parse.quote(proxy_user)
                        safe_pass = urllib.parse.quote(proxy_pass)
                        auth_str = f"{safe_user}:{safe_pass}@"

                    proxy_str = f"{proxy_type}://{auth_str}{proxy_url}:{proxy_port}"
                    proxy_dict = {"http": proxy_str, "https": proxy_str}
                    helper.log_info(
                        f"[*] Using proxy '{opt_proxy_server}' -> {proxy_url}:{proxy_port}"
                    )
                else:
                    helper.log_warning(
                        f"[!] Selected proxy '{opt_proxy_server}' is DISABLED. "
                        f"Proceeding without proxy. Please select an enabled proxy."
                    )
            else:
                helper.log_warning(
                    f"[!] Unable to load proxy '{opt_proxy_server}'. "
                    f"HTTP Status: {proxy_resp.status_code}. Proceeding without proxy."
                )
        except Exception as e:
            helper.log_warning(
                f"[!] Error loading proxy '{opt_proxy_server}': {str(e)}. "
                f"Proceeding without proxy."
            )

    # ── 4. INITIALIZE OFFSET STATE ───────────────────────────────────────────
    state = OffsetStateManager(safe_stanza_name, helper)
    offset = state.read_offset()

    helper.log_info(
        f"[*] Stanza '{stanza_name}' | "
        f"Account: {opt_akamai_account} | "
        f"Config ID: {opt_config_id} | "
        f"Offset: {offset or 'null (first run)'}"
    )

    # ── 5. SETUP EDGEGRID SESSION ────────────────────────────────────────────
    session = requests.Session()
    session.auth = EdgeGridAuth(
        client_token=client_token,
        client_secret=client_secret,
        access_token=access_token
    )

    # ── 6. FETCH AKAMAI SIEM EVENTS ─────────────────────────────────────────
    try:
        offset_param = offset if offset else "null"
        url_path = (
            f"/siem/v1/configs/{opt_config_id}"
            f"?offset={offset_param}&limit={opt_limit_num}"
        )
        full_url = f"https://{akamai_host}{url_path}"

        # SSL verification
        verify_param = True
        if disable_ssl:
            verify_param = False
        elif cert_location:
            verify_param = cert_location

        response = session.get(
            full_url,
            proxies=proxy_dict,
            verify=verify_param
        )

        # ── Log detailed error for non-200 responses ────────────────────────
        if response.status_code != 200:
            try:
                error_body = response.text[:500]
            except Exception:
                error_body = "(unable to read response body)"
            helper.log_error(
                f"[-] FATAL: Akamai API returned HTTP {response.status_code} for "
                f"'{stanza_name}' (Config ID: {opt_config_id}). "
                f"URL: {full_url} | "
                f"Response: {error_body}"
            )
            return

        content = response.text

        # Parse response — Akamai can return JSON or NDJSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            lines = content.strip().splitlines()
            data = {"data": [json.loads(line) for line in lines if line.strip()]}

        # ── 7. PROCESS AND WRITE EVENTS ──────────────────────────────────────
        new_offset = None
        if "offset" in data:
            new_offset = data["offset"]

        total_events = 0
        for event_raw in data.get("data", []):
            event_raw = transform_headers_in_event(event_raw)
            event_raw = decode_attackdata_fields(event_raw)

            event = helper.new_event(
                source=f"ensign_akamaisiem://{stanza_name}_{opt_config_id}",
                index=helper.get_output_index(),
                sourcetype=opt_sourcetype,
                data=json.dumps(event_raw, ensure_ascii=False)
            )
            ew.write_event(event)
            total_events += 1

            if "offset" in event_raw:
                new_offset = event_raw["offset"]

        # ── 8. PERSIST OFFSET ────────────────────────────────────────────────
        if new_offset and new_offset != offset:
            state.write_offset(new_offset)

        helper.log_info(
            f"[+] Task '{stanza_name}' completed | "
            f"Ingested: {total_events} events | "
            f"Config ID: {opt_config_id} | "
            f"New offset: {new_offset or 'unchanged'}"
        )

    except requests.exceptions.RequestException as e:
        helper.log_error(
            f"[-] FATAL: Network error fetching Akamai SIEM logs for "
            f"'{stanza_name}': {str(e)}"
        )
    except Exception as e:
        helper.log_error(
            f"[-] FATAL: Data collection error for '{stanza_name}': {str(e)}"
        )
