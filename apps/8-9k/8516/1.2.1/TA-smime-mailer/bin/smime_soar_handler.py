"""
S/MIME Mailer -- SOAR Integration REST Handler.

Receives email send requests from Splunk SOAR.  All certificate management,
S/MIME signing, encryption, and delivery is handled locally by TA-smime-mailer
on the Search Head.  SOAR only supplies the envelope (recipients, subject,
body, attachments) -- it never touches any certificate material.

Endpoints:
    GET  /services/smime_soar/send                               -- health check
    POST /services/smime_soar/send   {"action": "send", ...}     -- send an email
    POST /services/smime_soar/send   {"action": "test"}          -- test config
    POST /services/smime_soar/send   {"action": "check_certs", "to": "a@b,c@d"}
                                                                 -- validate recipient certs
    POST /services/smime_soar/send   {"action": "check_cert", "email": "a@b"}
                                                                 -- check one cert's details
"""

import json
import logging
import os
import sys
import traceback

lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

logger = logging.getLogger('smime_mailer.soar')

APP_NAME = 'TA-smime-mailer'


class SmimeSoarHandler(PersistentServerConnectionApplication):
    """REST handler: /services/smime_soar/send"""

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

            if method == 'GET':
                return self._health_check(session_key)
            elif method == 'POST':
                return self._dispatch_post(request, session_key)
            else:
                return self._error(405, f'Method {method} not allowed')

        except Exception as e:
            logger.error(f'SmimeSoarHandler error: {e}\n{traceback.format_exc()}')
            return self._error(500, f'Internal error: {str(e)}')

    # ------------------------------------------------------------------
    # Health check (used by SOAR test connectivity)
    # ------------------------------------------------------------------
    def _health_check(self, session_key):
        """Return basic app status so SOAR can confirm reachability."""
        try:
            settings = self._read_settings(session_key)
        except Exception as e:
            return self._error(500, f'Cannot read TA-smime-mailer settings: {e}')

        return self._success({
            'message': 'S/MIME Mailer SOAR endpoint is running.',
            'sender_email': settings.get('sender_email', ''),
            'use_signing': settings.get('use_signing', 'true'),
            'use_encryption': settings.get('use_encryption', 'true'),
            'smtp_auth_type': settings.get('smtp_auth_type', 'basic'),
            'use_hf_proxy': settings.get('use_hf_proxy', 'false'),
        })

    # ------------------------------------------------------------------
    # POST dispatcher
    # ------------------------------------------------------------------
    def _dispatch_post(self, request, session_key):
        payload_str = request.get('payload', '{}')
        try:
            payload = json.loads(payload_str)
        except (json.JSONDecodeError, TypeError):
            return self._error(400, 'Invalid JSON payload.')

        action = payload.get('action', 'send')

        if action == 'send':
            return self._send_email(payload, session_key)
        elif action == 'test':
            return self._test_config(payload, session_key)
        elif action == 'check_certs':
            return self._check_certs(payload, session_key)
        elif action == 'check_cert':
            return self._check_single_cert(payload, session_key)
        else:
            return self._error(400, f'Unknown action: {action}')

    # ==================================================================
    # Internal REST helpers -- explicit error handling, no silent failures
    # ==================================================================
    def _rest_get(self, uri, session_key):
        """GET a Splunk REST URI.  Returns parsed JSON dict.  Raises on error."""
        resp, content = rest.simpleRequest(
            uri, sessionKey=session_key, method='GET', raiseAllErrors=True,
        )
        return json.loads(content)

    def _read_settings(self, session_key):
        """Read TA-smime-mailer SMTP settings.  Raises on failure."""
        uri = (
            f'/servicesNS/nobody/{APP_NAME}'
            f'/configs/conf-smime_mailer_settings/smtp?output_mode=json'
        )
        data = self._rest_get(uri, session_key)
        settings = data.get('entry', [{}])[0].get('content', {})
        return {k: v for k, v in settings.items() if not k.startswith('eai:')}

    def _read_all_recipient_certs(self, session_key):
        """Read all recipient certificates.  Returns {email: info}.  Raises on failure."""
        uri = (
            f'/servicesNS/nobody/{APP_NAME}'
            f'/configs/conf-smime_recipient_certs?output_mode=json&count=0'
        )
        data = self._rest_get(uri, session_key)
        certs = {}
        for e in data.get('entry', []):
            name = e.get('name', '')
            if name in ('', 'default'):
                continue
            info = e.get('content', {})
            if 'cert_pem' in info:
                info['cert_pem'] = info['cert_pem'].replace('\\n', '\n')
            certs[name.lower()] = info
        logger.info(f'Loaded {len(certs)} recipient cert(s): {list(certs.keys())}')
        return certs

    def _read_password(self, name, session_key):
        """Retrieve a clear-text password by listing all and filtering.

        Uses the list approach instead of a direct GET to avoid URI-encoding
        issues with special characters (@, etc.) in password names.
        """
        realm = APP_NAME
        uri = (
            f'/servicesNS/nobody/{APP_NAME}'
            f'/storage/passwords?output_mode=json&count=0'
        )
        try:
            data = self._rest_get(uri, session_key)
            for entry in data.get('entry', []):
                content = entry.get('content', {})
                if content.get('realm') == realm and content.get('username') == name:
                    return content.get('clear_password')
            logger.warning(f'Password "{name}" not found in realm "{realm}"')
            return None
        except Exception as e:
            logger.warning(f'Password listing failed: {e}')
            return None

    def _read_sender_cert(self, email, session_key):
        """Load sender cert PEM and private key.  Returns (cert_pem, key_pem, diag)."""
        # List all sender cert stanzas to avoid @ in URI path
        uri = (
            f'/servicesNS/nobody/{APP_NAME}'
            f'/configs/conf-smime_sender_certs?output_mode=json&count=0'
        )
        cert_pem = None
        diag = {}
        try:
            data = self._rest_get(uri, session_key)
            stanzas = []
            for e in data.get('entry', []):
                name = e.get('name', '')
                if name == 'default':
                    continue
                stanzas.append(name)
                if name.lower() == email.lower():
                    info = e.get('content', {})
                    raw = info.get('cert_pem', '')
                    cert_pem = raw.replace('\\n', '\n') if raw else None
            diag['sender_cert_stanzas'] = stanzas
            diag['sender_cert_found'] = cert_pem is not None
        except Exception as e:
            logger.warning(f'Could not list sender certs: {e}')
            diag['sender_cert_error'] = str(e)
            return None, None, diag

        if not cert_pem:
            logger.warning(
                f'Sender cert stanza for {email} not found. '
                f'Available stanzas: {diag.get("sender_cert_stanzas", [])}'
            )
            return None, None, diag

        key_pem = self._read_password(f'smime_sender_key__{email}', session_key)
        diag['sender_key_found'] = key_pem is not None
        if not key_pem:
            logger.warning(f'Sender private key not found for {email}')
        return cert_pem, key_pem, diag

    # ==================================================================
    # ACTION: send -- Full email send with local cert resolution
    # ==================================================================
    def _send_email(self, payload, session_key):
        """Receive envelope from SOAR, load certs, sign/encrypt, send."""
        from smime_mailer_lib import SmimeMailer
        import base64

        # ---- Parse envelope from SOAR ----
        to_str = payload.get('to', '')
        cc_str = payload.get('cc', '')
        bcc_str = payload.get('bcc', '')
        subject = payload.get('subject', '')
        body = payload.get('body', '')
        content_type = payload.get('content_type', 'html')
        priority = payload.get('priority', '3')

        to_list = [t.strip() for t in to_str.split(',') if t.strip()]
        cc_list = [c.strip() for c in cc_str.split(',') if c.strip()] if cc_str else []
        bcc_list = [b.strip() for b in bcc_str.split(',') if b.strip()] if bcc_str else []

        if not to_list:
            return self._error(400, 'At least one recipient (to) is required.')

        all_recipients = to_list + cc_list + bcc_list

        # ---- Load TA-smime-mailer config from Splunk ----
        try:
            settings = self._read_settings(session_key)
        except Exception as e:
            return self._error(500,
                f'Cannot read TA-smime-mailer settings: {e}. '
                f'Check that the token user has read access to '
                f'{APP_NAME}/configs/conf-smime_mailer_settings.'
            )

        smtp_password = self._read_password('smime_smtp_password', session_key)
        oauth2_secret = self._read_password('smime_oauth2_client_secret', session_key)
        hf_token = self._read_password('smime_hf_token', session_key)

        # Sender email: SOAR override -> TA-smime-mailer config
        sender_email = (
            payload.get('sender_email', '').strip()
            or settings.get('sender_email', '')
        )
        if not sender_email:
            return self._error(400,
                'Sender email is not configured. '
                'Set it in TA-smime-mailer settings or pass sender_email in the request.'
            )

        use_signing = settings.get('use_signing', 'true').lower() in ('true', '1', 'yes')
        use_encryption = settings.get('use_encryption', 'true').lower() in ('true', '1', 'yes')

        # ---- Load recipient certificates ----
        all_certs = {}
        if use_encryption:
            try:
                all_certs = self._read_all_recipient_certs(session_key)
            except Exception as e:
                return self._error(500,
                    f'Cannot read recipient certificates: {e}. '
                    f'Check that the token user has read access to '
                    f'{APP_NAME}/configs/conf-smime_recipient_certs.'
                )

            # Validate every recipient has a cert
            cert_errors = []
            for rcpt in all_recipients:
                rcpt_lower = rcpt.strip().lower()
                if rcpt_lower not in all_certs:
                    cert_errors.append({
                        'email': rcpt_lower,
                        'error': 'no_certificate',
                        'message': f'No S/MIME certificate configured for {rcpt_lower}',
                    })
                else:
                    info = all_certs[rcpt_lower]
                    if info.get('enabled', '1') in ('0', 'false', 'False'):
                        cert_errors.append({
                            'email': rcpt_lower,
                            'error': 'certificate_disabled',
                            'message': f'Certificate for {rcpt_lower} is disabled',
                        })

            if cert_errors:
                return self._error(400, json.dumps({
                    'error': 'recipient_cert_validation_failed',
                    'message': (
                        f'Encryption is enabled but certificates are missing or '
                        f'invalid for {len(cert_errors)} recipient(s).'
                    ),
                    'cert_errors': cert_errors,
                    'recipients_checked': len(all_recipients),
                    'known_certs': list(all_certs.keys()),
                }))

        # Build cert map
        recipient_cert_map = {}
        if use_encryption:
            for rcpt in all_recipients:
                rcpt_lower = rcpt.strip().lower()
                info = all_certs.get(rcpt_lower, {})
                pem = info.get('cert_pem', '')
                if pem:
                    recipient_cert_map[rcpt_lower] = pem

        # ---- Check sender certificate if signing is enabled ----
        sender_cert_pem = ''
        sender_key_pem = ''

        if use_signing:
            sender_cert_pem, sender_key_pem, sender_diag = self._read_sender_cert(
                sender_email, session_key
            )
            if not sender_cert_pem or not sender_key_pem:
                return self._error(400, json.dumps({
                    'error': 'sender_cert_missing',
                    'message': (
                        f'Signing is enabled but no sender certificate/key found '
                        f'for {sender_email} in TA-smime-mailer.'
                    ),
                    'diagnostics': sender_diag,
                }))

            # Validate sender cert is not expired
            try:
                from smime_cert_utils import validate_certificate
                validation = validate_certificate(sender_cert_pem)
                if not validation.get('valid'):
                    return self._error(400, json.dumps({
                        'error': 'sender_cert_invalid',
                        'message': (
                            f'Sender certificate for {sender_email} is invalid: '
                            f'{validation.get("error", "unknown error")}'
                        ),
                    }))
            except ImportError:
                logger.warning('smime_cert_utils not available -- skipping sender cert validation')

        # ---- Check recipient cert expiry ----
        if use_encryption and recipient_cert_map:
            try:
                from smime_cert_utils import validate_certificate
                cert_errors = []
                for rcpt_email, rcpt_pem in recipient_cert_map.items():
                    v = validate_certificate(rcpt_pem)
                    if not v.get('valid'):
                        cert_errors.append({
                            'email': rcpt_email,
                            'error': 'certificate_expired',
                            'message': (
                                f'Certificate for {rcpt_email} is expired/invalid: '
                                f'{v.get("error", "unknown")}'
                            ),
                        })
                if cert_errors:
                    return self._error(400, json.dumps({
                        'error': 'recipient_cert_expired',
                        'message': f'{len(cert_errors)} recipient certificate(s) are expired or invalid.',
                        'cert_errors': cert_errors,
                    }))
            except ImportError:
                logger.warning('cryptography not available -- skipping cert expiry check')

        # ---- Parse attachments ----
        attachments = []
        att_json = payload.get('attachments_json', '')
        if att_json:
            try:
                att_list = json.loads(att_json) if isinstance(att_json, str) else att_json
                for att in att_list:
                    data_b64 = att.get('data_b64', '')
                    data_bytes = base64.b64decode(data_b64) if data_b64 else b''
                    attachments.append({
                        'filename': att.get('filename', 'attachment'),
                        'data': data_bytes,
                        'mime_type': att.get('mime_type', 'application/octet-stream'),
                    })
            except Exception as e:
                return self._error(400, f'Invalid attachments_json: {e}')

        # ---- Initialize mailer and send ----
        try:
            mailer = SmimeMailer(
                smtp_host=settings.get('smtp_host', 'localhost'),
                smtp_port=int(settings.get('smtp_port', 25)),
                smtp_security=settings.get('smtp_security', 'starttls'),
                smtp_auth_type=settings.get('smtp_auth_type', 'basic'),
                smtp_user=settings.get('smtp_user', ''),
                smtp_password=smtp_password or '',
                oauth2_client_id=settings.get('oauth2_client_id', ''),
                oauth2_client_secret=oauth2_secret or '',
                oauth2_tenant_id=settings.get('oauth2_tenant_id', ''),
                oauth2_token_url=settings.get('oauth2_token_url', ''),
                oauth2_scope=settings.get(
                    'oauth2_scope', 'https://graph.microsoft.com/.default'
                ),
                sender_email=sender_email,
                sender_name=settings.get('sender_name', ''),
                sender_cert_pem=sender_cert_pem,
                sender_key_pem=sender_key_pem,
                sign=use_signing,
                encrypt=use_encryption,
                use_hf_proxy=settings.get('use_hf_proxy', 'false'),
                hf_host=settings.get('hf_host', ''),
                hf_port=settings.get('hf_port', '8089'),
                hf_token=hf_token or '',
            )
        except Exception as e:
            return self._error(500, f'Failed to initialize mailer: {e}')

        try:
            result = mailer.send(
                to=to_list,
                subject=subject,
                body=body,
                content_type=content_type,
                cc=cc_list,
                bcc=bcc_list,
                attachments=attachments if attachments else None,
                recipient_certs=recipient_cert_map if recipient_cert_map else None,
                priority=priority,
            )

            message_id = result.get('message_id', '')
            use_hf = settings.get('use_hf_proxy', 'false').lower() in ('true', '1')
            transport = (
                'hf_proxy' if use_hf
                else 'graph_api' if settings.get('smtp_auth_type') == 'oauth2'
                else 'smtp'
            )

            logger.info(
                f'SOAR email sent: to={to_list}, cc={cc_list}, bcc={bcc_list}, '
                f'subject="{subject}", transport={transport}, '
                f'signed={use_signing}, encrypted={use_encryption}'
            )

            return self._success({
                'message': f'Email sent to {len(all_recipients)} recipient(s)',
                'message_id': message_id,
                'recipients_count': len(all_recipients),
                'transport': transport,
                'signed': use_signing,
                'encrypted': use_encryption,
                'sender_email': sender_email,
            })

        except Exception as e:
            logger.error(f'SOAR email send failed: {e}\n{traceback.format_exc()}')
            return self._error(500, f'Email send failed: {str(e)}')

    # ==================================================================
    # ACTION: test -- Validate TA-smime-mailer configuration
    # ==================================================================
    def _test_config(self, payload, session_key):
        """Run a full config check."""
        issues = []
        info = {}

        try:
            settings = self._read_settings(session_key)
        except Exception as e:
            return self._success({
                'message': f'Cannot read settings: {e}',
                'config_valid': False,
                'issues': [f'Cannot read smime_mailer_settings: {e}'],
                'info': {},
            })

        sender_email = settings.get('sender_email', '')
        if not sender_email:
            issues.append('Sender email is not configured.')
        else:
            info['sender_email'] = sender_email

        auth_type = settings.get('smtp_auth_type', 'basic')
        info['smtp_auth_type'] = auth_type
        use_hf = settings.get('use_hf_proxy', 'false').lower() in ('true', '1', 'yes')
        info['use_hf_proxy'] = use_hf

        if auth_type == 'oauth2':
            if not settings.get('oauth2_client_id'):
                issues.append('OAuth2 Client ID is not configured.')
            secret = self._read_password('smime_oauth2_client_secret', session_key)
            if not secret:
                issues.append('OAuth2 Client Secret is not stored.')
            else:
                info['oauth2_client_secret_stored'] = True
        else:
            smtp_host = settings.get('smtp_host', '')
            if not smtp_host:
                issues.append('SMTP host is not configured.')
            info['smtp_host'] = smtp_host
            info['smtp_port'] = settings.get('smtp_port', '25')

        if use_hf:
            hf_host = settings.get('hf_host', '')
            if not hf_host:
                issues.append('HF proxy is enabled but hf_host is not set.')
            hf_token = self._read_password('smime_hf_token', session_key)
            if not hf_token:
                issues.append('HF proxy is enabled but hf_token is not stored.')
            else:
                info['hf_token_stored'] = True

        use_signing = settings.get('use_signing', 'true').lower() in ('true', '1', 'yes')
        info['use_signing'] = use_signing
        info['use_encryption'] = settings.get(
            'use_encryption', 'true'
        ).lower() in ('true', '1', 'yes')

        if use_signing and sender_email:
            cert_pem, key_pem, _diag = self._read_sender_cert(sender_email, session_key)
            if not cert_pem:
                issues.append(f'No sender certificate found for {sender_email}.')
            elif not key_pem:
                issues.append(
                    f'Sender certificate exists but private key is missing for {sender_email}.'
                )
            else:
                info['sender_cert_found'] = True
                info['sender_key_found'] = True
                try:
                    from smime_cert_utils import validate_certificate
                    v = validate_certificate(cert_pem)
                    if v.get('valid'):
                        ci = v.get('cert_info', {})
                        info['sender_cert_cn'] = ci.get('cn', '')
                        info['sender_cert_expires'] = ci.get('not_after', '')
                        info['sender_cert_valid'] = True
                    else:
                        issues.append(f'Sender cert issue: {v.get("error", "unknown")}')
                except ImportError:
                    info['sender_cert_valid'] = 'unknown (cert validation library not available)'

        # Test access to recipient certs
        try:
            all_certs = self._read_all_recipient_certs(session_key)
            info['recipient_certs_count'] = len(all_certs)
            info['recipient_emails'] = list(all_certs.keys())
        except Exception as e:
            issues.append(f'Cannot read recipient certificates: {e}')

        if issues:
            return self._success({
                'message': f'Configuration has {len(issues)} issue(s)',
                'config_valid': False,
                'issues': issues,
                'info': info,
            })
        else:
            return self._success({
                'message': 'Configuration looks good',
                'config_valid': True,
                'issues': [],
                'info': info,
            })

    # ==================================================================
    # ACTION: check_certs -- Validate certs for a list of recipients
    # ==================================================================
    def _check_certs(self, payload, session_key):
        """Check whether all listed recipients have valid, non-expired certs."""
        to_str = payload.get('to', '')
        if not to_str:
            return self._error(400, '"to" parameter is required (comma-separated emails)')

        recipients = [r.strip().lower() for r in to_str.split(',') if r.strip()]

        try:
            all_certs = self._read_all_recipient_certs(session_key)
        except Exception as e:
            return self._error(500, f'Cannot read recipient certificates: {e}')

        results = []
        all_ok = True

        for rcpt in recipients:
            if rcpt not in all_certs:
                results.append({
                    'email': rcpt,
                    'has_certificate': False, 'enabled': False, 'valid': False,
                    'error': 'no_certificate',
                    'message': f'No certificate configured for {rcpt}',
                })
                all_ok = False
                continue

            info = all_certs[rcpt]
            enabled = info.get('enabled', '1') not in ('0', 'false', 'False')

            if not enabled:
                results.append({
                    'email': rcpt,
                    'has_certificate': True, 'enabled': False, 'valid': False,
                    'error': 'certificate_disabled',
                    'message': f'Certificate for {rcpt} is disabled',
                })
                all_ok = False
                continue

            cert_pem = info.get('cert_pem', '')
            cert_valid = True

            if cert_pem:
                try:
                    from smime_cert_utils import validate_certificate
                    v = validate_certificate(cert_pem)
                    cert_valid = v.get('valid', False)
                    if not cert_valid:
                        results.append({
                            'email': rcpt,
                            'has_certificate': True, 'enabled': True, 'valid': False,
                            'error': 'certificate_expired',
                            'message': v.get('error', 'Certificate validation failed'),
                        })
                        all_ok = False
                        continue
                except ImportError:
                    pass

            results.append({
                'email': rcpt,
                'has_certificate': True, 'enabled': True, 'valid': cert_valid,
                'error': '',
                'message': 'OK',
            })

        return self._success({
            'all_valid': all_ok,
            'recipients_checked': len(recipients),
            'recipients': results,
        })

    # ==================================================================
    # ACTION: check_cert -- Detailed info for one cert
    # ==================================================================
    def _check_single_cert(self, payload, session_key):
        """Return detailed certificate info for a single email address."""
        email = (payload.get('email', '') or '').strip().lower()
        if not email:
            return self._error(400, '"email" parameter is required')

        try:
            all_certs = self._read_all_recipient_certs(session_key)
        except Exception as e:
            return self._error(500, f'Cannot read recipient certificates: {e}')

        if email not in all_certs:
            return self._error(404, f'No certificate found for {email}')

        info = all_certs[email]
        cert_pem = info.get('cert_pem', '')

        result = {
            'email': email,
            'cn': info.get('cn', ''),
            'not_after': info.get('not_after', ''),
            'not_before': info.get('not_before', ''),
            'issuer': info.get('issuer', ''),
            'serial': info.get('serial', ''),
            'fingerprint_sha256': info.get('fingerprint_sha256', ''),
            'enabled': info.get('enabled', '1'),
            'notify_on_expiry': info.get('notify_on_expiry', '0'),
        }

        if cert_pem:
            try:
                from smime_cert_utils import validate_certificate
                import datetime

                v = validate_certificate(cert_pem)
                result['valid'] = v.get('valid', False)
                ci = v.get('cert_info', {})

                not_after_str = ci.get('not_after', '')
                if not_after_str:
                    try:
                        not_after_dt = datetime.datetime.fromisoformat(
                            not_after_str.replace('Z', '+00:00')
                        )
                        now = datetime.datetime.now(datetime.timezone.utc)
                        delta = not_after_dt - now
                        result['days_to_expiration'] = int(
                            delta.total_seconds() / 86400
                        )
                        if delta.total_seconds() <= 0:
                            result['status'] = 'expired'
                        elif result['days_to_expiration'] <= 30:
                            result['status'] = 'expiring_soon'
                        else:
                            result['status'] = 'valid'
                    except Exception:
                        result['status'] = 'unknown'

                result['email_addresses'] = ci.get('email_addresses', [])
                result['key_usage'] = ci.get('key_usage', {})

            except ImportError:
                result['valid'] = None
                result['status'] = 'unknown'

        return self._success({'certificate': result})

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
