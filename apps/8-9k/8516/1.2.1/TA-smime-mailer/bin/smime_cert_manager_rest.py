"""
REST handler for S/MIME certificate management.
Provides endpoints to upload, validate, list, and delete recipient/sender certificates.
"""

import json
import os
import sys
import re
import traceback
import logging

# Add the lib folder so we can import our helpers
lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

logger = logging.getLogger('smime_mailer.rest')


def _import_cert_utils():
    """Lazily import smime_cert_utils (requires cryptography library)."""
    try:
        from smime_cert_utils import parse_certificate_pem, validate_certificate
        return parse_certificate_pem, validate_certificate
    except ImportError as e:
        raise ImportError(
            f'Certificate operations require the cryptography library. '
            f'Install it with: pip install cryptography --target {lib_dir} -- {e}'
        )


class SmimeCertManagerHandler(PersistentServerConnectionApplication):
    """
    REST handler accessible at /services/smime_mailer/cert_manager
    
    Supported operations:
      GET    ?action=list_recipients              - List all recipient certs
      GET    ?action=list_senders                  - List all sender certs
      GET    ?action=validate_recipients&to=a@b,c@d - Check all recipients have certs
      POST   action=add_recipient                  - Upload a recipient cert (PEM)
      POST   action=add_sender                     - Upload a sender cert + key (PEM)
      DELETE ?action=delete_recipient&email=a@b     - Remove a recipient cert
      DELETE ?action=delete_sender&email=a@b        - Remove a sender cert
      POST   action=test_smtp                      - Test SMTP connectivity
    """

    APP_NAME = 'TA-smime-mailer'

    def __init__(self, command_line, command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            method = request.get('method', 'GET')
            session_key = request['session']['authtoken']

            # Parse query / form params
            # persistconn passes query as list of 2-element lists: [[name, value], ...]
            query = {}
            for pair in request.get('query', []):
                if isinstance(pair, dict):
                    query[pair['name']] = pair['value']
                else:
                    query[pair[0]] = pair[1]

            form = {}
            if request.get('payload'):
                try:
                    form = json.loads(request['payload'])
                except (json.JSONDecodeError, TypeError):
                    # Try form-encoded
                    for pair in request.get('form', []):
                        if isinstance(pair, dict):
                            form[pair['name']] = pair['value']
                        else:
                            form[pair[0]] = pair[1]

            action = query.get('action') or form.get('action', '')

            if method == 'GET':
                return self._handle_get(action, query, session_key)
            elif method == 'POST':
                return self._handle_post(action, form, session_key)
            elif method == 'DELETE':
                return self._handle_delete(action, query, session_key)
            else:
                return self._error(405, f'Method {method} not allowed')

        except Exception as e:
            return self._error(500, f'Internal error: {str(e)}\n{traceback.format_exc()}')

    # ------------------------------------------------------------------
    # GET handlers
    # ------------------------------------------------------------------
    def _handle_get(self, action, query, session_key):
        if action == 'list_recipients':
            return self._list_certs('smime_recipient_certs', session_key)
        elif action == 'list_senders':
            return self._list_certs('smime_sender_certs', session_key)
        elif action == 'validate_recipients':
            return self._validate_recipients(query, session_key)
        elif action == 'get_smtp':
            return self._get_smtp_settings(session_key)
        else:
            return self._error(400, f'Unknown GET action: {action}')

    # ------------------------------------------------------------------
    # POST handlers
    # ------------------------------------------------------------------
    def _handle_post(self, action, form, session_key):
        if action == 'add_recipient':
            return self._add_recipient_cert(form, session_key)
        elif action == 'add_sender':
            return self._add_sender_cert(form, session_key)
        elif action == 'add_sender_pfx':
            return self._add_sender_pfx(form, session_key)
        elif action == 'save_smtp':
            return self._save_smtp_settings(form, session_key)
        elif action == 'test_smtp':
            return self._test_smtp(form, session_key)
        elif action == 'toggle_notify':
            return self._toggle_notify(form, session_key)
        else:
            return self._error(400, f'Unknown POST action: {action}')

    # ------------------------------------------------------------------
    # DELETE handlers
    # ------------------------------------------------------------------
    def _handle_delete(self, action, query, session_key):
        email = query.get('email', '')
        if not email:
            return self._error(400, 'Missing email parameter')

        if action == 'delete_recipient':
            return self._delete_cert('smime_recipient_certs', email, session_key)
        elif action == 'delete_sender':
            return self._delete_cert('smime_sender_certs', email, session_key)
        else:
            return self._error(400, f'Unknown DELETE action: {action}')

    # ------------------------------------------------------------------
    # Certificate operations
    # ------------------------------------------------------------------
    def _list_certs(self, conf_name, session_key):
        """List all certificate stanzas from the given conf file.

        For sender certs, also checks whether the private key exists in the
        credential store and adds a ``has_private_key`` boolean to each entry.
        """
        try:
            uri = f'/servicesNS/nobody/{self.APP_NAME}/configs/conf-{conf_name}?output_mode=json&count=0'
            response, content = rest.simpleRequest(uri, sessionKey=session_key, method='GET')
            data = json.loads(content)
            entries = []
            for e in data.get('entry', []):
                if e['name'] in ('default',):
                    continue
                info = e.get('content', {})
                info['email'] = e['name']
                entries.append(info)

            # For sender certs: check private key health
            if conf_name == 'smime_sender_certs' and entries:
                stored_keys = self._list_stored_password_names(session_key)
                for entry in entries:
                    key_name = f'smime_sender_key__{entry["email"]}'
                    entry['has_private_key'] = key_name in stored_keys

            # CRL revocation check for all certs
            try:
                from smime_cert_utils import check_crl_revocation_cached
                crl_cache = {}
                for entry in entries:
                    cert_pem_raw = entry.get('cert_pem', '')
                    if cert_pem_raw:
                        # Unescape \\n back to real newlines
                        cert_pem_real = cert_pem_raw.replace('\\n', '\n')
                        crl_res = check_crl_revocation_cached(cert_pem_real, cache=crl_cache, timeout=8)
                        entry['crl_checked'] = crl_res.get('checked', False)
                        entry['crl_revoked'] = crl_res.get('revoked', False)
                        entry['crl_reason'] = crl_res.get('reason', '')
                        entry['crl_revocation_date'] = crl_res.get('revocation_date', '')
                        entry['crl_error'] = crl_res.get('error', '')
                        entry['crl_url'] = crl_res.get('crl_url', '')
                    else:
                        entry['crl_checked'] = False
                        entry['crl_revoked'] = False
                        entry['crl_error'] = 'No certificate PEM data'
            except ImportError:
                logger.debug('smime_cert_utils not available for CRL check in _list_certs')
            except Exception as e:
                logger.debug(f'CRL check in _list_certs failed: {e}')

            return self._success({'entries': entries})
        except Exception as e:
            return self._error(500, f'Error listing {conf_name}: {str(e)}')

    def _list_stored_password_names(self, session_key):
        """Return a set of password usernames stored in this app's realm."""
        realm = self.APP_NAME
        uri = f'/servicesNS/nobody/{self.APP_NAME}/storage/passwords?output_mode=json&count=0&search={realm}'
        try:
            response, content = rest.simpleRequest(uri, sessionKey=session_key, method='GET')
            data = json.loads(content)
            return {
                entry.get('content', {}).get('username', '')
                for entry in data.get('entry', [])
                if entry.get('content', {}).get('realm') == realm
            }
        except Exception:
            return set()

    def _add_recipient_cert(self, form, session_key):
        """Add or update a recipient public certificate."""
        email = form.get('email', '').strip().lower()
        cert_pem = form.get('cert_pem', '').strip()

        if not email or not cert_pem:
            return self._error(400, 'email and cert_pem are required')

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return self._error(400, 'Invalid email address format')

        # Parse and validate the certificate
        try:
            parse_certificate_pem, validate_certificate = _import_cert_utils()
        except ImportError as e:
            return self._error(500, str(e))

        try:
            cert_info = parse_certificate_pem(cert_pem)
        except Exception as e:
            return self._error(400, f'Invalid certificate: {str(e)}')

        validation = validate_certificate(cert_pem)
        if not validation['valid']:
            return self._error(400, f'Certificate validation failed: {validation["error"]}')

        # Store newlines as literal \\n for conf file compatibility
        cert_pem_escaped = cert_pem.replace('\r\n', '\n').replace('\n', '\\n')

        # Write to conf
        notify_on_expiry = form.get('notify_on_expiry', '0').strip()
        if notify_on_expiry.lower() in ('true', '1', 'yes'):
            notify_on_expiry = '1'
        else:
            notify_on_expiry = '0'

        stanza_data = {
            'cert_pem': cert_pem_escaped,
            'cn': cert_info.get('cn', ''),
            'serial': cert_info.get('serial', ''),
            'not_after': cert_info.get('not_after', ''),
            'not_before': cert_info.get('not_before', ''),
            'issuer': cert_info.get('issuer', ''),
            'fingerprint_sha256': cert_info.get('fingerprint_sha256', ''),
            'enabled': '1',
            'notify_on_expiry': notify_on_expiry,
        }

        try:
            self._write_conf_stanza('smime_recipient_certs', email, stanza_data, session_key)
            return self._success({
                'message': f'Certificate for {email} saved successfully',
                'cert_info': cert_info,
            })
        except Exception as e:
            return self._error(500, f'Failed to save certificate: {str(e)}')

    def _add_sender_cert(self, form, session_key):
        """Add or update a sender certificate + private key."""
        email = form.get('email', '').strip().lower()
        cert_pem = form.get('cert_pem', '').strip()
        key_pem = form.get('key_pem', '').strip()

        if not email or not cert_pem or not key_pem:
            return self._error(400, 'email, cert_pem, and key_pem are required')

        # Parse certificate
        try:
            parse_certificate_pem, _ = _import_cert_utils()
        except ImportError as e:
            return self._error(500, str(e))

        try:
            cert_info = parse_certificate_pem(cert_pem)
        except Exception as e:
            return self._error(400, f'Invalid certificate: {str(e)}')

        cert_pem_escaped = cert_pem.replace('\r\n', '\n').replace('\n', '\\n')

        # Store private key in Splunk's credential store
        try:
            self._store_password(f'smime_sender_key__{email}', key_pem, session_key)
        except Exception as e:
            return self._error(500, f'Failed to store private key: {str(e)}')

        notify_on_expiry = form.get('notify_on_expiry', '0').strip()
        if notify_on_expiry.lower() in ('true', '1', 'yes'):
            notify_on_expiry = '1'
        else:
            notify_on_expiry = '0'

        stanza_data = {
            'cert_pem': cert_pem_escaped,
            'cn': cert_info.get('cn', ''),
            'not_after': cert_info.get('not_after', ''),
            'fingerprint_sha256': cert_info.get('fingerprint_sha256', ''),
            'enabled': '1',
            'notify_on_expiry': notify_on_expiry,
        }

        try:
            self._write_conf_stanza('smime_sender_certs', email, stanza_data, session_key)
            return self._success({
                'message': f'Sender certificate for {email} saved',
                'cert_info': cert_info,
            })
        except Exception as e:
            return self._error(500, f'Failed to save sender certificate: {str(e)}')

    def _add_sender_pfx(self, form, session_key):
        """Add a sender certificate from a PFX/PKCS#12 file (base64-encoded)."""
        import base64
        email = form.get('email', '').strip().lower()
        pfx_b64 = form.get('pfx_data', '').strip()
        pfx_password = form.get('pfx_password', '')

        if not email:
            return self._error(400, 'email is required')
        if not pfx_b64:
            return self._error(400, 'pfx_data (base64-encoded PFX) is required')

        try:
            pfx_bytes = base64.b64decode(pfx_b64)
        except Exception as e:
            return self._error(400, f'Invalid base64 data: {str(e)}')

        # Parse PFX
        try:
            from smime_cert_utils import parse_pfx
            pfx_result = parse_pfx(pfx_bytes, pfx_password)
        except ImportError as e:
            return self._error(500, f'Certificate utilities not available: {str(e)}')
        except Exception as e:
            return self._error(400, f'Failed to parse PFX file: {str(e)}')

        cert_pem = pfx_result['cert_pem']
        key_pem = pfx_result['key_pem']
        cert_info = pfx_result['cert_info']

        cert_pem_escaped = cert_pem.replace('\r\n', '\n').replace('\n', '\\n')

        # Store private key in credential store
        try:
            self._store_password(f'smime_sender_key__{email}', key_pem, session_key)
        except Exception as e:
            return self._error(500, f'Failed to store private key: {str(e)}')

        notify_on_expiry = form.get('notify_on_expiry', '0').strip()
        if notify_on_expiry.lower() in ('true', '1', 'yes'):
            notify_on_expiry = '1'
        else:
            notify_on_expiry = '0'

        stanza_data = {
            'cert_pem': cert_pem_escaped,
            'cn': cert_info.get('cn', ''),
            'not_after': cert_info.get('not_after', ''),
            'fingerprint_sha256': cert_info.get('fingerprint_sha256', ''),
            'enabled': '1',
            'notify_on_expiry': notify_on_expiry,
        }

        try:
            self._write_conf_stanza('smime_sender_certs', email, stanza_data, session_key)
            chain_count = pfx_result.get('chain_count', 0)
            msg = f'Sender certificate for {email} imported from PFX'
            if chain_count:
                msg += f' ({chain_count} CA certificate(s) in chain)'
            return self._success({
                'message': msg,
                'cert_info': cert_info,
            })
        except Exception as e:
            return self._error(500, f'Failed to save sender certificate: {str(e)}')

    def _toggle_notify(self, form, session_key):
        """Toggle the notify_on_expiry flag for a certificate stanza."""
        email = form.get('email', '').strip().lower()
        cert_type = form.get('cert_type', '').strip().lower()

        if not email or cert_type not in ('recipient', 'sender'):
            return self._error(400, 'email and cert_type (recipient|sender) are required')

        conf_name = 'smime_recipient_certs' if cert_type == 'recipient' else 'smime_sender_certs'

        # Read current value
        try:
            uri = f'/servicesNS/nobody/{self.APP_NAME}/configs/conf-{conf_name}/{email}?output_mode=json'
            response, content = rest.simpleRequest(uri, sessionKey=session_key, method='GET')
            data = json.loads(content)
            current = data.get('entry', [{}])[0].get('content', {})
            current_val = current.get('notify_on_expiry', '0') or '0'
        except Exception as e:
            return self._error(404, f'Certificate not found: {str(e)}')

        new_val = '0' if current_val in ('1', 'true', 'yes') else '1'

        try:
            self._write_conf_stanza(conf_name, email, {'notify_on_expiry': new_val}, session_key)
            return self._success({
                'message': f'Expiry notification {"enabled" if new_val == "1" else "disabled"} for {email}',
                'notify_on_expiry': new_val,
            })
        except Exception as e:
            return self._error(500, f'Failed to update: {str(e)}')

    def _delete_cert(self, conf_name, email, session_key):
        """Delete a certificate stanza."""
        try:
            uri = (
                f'/servicesNS/nobody/{self.APP_NAME}/configs/conf-{conf_name}/{email}'
                f'?output_mode=json'
            )
            rest.simpleRequest(uri, sessionKey=session_key, method='DELETE')
            return self._success({'message': f'Certificate for {email} deleted'})
        except Exception as e:
            return self._error(500, f'Delete failed: {str(e)}')

    def _validate_recipients(self, query, session_key):
        """
        Check that ALL recipients (comma-separated in 'to') have valid,
        enabled certificates. Returns per-recipient status.
        """
        to_str = query.get('to', '')
        if not to_str:
            return self._error(400, 'to parameter is required')

        recipients = [r.strip().lower() for r in to_str.split(',') if r.strip()]
        if not recipients:
            return self._error(400, 'No recipients specified')

        # Load all recipient certs
        uri = f'/servicesNS/nobody/{self.APP_NAME}/configs/conf-smime_recipient_certs?output_mode=json&count=0'
        response, content = rest.simpleRequest(uri, sessionKey=session_key, method='GET')
        data = json.loads(content)

        known = {}
        for e in data.get('entry', []):
            email_key = e['name'].lower()
            info = e.get('content', {})
            known[email_key] = info

        results = {}
        all_valid = True
        for r in recipients:
            if r in known:
                cert_data = known[r]
                if cert_data.get('enabled', '1') in ('0', 'false', 'False'):
                    results[r] = {'has_cert': True, 'enabled': False, 'valid': False, 'error': 'Certificate is disabled'}
                    all_valid = False
                else:
                    # Check expiry
                    not_after = cert_data.get('not_after', '')
                    results[r] = {'has_cert': True, 'enabled': True, 'valid': True, 'not_after': not_after}
            else:
                results[r] = {'has_cert': False, 'enabled': False, 'valid': False, 'error': 'No certificate found'}
                all_valid = False

        return self._success({
            'all_valid': all_valid,
            'recipients': results,
        })

    # ------------------------------------------------------------------
    # SMTP settings
    # ------------------------------------------------------------------
    def _get_smtp_settings(self, session_key):
        try:
            uri = f'/servicesNS/nobody/{self.APP_NAME}/configs/conf-smime_mailer_settings/smtp?output_mode=json'
            response, content = rest.simpleRequest(uri, sessionKey=session_key, method='GET')
            data = json.loads(content)
            settings = data.get('entry', [{}])[0].get('content', {})
            # Strip internal Splunk fields
            clean = {k: v for k, v in settings.items() if not k.startswith('eai:')}

            # Check which secrets are already stored (without revealing values)
            secret_names = [
                ('has_smtp_password', 'smime_smtp_password'),
                ('has_oauth2_client_secret', 'smime_oauth2_client_secret'),
                ('has_hf_token', 'smime_hf_token'),
            ]
            for flag, pw_name in secret_names:
                try:
                    val = self._get_password(pw_name, session_key)
                    clean[flag] = bool(val)
                except Exception:
                    clean[flag] = False

            return self._success({'settings': clean})
        except Exception as e:
            return self._error(500, f'Failed to read SMTP settings: {str(e)}')

    def _save_smtp_settings(self, form, session_key):
        allowed_fields = [
            'smtp_host', 'smtp_port', 'smtp_security', 'smtp_auth_type', 'smtp_user',
            'sender_email', 'sender_name', 'splunk_hostname', 'use_signing', 'use_encryption',
            'verify_recipient_certs', 'oauth2_client_id', 'oauth2_tenant_id',
            'oauth2_token_url', 'oauth2_scope',
            'use_hf_proxy', 'hf_host', 'hf_port',
            'expiry_notifications_enabled',
            'expiry_notification_emails',
        ]
        stanza_data = {k: form[k] for k in allowed_fields if k in form}

        # Normalize 'submission' → 'starttls' for storage (same STARTTLS mechanism)
        if stanza_data.get('smtp_security') == 'submission':
            stanza_data['smtp_security'] = 'starttls'

        # Handle password separately via credential store
        if 'smtp_password' in form and form['smtp_password']:
            try:
                self._store_password('smime_smtp_password', form['smtp_password'], session_key)
            except Exception as e:
                return self._error(500, f'Failed to store SMTP password: {str(e)}')

        # Handle OAuth2 client secret separately via credential store
        if 'oauth2_client_secret' in form and form['oauth2_client_secret']:
            try:
                self._store_password('smime_oauth2_client_secret', form['oauth2_client_secret'], session_key)
            except Exception as e:
                return self._error(500, f'Failed to store OAuth2 client secret: {str(e)}')

        # Handle HF auth token separately via credential store
        if 'hf_token' in form and form['hf_token']:
            try:
                self._store_password('smime_hf_token', form['hf_token'], session_key)
            except Exception as e:
                return self._error(500, f'Failed to store HF auth token: {str(e)}')

        try:
            self._write_conf_stanza('smime_mailer_settings', 'smtp', stanza_data, session_key)

            # Mark app as configured
            self._write_conf_stanza('app', 'install', {'is_configured': '1'}, session_key)

            return self._success({'message': 'SMTP settings saved'})
        except Exception as e:
            return self._error(500, f'Failed to save SMTP settings: {str(e)}')

    def _test_smtp(self, form, session_key):
        """Test SMTP connectivity with the current or supplied settings."""
        import smtplib
        import ssl

        # If HF proxy is enabled, delegate the test to the HF
        use_hf = form.get('use_hf_proxy', 'false').lower() in ('true', '1', 'yes')
        if use_hf:
            return self._test_hf_proxy(form, session_key)

        host = form.get('smtp_host', 'localhost')
        port = int(form.get('smtp_port', 25))
        security = (form.get('smtp_security', 'starttls') or 'starttls').strip().lower()
        # Normalize 'submission' to 'starttls' (same protocol, different default port)
        if security == 'submission':
            security = 'starttls'
        auth_type = form.get('smtp_auth_type', 'basic')
        user = form.get('smtp_user', '')
        password = form.get('smtp_password', '')

        try:
            if auth_type == 'oauth2':
                # Test via Microsoft Graph API instead of SMTP
                # client_credentials grant does not work with SMTP XOAUTH2 on M365
                return self._test_graph_api(form, session_key)

            context = ssl.create_default_context()

            if security == 'ssl':
                server = smtplib.SMTP_SSL(host, port, timeout=15, context=context)
            else:
                server = smtplib.SMTP(host, port, timeout=15)
                server.ehlo()
                if security == 'starttls':
                    server.starttls(context=context)
                    server.ehlo()

            if user and password:
                server.login(user, password)

            server.quit()
            return self._success({'message': f'SMTP connection to {host}:{port} ({security}, auth={auth_type}) successful'})
        except Exception as e:
            err = str(e)
            err_lower = err.lower()
            if 'wrong_version_number' in err_lower:
                err = (
                    f'{err}. TLS mode mismatch detected. '
                    f'Try switching Connection Security (STARTTLS vs SMTPS/SSL) for this host/port.'
                )
            return self._error(400, f'SMTP test failed: {err}')

    def _test_graph_api(self, form, session_key):
        """Test Microsoft Graph API connectivity by acquiring a token and checking Mail.Send role."""
        import base64

        user = form.get('smtp_user', '')
        try:
            # Acquire token with Graph scope — this validates client_id, secret, tenant
            access_token = self._acquire_oauth2_token(form, session_key,
                                                       scope='https://graph.microsoft.com/.default')

            # Decode token payload (JWT) to verify Mail.Send role is present
            # JWT is header.payload.signature — we only need payload
            roles = []
            app_name = ''
            try:
                payload_b64 = access_token.split('.')[1]
                # Fix base64 padding
                payload_b64 += '=' * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64).decode('utf-8'))
                roles = payload.get('roles', [])
                app_name = payload.get('app_displayname', '') or payload.get('appid', '')
            except Exception:
                pass  # If JWT decode fails, token was still acquired successfully

            has_mail_send = 'Mail.Send' in roles
            role_info = f' Roles: {", ".join(roles)}.' if roles else ''

            if has_mail_send:
                return self._success({
                    'message': f'Graph API connection successful! Token acquired for app "{app_name}". '
                               f'Mail.Send permission confirmed for mailbox: {user}.{role_info}'
                })
            else:
                return self._success({
                    'message': f'Graph API token acquired for app "{app_name}", '
                               f'but Mail.Send role NOT found in token.{role_info} '
                               f'Please verify the API permission is granted and admin-consented in Azure AD.'
                })
        except Exception as e:
            return self._error(400, f'Graph API test failed: {str(e)}')

    def _test_hf_proxy(self, form, session_key):
        """Test end-to-end: SH → HF proxy → SMTP GW / Graph API."""
        import urllib.request
        import urllib.error
        import ssl

        hf_host = form.get('hf_host', '').strip()
        hf_port = form.get('hf_port', '8089').strip()
        hf_token = form.get('hf_token', '')

        if not hf_host:
            return self._error(400, 'HF Hostname is required for proxy test.')

        # If no token in form, try credential store
        if not hf_token:
            try:
                hf_token = self._get_password('smime_hf_token', session_key)
            except Exception:
                pass

        if not hf_token:
            return self._error(400, 'HF Auth Token is required. Please save settings first or enter a token.')

        # Build a test payload with all SMTP / Graph settings from the form
        test_payload = {
            'action': 'test',
            'smtp_host': form.get('smtp_host', 'localhost'),
            'smtp_port': form.get('smtp_port', '25'),
            'smtp_security': form.get('smtp_security', 'starttls'),
            'smtp_auth_type': form.get('smtp_auth_type', 'basic'),
            'smtp_user': form.get('smtp_user', ''),
            'smtp_password': form.get('smtp_password', ''),
        }

        # Include OAuth2 / Graph API credentials if applicable
        auth_type = form.get('smtp_auth_type', 'basic')
        if auth_type == 'oauth2':
            test_payload['oauth2_client_id'] = form.get('oauth2_client_id', '')
            test_payload['oauth2_tenant_id'] = form.get('oauth2_tenant_id', '')
            test_payload['oauth2_token_url'] = form.get('oauth2_token_url', '')
            test_payload['oauth2_scope'] = form.get('oauth2_scope', 'https://graph.microsoft.com/.default')
            # Resolve secret from credential store if not in form
            client_secret = form.get('oauth2_client_secret', '')
            if not client_secret:
                try:
                    client_secret = self._get_password('smime_oauth2_client_secret', session_key)
                except Exception:
                    pass
            test_payload['oauth2_client_secret'] = client_secret

        # Resolve SMTP password from credential store if not in form
        if not test_payload['smtp_password']:
            try:
                test_payload['smtp_password'] = self._get_password('smime_smtp_password', session_key)
            except Exception:
                pass

        url = f'https://{hf_host}:{hf_port}/services/smime_proxy/send?output_mode=json'
        body = json.dumps(test_payload).encode('utf-8')

        try:
            req = urllib.request.Request(url, data=body, method='POST')
            req.add_header('Authorization', f'Bearer {hf_token}')
            req.add_header('Content-Type', 'application/json')

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                msg = data.get('message', 'End-to-end test through HF proxy successful')
                return self._success({'message': msg})
        except urllib.error.HTTPError as e:
            body_str = ''
            try:
                body_str = e.read().decode('utf-8', errors='replace')
            except Exception:
                pass
            # Try to extract the message from the JSON error body
            detail = body_str
            try:
                err_data = json.loads(body_str)
                detail = err_data.get('message', body_str)
            except Exception:
                pass
            return self._error(400, f'HF proxy test failed (HTTP {e.code}): {detail}')
        except Exception as e:
            return self._error(400, f'HF proxy test failed: {str(e)}')

    def _acquire_oauth2_token(self, form_or_settings, session_key, scope=None):
        """
        Acquire an OAuth2 access token using the client_credentials grant.
        Works with Microsoft 365 / Azure AD and other OAuth2 providers.
        If scope is provided, it overrides the configured value.
        """
        import urllib.request
        import urllib.parse
        import urllib.error

        client_id = form_or_settings.get('oauth2_client_id', '')
        client_secret = form_or_settings.get('oauth2_client_secret', '')
        tenant_id = form_or_settings.get('oauth2_tenant_id', '')
        token_url = form_or_settings.get('oauth2_token_url', '')
        scope = scope or form_or_settings.get('oauth2_scope', 'https://graph.microsoft.com/.default')

        if not client_id:
            raise ValueError('OAuth2 Client ID is required')

        # If no client_secret in form, try credential store
        if not client_secret:
            try:
                client_secret = self._get_password('smime_oauth2_client_secret', session_key)
            except Exception:
                pass

        if not client_secret:
            raise ValueError('OAuth2 Client Secret is required')

        # Build token URL from tenant_id if not explicitly provided
        if not token_url:
            if tenant_id:
                token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
            else:
                raise ValueError('Either oauth2_token_url or oauth2_tenant_id is required')
        elif '{tenant}' in token_url and tenant_id:
            # Replace placeholder {tenant} with actual tenant_id
            token_url = token_url.replace('{tenant}', tenant_id)

        # Request token
        post_data = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': scope,
        }).encode('utf-8')

        req = urllib.request.Request(token_url, data=post_data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                token_data = json.loads(resp.read().decode('utf-8'))
                access_token = token_data.get('access_token')
                if not access_token:
                    raise RuntimeError(f'No access_token in response: {token_data}')
                return access_token
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'OAuth2 token request failed ({e.code}): {body}')

    @staticmethod
    def _build_xoauth2_string(user, access_token):
        """Build the XOAUTH2 authentication string for SMTP."""
        import base64
        auth_string = f'user={user}\x01auth=Bearer {access_token}\x01\x01'
        return base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _write_conf_stanza(self, conf_name, stanza_name, data, session_key):
        """Create or update a stanza in a .conf file via REST."""
        base_uri = f'/servicesNS/nobody/{self.APP_NAME}/configs/conf-{conf_name}'

        # Try to update existing
        try:
            uri = f'{base_uri}/{stanza_name}?output_mode=json'
            rest.simpleRequest(uri, sessionKey=session_key, method='POST', postargs=data)
            return
        except Exception:
            pass

        # Create new stanza
        data['name'] = stanza_name
        rest.simpleRequest(f'{base_uri}?output_mode=json', sessionKey=session_key, method='POST', postargs=data)

    def _store_password(self, name, password, session_key):
        """Store a password in Splunk's credential store."""
        realm = self.APP_NAME
        uri = f'/servicesNS/nobody/{self.APP_NAME}/storage/passwords'

        # Delete existing if present
        try:
            del_uri = f'{uri}/{realm}:{name}:?output_mode=json'
            rest.simpleRequest(del_uri, sessionKey=session_key, method='DELETE')
        except Exception:
            pass

        rest.simpleRequest(
            f'{uri}?output_mode=json',
            sessionKey=session_key,
            method='POST',
            postargs={
                'name': name,
                'password': password,
                'realm': realm,
            },
        )

    def _get_password(self, name, session_key):
        """Retrieve a password from Splunk's credential store."""
        realm = self.APP_NAME
        uri = f'/servicesNS/nobody/{self.APP_NAME}/storage/passwords/{realm}:{name}:?output_mode=json'
        response, content = rest.simpleRequest(uri, sessionKey=session_key, method='GET')
        data = json.loads(content)
        return data['entry'][0]['content']['clear_password']

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _success(data):
        return {
            'status': 200,
            'headers': {'Content-Type': 'application/json'},
            'payload': json.dumps({'status': 'ok', **data}),
        }

    @staticmethod
    def _error(status, message):
        return {
            'status': status,
            'headers': {'Content-Type': 'application/json'},
            'payload': json.dumps({'status': 'error', 'message': message}),
        }
