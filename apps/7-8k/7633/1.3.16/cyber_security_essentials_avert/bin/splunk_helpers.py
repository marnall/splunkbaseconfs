"""
Shared helper utilities for Splunk Cloud and on-premise compatibility.

Provides session key retrieval and REST API calls that work across both
Splunk Cloud Platform and Splunk Enterprise (on-premise).
"""
import os
import sys
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

APP_NAME = 'cyber_security_essentials_avert'
SPLUNK_HOME = os.environ.get('SPLUNK_HOME', '')
SPLUNK_BASE = 'https://localhost:8089'


def get_session_key():
    """
    Retrieve the Splunk session key using multiple strategies.
    Works on both Splunk Cloud and Splunk Enterprise (on-premise).

    Priority:
      1. SPLUNK_SESSION_KEY environment variable (set by some invocation contexts)
      2. splunk.Intersplunk module (Splunk's built-in Python, available on both platforms)
      3. stdin payload 'session_key' field (alert actions pass it in the JSON payload)
    """
    # Strategy 1: Environment variable
    session_key = os.environ.get('SPLUNK_SESSION_KEY', '')
    if session_key:
        return session_key

    # Strategy 2: Splunk's built-in Intersplunk module
    # Available in both Cloud and on-premise as part of Splunk's Python environment
    try:
        import splunk.Intersplunk as si
        results, dummyresults, settings = si.getOrganizedResults()
        session_key = settings.get('sessionKey', '')
        if session_key:
            return session_key
    except Exception:
        pass

    # Strategy 3: Read from Splunk's auth token (stored by splunkd)
    try:
        token_path = os.path.join(SPLUNK_HOME, 'var', 'run', 'splunk', 'dispatch')
        if not os.path.exists(token_path):
            # Alternative: try reading from the search info passed in environment
            for env_key in ('SPLUNKD_SESSION_KEY', 'session_key', 'sessionKey'):
                val = os.environ.get(env_key, '')
                if val:
                    return val
    except Exception:
        pass

    return ''


def get_session_key_from_payload(payload):
    """Extract session key from an alert action payload dict."""
    return payload.get('session_key', '')


def splunk_rest(method, endpoint, session_key, data=None):
    """
    Make a REST call to the local Splunk instance.
    Works on both Cloud and on-premise (splunkd always listens on localhost:8089).
    """
    url = f'{SPLUNK_BASE}{endpoint}'
    headers = {'Authorization': f'Splunk {session_key}'}
    params = {'output_mode': 'json'}
    if data:
        params.update(data)
    if method == 'GET':
        resp = requests.get(url, headers=headers, params=params, verify=False, timeout=30)
    else:
        resp = requests.post(url, headers=headers, data=params, verify=False, timeout=30)
    resp.raise_for_status()
    return resp.json()


def read_conf(session_key, conf_name, stanza):
    """Read a stanza from a .conf file via Splunk REST API."""
    endpoint = f'/servicesNS/-/{APP_NAME}/configs/conf-{conf_name}/{stanza}'
    result = splunk_rest('GET', endpoint, session_key)
    entries = result.get('entry', [])
    if entries:
        return entries[0].get('content', {})
    return {}


def write_conf(session_key, conf_name, stanza, key_values):
    """Write key-value pairs to a .conf stanza via Splunk REST API."""
    endpoint = f'/servicesNS/-/{APP_NAME}/configs/conf-{conf_name}/{stanza}'
    splunk_rest('POST', endpoint, session_key, data=key_values)
