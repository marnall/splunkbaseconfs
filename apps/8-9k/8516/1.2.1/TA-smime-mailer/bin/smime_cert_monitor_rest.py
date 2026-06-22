"""
REST handler for S/MIME certificate monitoring.
Returns certificate status for all sender and recipient certificates.

Query with:
    | rest /servicesNS/nobody/TA-smime-mailer/smime_cert_monitor splunk_server=local

Returns a table with columns:
    email, cert_type, cert_name, not_after, days_to_expiration, status,
    issuer, fingerprint_sha256, serial, not_before, enabled
"""

import os
import sys
import json
import base64
import datetime
import urllib.request
import urllib.parse
import urllib.error
import ssl

# Add the lib folder so we can import our helpers
lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication


class SmimeCertMonitorHandler(PersistentServerConnectionApplication):
    """
    EAI REST handler that reports certificate inventory and expiration status.

    Reads stanzas from smime_recipient_certs.conf and smime_sender_certs.conf,
    calculates days-to-expiration, and returns a unified table.

    Each row is keyed as  ``<type>__<email>``  (e.g. ``recipient__bob@example.com``).
    """

    APP_NAME = 'TA-smime-mailer'

    # Threshold (in days) below which a certificate is flagged as "expiring_soon"
    EXPIRY_WARNING_DAYS = 30

    def __init__(self, command_line, command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        """Handle GET requests and return a Splunk REST-style entry list."""
        try:
            request = json.loads(in_string)
            method = request.get('method', 'GET')
            if method != 'GET':
                return self._error(405, f'Method {method} not allowed')

            session_key = request['session']['authtoken']
            entries = self._collect_entries(session_key)
            return self._success({'entry': entries})
        except Exception as e:
            return self._error(500, f'Internal error: {str(e)}')

    def _collect_entries(self, session_key):
        """Build and return all sender+recipient certificate rows."""
        entries = []
        now = datetime.datetime.now(datetime.timezone.utc)

        self._load_certs(
            conf_name='smime_recipient_certs',
            cert_type='recipient',
            session_key=session_key,
            entries=entries,
            now=now,
        )

        self._load_certs(
            conf_name='smime_sender_certs',
            cert_type='sender',
            session_key=session_key,
            entries=entries,
            now=now,
        )

        # If HF proxy is enabled, add a row for the bearer token expiration
        self._load_hf_token(session_key, entries, now)

        # If OAuth2 / Graph API is configured, check Azure app secret expiry
        self._load_graph_secret_expiry(session_key, entries, now)

        entries.sort(key=lambda e: e.get('name', ''))
        return entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_certs(self, conf_name, cert_type, session_key, entries, now):
        """Read all stanzas from *conf_name* and append rows to *entries*."""
        try:
            uri = (
                f'/servicesNS/nobody/{self.APP_NAME}/configs/conf-{conf_name}'
                f'?output_mode=json&count=0'
            )
            response, content = rest.simpleRequest(
                uri, sessionKey=session_key, method='GET',
            )
            data = json.loads(content)
        except Exception:
            # If the conf file doesn't exist yet or is empty, skip silently
            return

        # Try to import CRL checking (best-effort)
        crl_check_fn = None
        try:
            from smime_cert_utils import check_crl_revocation_cached
            crl_check_fn = check_crl_revocation_cached
        except ImportError:
            pass

        crl_cache = {}

        for entry in data.get('entry', []):
            stanza_name = entry['name']
            if stanza_name in ('default',):
                continue

            c = entry.get('content', {})
            email = stanza_name
            cn = c.get('cn', '') or ''
            not_after_str = c.get('not_after', '') or ''
            not_before_str = c.get('not_before', '') or ''
            issuer = c.get('issuer', '') or ''
            fingerprint = c.get('fingerprint_sha256', '') or ''
            serial = c.get('serial', '') or ''
            enabled = c.get('enabled', '1') or '1'
            notify_on_expiry = c.get('notify_on_expiry', '0') or '0'
            cert_pem_raw = c.get('cert_pem', '') or ''

            # --- Calculate days to expiration & human-readable status ----
            days_to_exp = ''
            status = 'unknown'
            if not_after_str:
                try:
                    not_after_dt = datetime.datetime.fromisoformat(
                        not_after_str.replace('Z', '+00:00')
                    )
                    delta = not_after_dt - now
                    days_int = int(delta.total_seconds() / 86400)
                    days_to_exp = str(days_int)
                    if delta.total_seconds() <= 0:
                        status = 'expired'
                    elif days_int <= self.EXPIRY_WARNING_DAYS:
                        status = 'expiring_soon'
                    else:
                        status = 'valid'
                except Exception:
                    pass

            # --- CRL revocation check ------------------------------------
            crl_checked = False
            crl_revoked = False
            crl_reason = ''
            crl_revocation_date = ''
            crl_error = ''
            crl_url = ''
            if crl_check_fn and cert_pem_raw:
                try:
                    cert_pem_real = cert_pem_raw.replace('\\n', '\n')
                    crl_res = crl_check_fn(cert_pem_real, cache=crl_cache, timeout=8)
                    crl_checked = crl_res.get('checked', False)
                    crl_revoked = crl_res.get('revoked', False)
                    crl_reason = crl_res.get('reason', '')
                    crl_revocation_date = crl_res.get('revocation_date', '')
                    crl_error = crl_res.get('error', '')
                    crl_url = crl_res.get('crl_url', '')
                    # Override status if certificate is revoked
                    if crl_revoked:
                        status = 'revoked'
                except Exception:
                    pass

            # Use a unique key per entry:  <cert_type>__<email>
            key = f'{cert_type}__{email}'
            entries.append({
                'name': key,
                'content': {
                    'email': email,
                    'cert_type': cert_type,
                    'cert_name': cn,
                    'not_after': not_after_str,
                    'not_before': not_before_str,
                    'days_to_expiration': days_to_exp,
                    'status': status,
                    'issuer': issuer,
                    'fingerprint_sha256': fingerprint,
                    'serial': serial,
                    'enabled': enabled,
                    'notify_on_expiry': notify_on_expiry,
                    'crl_checked': str(crl_checked).lower(),
                    'crl_revoked': str(crl_revoked).lower(),
                    'crl_reason': crl_reason,
                    'crl_revocation_date': crl_revocation_date,
                    'crl_error': crl_error,
                    'crl_url': crl_url,
                }
            })

    def _load_hf_token(self, session_key, entries, now):
        """If HF proxy is enabled, decode the stored bearer token (JWT) and
        add a row reporting its expiration date."""
        try:
            # Check if HF proxy is enabled
            uri = (
                f'/servicesNS/nobody/{self.APP_NAME}/configs/conf-smime_mailer_settings'
                f'/smtp?output_mode=json'
            )
            response, content = rest.simpleRequest(
                uri, sessionKey=session_key, method='GET',
            )
            data = json.loads(content)
            settings = data.get('entry', [{}])[0].get('content', {})
            use_hf = (settings.get('use_hf_proxy', 'false') or 'false').lower() in ('true', '1', 'yes')
            if not use_hf:
                return

            hf_host = settings.get('hf_host', '') or ''
        except Exception:
            return

        # Retrieve the token from credential store
        try:
            uri_pw = (
                f'/servicesNS/nobody/{self.APP_NAME}/storage/passwords'
                f'?output_mode=json&count=0&search=smime_hf_token'
            )
            response, content = rest.simpleRequest(
                uri_pw, sessionKey=session_key, method='GET',
            )
            pw_data = json.loads(content)
            token = ''
            for e in pw_data.get('entry', []):
                if 'smime_hf_token' in e.get('name', ''):
                    token = e.get('content', {}).get('clear_password', '')
                    break
            if not token:
                return
        except Exception:
            return

        # Decode the JWT payload to read 'exp' and 'iat' claims
        not_after_str = ''
        not_before_str = ''
        days_to_exp = ''
        status = 'unknown'
        issuer_info = ''
        subject = ''
        try:
            parts = token.split('.')
            if len(parts) >= 2:
                payload_b64 = parts[1]
                # Fix base64 padding
                payload_b64 += '=' * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64).decode('utf-8'))

                exp_ts = payload.get('exp')
                iat_ts = payload.get('iat') or payload.get('nbf')
                issuer_info = payload.get('iss', '')
                subject = payload.get('sub', '')

                if exp_ts:
                    exp_dt = datetime.datetime.fromtimestamp(int(exp_ts), tz=datetime.timezone.utc)
                    not_after_str = exp_dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                    delta = exp_dt - now
                    days_int = int(delta.total_seconds() / 86400)
                    days_to_exp = str(days_int)
                    if delta.total_seconds() <= 0:
                        status = 'expired'
                    elif days_int <= self.EXPIRY_WARNING_DAYS:
                        status = 'expiring_soon'
                    else:
                        status = 'valid'

                if iat_ts:
                    iat_dt = datetime.datetime.fromtimestamp(int(iat_ts), tz=datetime.timezone.utc)
                    not_before_str = iat_dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
        except Exception:
            pass

        label = f'HF proxy token ({hf_host})' if hf_host else 'HF proxy token'
        entries.append({
            'name': 'token__hf_proxy',
            'content': {
                'email': subject or hf_host or 'hf_proxy',
                'cert_type': 'token',
                'cert_name': label,
                'not_after': not_after_str,
                'not_before': not_before_str,
                'days_to_expiration': days_to_exp,
                'status': status,
                'issuer': issuer_info,
                'fingerprint_sha256': '',
                'serial': '',
                'enabled': '1',
            }
        })

    def _load_graph_secret_expiry(self, session_key, entries, now):
        """If OAuth2 / Graph API is configured, query Microsoft Graph for
        the Azure AD application's ``passwordCredentials`` and report each
        client-secret's expiration date.

        When the HF proxy is enabled the query is routed through the HF so
        that internet-restricted Search Heads can still obtain this data.

        Any failure is non-fatal — an error row is appended so the admin
        knows the check could not be completed, but certificate rows are
        unaffected.
        """
        try:
            uri = (
                f'/servicesNS/nobody/{self.APP_NAME}/configs/conf-smime_mailer_settings'
                f'/smtp?output_mode=json'
            )
            response, content = rest.simpleRequest(
                uri, sessionKey=session_key, method='GET',
            )
            data = json.loads(content)
            settings = data.get('entry', [{}])[0].get('content', {})
        except Exception:
            return

        auth_type = (settings.get('smtp_auth_type', '') or '').strip().lower()
        client_id = (settings.get('oauth2_client_id', '') or '').strip()
        tenant_id = (settings.get('oauth2_tenant_id', '') or '').strip()

        if auth_type != 'oauth2' or not client_id:
            return  # OAuth2 / Graph API not configured

        # Retrieve client secret from credential store
        client_secret = ''
        try:
            pw_uri = (
                f'/servicesNS/nobody/{self.APP_NAME}/storage/passwords'
                f'/{self.APP_NAME}:smime_oauth2_client_secret:?output_mode=json'
            )
            resp, pw_content = rest.simpleRequest(
                pw_uri, sessionKey=session_key, method='GET',
            )
            pw_data = json.loads(pw_content)
            client_secret = pw_data['entry'][0]['content']['clear_password']
        except Exception:
            pass

        if not client_secret:
            return  # Cannot check without the secret

        token_url = (settings.get('oauth2_token_url', '') or '').strip()
        scope = (settings.get('oauth2_scope', '') or 'https://graph.microsoft.com/.default').strip()

        use_hf = (settings.get('use_hf_proxy', 'false') or 'false').lower() in ('true', '1', 'yes')

        if use_hf:
            self._check_graph_secrets_via_hf(
                settings, client_id, client_secret, tenant_id,
                token_url, scope, session_key, entries, now,
            )
        else:
            self._check_graph_secrets_direct(
                client_id, client_secret, tenant_id,
                token_url, scope, entries, now,
            )

    # -- Direct call (SH has internet access) --
    def _check_graph_secrets_direct(self, client_id, client_secret, tenant_id,
                                     token_url, scope, entries, now):
        try:
            creds = self._query_graph_password_credentials(
                client_id, client_secret, tenant_id, token_url, scope,
            )
            self._append_secret_entries(creds, client_id, entries, now)
        except Exception as e:
            self._append_secret_error(str(e), client_id, entries)

    # -- Via HF proxy --
    def _check_graph_secrets_via_hf(self, settings, client_id, client_secret,
                                     tenant_id, token_url, scope,
                                     session_key, entries, now):
        hf_host = (settings.get('hf_host', '') or '').strip()
        hf_port = (settings.get('hf_port', '8089') or '8089').strip()

        # Retrieve HF token
        hf_token = ''
        try:
            pw_uri = (
                f'/servicesNS/nobody/{self.APP_NAME}/storage/passwords'
                f'?output_mode=json&count=0&search=smime_hf_token'
            )
            resp, pw_content = rest.simpleRequest(
                pw_uri, sessionKey=session_key, method='GET',
            )
            pw_data = json.loads(pw_content)
            for e in pw_data.get('entry', []):
                if 'smime_hf_token' in e.get('name', ''):
                    hf_token = e.get('content', {}).get('clear_password', '')
                    break
        except Exception:
            pass

        if not hf_host or not hf_token:
            self._append_secret_error(
                'HF proxy enabled but host/token not configured — '
                'cannot check Azure app secret expiry',
                client_id, entries,
            )
            return

        payload = json.dumps({
            'action': 'check_secrets',
            'oauth2_client_id': client_id,
            'oauth2_client_secret': client_secret,
            'oauth2_tenant_id': tenant_id,
            'oauth2_token_url': token_url,
            'oauth2_scope': scope,
        }).encode('utf-8')

        url = f'https://{hf_host}:{hf_port}/services/smime_proxy/send?output_mode=json'
        try:
            req = urllib.request.Request(url, data=payload, method='POST')
            req.add_header('Authorization', f'Bearer {hf_token}')
            req.add_header('Content-Type', 'application/json')
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))

            creds = resp_data.get('password_credentials', [])
            self._append_secret_entries(creds, client_id, entries, now)
        except urllib.error.HTTPError as e:
            body = ''
            try:
                body = e.read().decode('utf-8', errors='replace')
                detail = json.loads(body).get('message', body)
            except Exception:
                detail = body or str(e)
            self._append_secret_error(
                f'HF proxy returned HTTP {e.code}: {detail}', client_id, entries,
            )
        except Exception as e:
            self._append_secret_error(
                f'HF proxy request failed: {e}', client_id, entries,
            )

    # -- Shared: query Graph API for passwordCredentials --
    def _query_graph_password_credentials(self, client_id, client_secret,
                                           tenant_id, token_url, scope):
        """Acquire an OAuth2 token and query Graph /applications for
        ``passwordCredentials``.  Returns a list of dicts with keys
        ``displayName``, ``endDateTime``, ``startDateTime``, ``keyId``."""
        if not token_url:
            if tenant_id:
                token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
            else:
                raise ValueError('oauth2_token_url or oauth2_tenant_id is required')
        elif '{tenant}' in token_url and tenant_id:
            token_url = token_url.replace('{tenant}', tenant_id)

        # 1. Obtain access token
        tok_data = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': scope,
        }).encode('utf-8')
        tok_req = urllib.request.Request(token_url, data=tok_data, method='POST')
        tok_req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        with urllib.request.urlopen(tok_req, timeout=15) as resp:
            tok_resp = json.loads(resp.read().decode('utf-8'))
        access_token = tok_resp.get('access_token')
        if not access_token:
            raise RuntimeError('No access_token in OAuth2 response')

        # 2. Query application's passwordCredentials
        graph_url = (
            f'https://graph.microsoft.com/v1.0/applications'
            f'?$filter=appId%20eq%20%27{client_id}%27'
            f'&$select=displayName,passwordCredentials'
        )
        g_req = urllib.request.Request(graph_url, method='GET')
        g_req.add_header('Authorization', f'Bearer {access_token}')
        with urllib.request.urlopen(g_req, timeout=15) as resp:
            g_data = json.loads(resp.read().decode('utf-8'))

        apps = g_data.get('value', [])
        if not apps:
            raise RuntimeError(
                f'Application with appId={client_id} not found. '
                f'The Application.Read.All permission may be missing.'
            )
        return apps[0].get('passwordCredentials', [])

    # -- Shared: turn passwordCredentials into monitor entries --
    def _append_secret_entries(self, creds, client_id, entries, now):
        if not creds:
            entries.append({
                'name': f'secret__{client_id}',
                'content': {
                    'email': client_id,
                    'cert_type': 'azure_secret',
                    'cert_name': 'No secrets found for Azure app',
                    'not_after': '',
                    'not_before': '',
                    'days_to_expiration': '',
                    'status': 'unknown',
                    'issuer': 'Microsoft Entra ID',
                    'fingerprint_sha256': '',
                    'serial': '',
                    'enabled': '1',
                }
            })
            return

        for idx, cred in enumerate(creds):
            display = cred.get('displayName', '') or f'Secret #{idx + 1}'
            key_id = cred.get('keyId', '') or ''
            end_str = cred.get('endDateTime', '') or ''
            start_str = cred.get('startDateTime', '') or ''

            not_after_str = ''
            not_before_str = ''
            days_to_exp = ''
            status = 'unknown'

            if end_str:
                try:
                    end_dt = datetime.datetime.fromisoformat(
                        end_str.replace('Z', '+00:00')
                    )
                    not_after_str = end_dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                    delta = end_dt - now
                    days_int = int(delta.total_seconds() / 86400)
                    days_to_exp = str(days_int)
                    if days_int < 0:
                        status = 'expired'
                    elif days_int <= self.EXPIRY_WARNING_DAYS:
                        status = 'expiring_soon'
                    else:
                        status = 'valid'
                except Exception:
                    pass

            if start_str:
                try:
                    start_dt = datetime.datetime.fromisoformat(
                        start_str.replace('Z', '+00:00')
                    )
                    not_before_str = start_dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                except Exception:
                    pass

            short_id = key_id[:8] if key_id else str(idx)
            entries.append({
                'name': f'secret__{client_id}__{short_id}',
                'content': {
                    'email': client_id,
                    'cert_type': 'azure_secret',
                    'cert_name': f'Azure app secret: {display}',
                    'not_after': not_after_str,
                    'not_before': not_before_str,
                    'days_to_expiration': days_to_exp,
                    'status': status,
                    'issuer': 'Microsoft Entra ID',
                    'fingerprint_sha256': '',
                    'serial': key_id,
                    'enabled': '1',
                }
            })

    def _append_secret_error(self, message, client_id, entries):
        """Add an error row so the admin knows the Azure secret check failed."""
        entries.append({
            'name': f'secret__{client_id}__error',
            'content': {
                'email': client_id,
                'cert_type': 'azure_secret',
                'cert_name': f'Azure app secret check failed: {message}',
                'not_after': '',
                'not_before': '',
                'days_to_expiration': '',
                'status': 'check_error',
                'issuer': 'Microsoft Entra ID',
                'fingerprint_sha256': '',
                'serial': '',
                'enabled': '1',
            }
        })

    @staticmethod
    def _success(data):
        return {
            'status': 200,
            'headers': {'Content-Type': 'application/json'},
            'payload': json.dumps(data),
        }

    @staticmethod
    def _error(status, message):
        return {
            'status': status,
            'headers': {'Content-Type': 'application/json'},
            'payload': json.dumps({'status': 'error', 'message': message}),
        }
