"""REST endpoint for testing a Jamf Pro input's `api_call` value.

Called by the Test Endpoint button on the input form. Looks up the account
named on the form, pulls its stored credentials via solnlib, gets a token,
then makes the actual call and reports back. Lets the operator catch a bad
endpoint before saving an input that would otherwise fail silently.

Credentials never travel through the browser — the form only sends the
account name and the candidate api_call value.
"""

import import_declare_test  # noqa: F401

import json
import os
import sys

# Add lib to path for requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import requests

import splunk.admin as admin
from solnlib.credentials import CredentialManager, CredentialNotExistException
from splunklib import binding, client

from jamf_test_connection import _validate_jss_url  # SSRF guard (HTTPS + private-range reject)


APP_NAME = "JAMF-Pro-addon-for-splunk"
ACCOUNT_CONF = "jamf_pro_addon_for_splunk_account"

_PROBE_TIMEOUT = 10


def _load_account(session_key, account_name):
    """Return (jss_url, username, password, auth_type) for an account, or raise ValueError."""
    if not account_name:
        raise ValueError("Account name is required")

    try:
        service = client.connect(
            token=session_key,
            app=APP_NAME,
            owner="nobody",
        )
    except Exception as exc:
        raise ValueError("Could not connect to splunkd: {}".format(exc))

    try:
        stanza = service.confs[ACCOUNT_CONF][account_name]
    except (KeyError, binding.HTTPError):
        raise ValueError("Account {!r} not found".format(account_name))

    jss_url = stanza.content.get("jss_url")
    username = stanza.content.get("username") or ""
    auth_type = stanza.content.get("auth_type") or ""

    # Legacy compat: infer auth_type from "client:" prefix and strip it for the OAuth call.
    if not auth_type:
        auth_type = "api_client" if username.startswith("client:") else "password"
    if username.startswith("client:"):
        username = username[len("client:"):]

    # UCC stores encrypted account fields under a chunked realm:
    #   __REST_CREDENTIAL__#<APP>#configs/conf-<conf>
    # keyed by stanza name, with a JSON blob whose "password" key holds the secret.
    realm = "__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, ACCOUNT_CONF)
    cm = CredentialManager(session_key=session_key, app=APP_NAME, realm=realm)
    try:
        blob = cm.get_password(account_name)
    except CredentialNotExistException:
        raise ValueError("No stored credentials for account {!r}".format(account_name))

    try:
        password = (json.loads(blob) or {}).get("password")
    except (TypeError, ValueError):
        password = None

    if not jss_url or not username or not password:
        raise ValueError("Account {!r} is missing required fields".format(account_name))

    return jss_url, username, password, auth_type


def _get_token(jss_url, username, password, auth_type):
    """Authenticate to Jamf Pro and return a bearer token, or raise ValueError."""
    base = jss_url.rstrip("/")

    if auth_type == "api_client":
        token_url = "{}/api/v1/oauth/token".format(base)
        resp = requests.post(
            token_url,
            data={
                "client_id": username,
                "client_secret": password,
                "grant_type": "client_credentials",
            },
            timeout=_PROBE_TIMEOUT,
        )
    else:
        token_url = "{}/api/v1/auth/token".format(base)
        resp = requests.post(token_url, auth=(username, password), timeout=_PROBE_TIMEOUT)

    if resp.status_code != 200:
        raise ValueError("Auth failed (HTTP {})".format(resp.status_code))

    body = resp.json()
    token = body.get("token") or body.get("access_token")
    if not token:
        raise ValueError("Auth succeeded but no token in response")
    return token


