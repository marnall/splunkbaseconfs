"""REST endpoint for testing Jamf Pro credentials without saving.

Called by the Test Credentials button in the UI. Validates credentials
by hitting the Jamf Pro token endpoint and returns success/failure as JSON.
"""

import import_declare_test  # noqa: F401

import import_declare_test  # noqa: F401

import ipaddress
import os
import socket
import sys
from urllib.parse import urlparse

# Add lib to path for requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import requests

_PRIVATE_NETWORKS = [
    ipaddress.ip_network('0.0.0.0/8'),       # "this network"; resolves to localhost on some stacks
    ipaddress.ip_network('10.0.0.0/8'),      # RFC 1918  # NOSONAR
    ipaddress.ip_network('100.64.0.0/10'),   # CGNAT  # NOSONAR
    ipaddress.ip_network('127.0.0.0/8'),     # loopback
    ipaddress.ip_network('169.254.0.0/16'),  # link-local (incl. cloud metadata 169.254.169.254)  # NOSONAR
    ipaddress.ip_network('172.16.0.0/12'),   # RFC 1918  # NOSONAR
    ipaddress.ip_network('192.168.0.0/16'),  # RFC 1918  # NOSONAR
    ipaddress.ip_network('224.0.0.0/4'),     # multicast  # NOSONAR
    ipaddress.ip_network('240.0.0.0/4'),     # reserved  # NOSONAR
    ipaddress.ip_network('::/128'),          # unspecified
    ipaddress.ip_network('::1/128'),         # loopback
    ipaddress.ip_network('fc00::/7'),        # ULA
    ipaddress.ip_network('fe80::/10'),       # link-local
    ipaddress.ip_network('ff00::/8'),        # multicast
]


def _validate_jss_url(url):
    """Raise ValueError if url is not a safe, public HTTPS destination."""
    parsed = urlparse(url)

    if parsed.scheme != 'https':
        raise ValueError('Only HTTPS URLs are permitted')

    host = parsed.hostname
    if not host:
        raise ValueError('URL must include a hostname')

    # Resolve the hostname and reject any address in a private/reserved range.
    # This runs at validation time; it does not fully prevent DNS rebinding but
    # does block the common cases (localhost, link-local, RFC-1918, metadata).
    try:
        results = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise ValueError('Hostname could not be resolved: {}'.format(host))

    for _family, _type, _proto, _canonname, sockaddr in results:
        addr_str = sockaddr[0]
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            continue
        if any(addr in net for net in _PRIVATE_NETWORKS):
            raise ValueError('URL resolves to a private or reserved address')


import json

import splunk.admin as admin
from splunklib import client, binding
from urllib.parse import urlparse as _urlparse
from solnlib.credentials import CredentialManager, CredentialNotExistException


APP_NAME = "JAMF-Pro-addon-for-splunk"
ACCOUNT_CONF = "jamf_pro_addon_for_splunk_account"
_CREDENTIAL_REALM = "__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, ACCOUNT_CONF)


def _resolve_account_credentials(session_key, account_name):
    """Look up stored credentials for a named account.

    Returns (jss_url, username, password, auth_type) or raises ValueError
    if the account doesn't exist or is missing required fields.
    """
    svc = client.connect(
        token=session_key,
        app=APP_NAME,
        owner="nobody",
        scheme="https",
        host="127.0.0.1",
        port=8089,
        autologin=True,
    )
    try:
        confs = svc.confs[ACCOUNT_CONF]
    except (KeyError, binding.HTTPError):
        raise ValueError("Account conf not found")

    jss_url = username = auth_type = None
    for stanza in confs:
        if stanza.name == account_name:
            c = stanza.content
            jss_url = c.get("jss_url", "")
            username = c.get("username", "")
            auth_type = c.get("auth_type", "api_client")
            break
    if jss_url is None:
        raise ValueError("Account '{}' not found".format(account_name))

    # Retrieve the real secret from the credential store (conf returns ******).
    cm = CredentialManager(session_key=session_key, app=APP_NAME, realm=_CREDENTIAL_REALM)
    try:
        blob = cm.get_password(account_name)
        password = (json.loads(blob) or {}).get("password")
    except (CredentialNotExistException, ValueError, TypeError):
        password = None

    if not jss_url or not username or not password:
        raise ValueError("Account '{}' is missing required fields".format(account_name))
    return jss_url, username, password, auth_type


def _probe_credentials(jss_url, username, password, auth_type):
    """Validate inputs, hit the Jamf token endpoint, return (status, message)."""
    if not jss_url or not username or not password:
        return 'error', 'Missing required fields'

    try:
        _validate_jss_url(jss_url)
    except ValueError as e:
        return 'error', str(e)

    base = jss_url.rstrip('/')
    timeout = 10

    try:
        if auth_type == 'api_client':
            token_url = '{}/api/v1/oauth/token'.format(base)
            resp = requests.post(
                token_url,
                data={
                    'client_id': username,
                    'client_secret': password,
                    'grant_type': 'client_credentials',
                },
                timeout=timeout,
            )
        else:
            token_url = '{}/api/v1/auth/token'.format(base)
            resp = requests.post(
                token_url,
                auth=(username, password),
                timeout=timeout,
            )

        if resp.status_code == 200:
            return 'success', 'Credentials verified'
        if resp.status_code in (400, 401):
            return 'invalid', 'Invalid credentials (HTTP {})'.format(resp.status_code)
        return 'error', 'HTTP {}'.format(resp.status_code)

    except requests.exceptions.Timeout:
        return 'timeout', 'Connection timed out'
    except requests.exceptions.ConnectionError:
        return 'connection_error', 'Could not connect to server'
    except requests.exceptions.RequestException as e:
        return 'error', str(e)[:100]


class TestConnectionHandler(admin.MConfigHandler):
    """REST handler for /jamf_test_connection endpoint.

    Accepts POST so credentials travel in the request body rather than the URL
    (which would otherwise be logged in browser history, web access logs, and
    Splunk's internal telemetry).
    """

    def setup(self):
        if self.requestedAction == admin.ACTION_CREATE:
            # splunk_form_key is splunkweb's CSRF token, forwarded by the __raw
            # proxy. Splunkd's AdminManager rejects POSTs with unknown args, so
            # we have to accept it explicitly even though the handler ignores it.
            for arg in ['jss_url', 'username', 'password', 'auth_type',
                        'account_name', 'splunk_form_key']:
                self.supportedArgs.addOptArg(arg)

    def handleCreate(self, confInfo):
        """Handle POST request with credentials in the request body.

        Two calling modes:
          1. Raw credentials (TestCredentialsButton on Account form):
             POST jss_url, username, password, auth_type
          2. Account name (InputStatusControl on Input edit form):
             POST account_name — credentials are resolved server-side
        """
        account_name = self.callerArgs.data.get('account_name', [None])[0]

        if account_name:
            try:
                jss_url, username, password, auth_type = _resolve_account_credentials(
                    self.getSessionKey(), account_name
                )
            except ValueError as e:
                confInfo['test'].append('status', 'error')
                confInfo['test'].append('message', str(e))
                return
        else:
            jss_url = self.callerArgs.data.get('jss_url', [None])[0]
            username = self.callerArgs.data.get('username', [None])[0]
            password = self.callerArgs.data.get('password', [None])[0]
            auth_type = self.callerArgs.data.get('auth_type', ['api_client'])[0]

        status, message = _probe_credentials(jss_url, username, password, auth_type)
        confInfo['test'].append('status', status)
        confInfo['test'].append('message', message)


if __name__ == '__main__':
    admin.init(TestConnectionHandler, admin.CONTEXT_APP_ONLY)