def _build_probe_url(jss_url, api_call, search_name):
    """Map (api_call mode, search_name) -> probe URL. Mirrors input_module_jamf.py:293/464/628.

    Returns (url, error_message). error_message is None on success.
    """
    base = jss_url.rstrip("/") + "/"

    if api_call == "computer":
        if not search_name:
            return None, "Search name is required for Advanced Computer Search"
        return "{}JSSResource/advancedcomputersearches/name/{}".format(base, search_name), None

    if api_call == "mobile_device":
        if not search_name:
            return None, "Search name is required for Advanced Mobile Device Search"
        return "{}JSSResource/advancedmobiledevicesearches/name/{}".format(base, search_name), None

    if api_call == "custom":
        if not search_name:
            return None, "API path is required for Custom mode"
        path = search_name.lstrip("/").rstrip("/")
        return base + path, None

    return None, "Unknown endpoint type {!r} (expected computer, mobile_device, or custom)".format(api_call)


def _probe_endpoint(jss_url, token, api_call, search_name):
    """Build URL from (api_call, search_name), GET with bearer token. Returns (status, http_code, message)."""
    url, err = _build_probe_url(jss_url, api_call, search_name)
    if err is not None:
        return "error", None, err

    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}

    try:
        resp = requests.get(url, headers=headers, timeout=_PROBE_TIMEOUT)
    except requests.exceptions.Timeout:
        return "timeout", None, "Connection timed out"
    except requests.exceptions.ConnectionError:
        return "connection_error", None, "Could not reach Jamf Pro"
    except requests.exceptions.RequestException as exc:
        return "error", None, str(exc)[:200]

    code = resp.status_code
    if code == 200:
        return "success", code, "Endpoint reachable (HTTP 200)"
    if code == 404:
        if api_call in ("computer", "mobile_device"):
            return "not_found", code, "Saved search {!r} not found (HTTP 404).".format(search_name)
        return "not_found", code, "Endpoint not found (HTTP 404). Check the path."
    if code in (401, 403):
        return "forbidden", code, "Authenticated, but endpoint denied (HTTP {}). The account may lack required privileges.".format(code)
    return "error", code, "Unexpected response (HTTP {})".format(code)


def _probe_input(session_key, account_name, api_call, search_name):
    """Validate inputs, look up account, get token, probe endpoint, return (status, http_code, message)."""
    try:
        jss_url, username, password, auth_type = _load_account(session_key, account_name)
    except ValueError as exc:
        return "error", None, str(exc)

    try:
        _validate_jss_url(jss_url)
    except ValueError as exc:
        return "error", None, "Account URL rejected: {}".format(exc)

    try:
        token = _get_token(jss_url, username, password, auth_type)
    except ValueError as exc:
        return "auth_failed", None, str(exc)
    except requests.exceptions.Timeout:
        return "timeout", None, "Auth request timed out"
    except requests.exceptions.ConnectionError:
        return "connection_error", None, "Could not reach Jamf Pro for auth"
    except requests.exceptions.RequestException as exc:
        return "error", None, "Auth error: {}".format(str(exc)[:200])

    return _probe_endpoint(jss_url, token, api_call, search_name)


class TestInputHandler(admin.MConfigHandler):
    """REST handler for /jamf_test_input.

    POST {account_name, api_call, search_name} → JSON {status, http_code, message}
    """

    def setup(self):
        if self.requestedAction == admin.ACTION_CREATE:
            # splunk_form_key is splunkweb's CSRF token, forwarded by the __raw
            # proxy. Splunkd's AdminManager rejects POSTs with unknown args, so
            # we have to accept it explicitly even though the handler ignores it.
            for arg in ["account_name", "api_call", "search_name", "splunk_form_key"]:
                self.supportedArgs.addOptArg(arg)

    def handleCreate(self, confInfo):
        account_name = self.callerArgs.data.get("account_name", [None])[0]
        api_call = self.callerArgs.data.get("api_call", [None])[0]
        search_name = self.callerArgs.data.get("search_name", [None])[0]

        status, http_code, message = _probe_input(
            self.getSessionKey(), account_name, api_call, search_name
        )

        confInfo["test"].append("status", status)
        confInfo["test"].append("message", message)
        if http_code is not None:
            confInfo["test"].append("http_code", str(http_code))


if __name__ == "__main__":
    admin.init(TestInputHandler, admin.CONTEXT_APP_ONLY)
