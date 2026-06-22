"""
Splunk configuration helper for the S/MIME Mailer app.
Loads settings, certificates, and passwords from Splunk's REST API.
"""

import json
import logging
import splunk.rest as rest

logger = logging.getLogger('smime_mailer')

APP_NAME = 'TA-smime-mailer'


def get_smtp_settings(session_key):
    """
    Load SMTP configuration from smime_mailer_settings.conf [smtp] stanza.
    Returns a dict of settings.
    """
    uri = f'/servicesNS/nobody/{APP_NAME}/configs/conf-smime_mailer_settings/smtp?output_mode=json'
    try:
        response, content = rest.simpleRequest(uri, sessionKey=session_key, method='GET')
        data = json.loads(content)
        settings = data.get('entry', [{}])[0].get('content', {})
        # Strip Splunk internal keys
        return {k: v for k, v in settings.items() if not k.startswith('eai:')}
    except Exception as e:
        logger.error(f'Failed to load SMTP settings: {e}')
        return {}


def get_smtp_password(session_key):
    """Retrieve the SMTP password from Splunk's credential store."""
    return _get_password('smime_smtp_password', session_key)


def get_oauth2_client_secret(session_key):
    """Retrieve the OAuth2 client secret from Splunk's credential store."""
    return _get_password('smime_oauth2_client_secret', session_key)


def get_hf_token(session_key):
    """Retrieve the Heavy Forwarder auth token from Splunk's credential store."""
    return _get_password('smime_hf_token', session_key)


def get_all_recipient_certs(session_key):
    """
    Load all recipient certificates from smime_recipient_certs.conf.
    Returns a dict: {email: {cert_pem, cn, not_after, enabled, ...}}
    """
    uri = f'/servicesNS/nobody/{APP_NAME}/configs/conf-smime_recipient_certs?output_mode=json&count=0'
    try:
        response, content = rest.simpleRequest(uri, sessionKey=session_key, method='GET')
        data = json.loads(content)
        certs = {}
        for e in data.get('entry', []):
            name = e['name']
            if name == 'default':
                continue
            info = e.get('content', {})
            # Un-escape cert PEM
            if 'cert_pem' in info:
                info['cert_pem'] = info['cert_pem'].replace('\\n', '\n')
            certs[name.lower()] = info
        return certs
    except Exception as e:
        logger.error(f'Failed to load recipient certs: {e}')
        return {}


def get_recipient_cert_pem(email, session_key):
    """Get the PEM certificate for a specific recipient."""
    certs = get_all_recipient_certs(session_key)
    info = certs.get(email.lower())
    if info and info.get('enabled', '1') not in ('0', 'false', 'False'):
        return info.get('cert_pem')
    return None


def get_sender_cert(email, session_key):
    """
    Load the sender certificate PEM and private key PEM for signing.
    Uses list-based lookup to avoid '@' in URI paths.
    Returns (cert_pem, key_pem) or (None, None).
    """
    # List all sender certs and filter by email (avoids @ in URI)
    uri = f'/servicesNS/nobody/{APP_NAME}/configs/conf-smime_sender_certs?output_mode=json&count=0'
    try:
        response, content = rest.simpleRequest(uri, sessionKey=session_key, method='GET')
        data = json.loads(content)
        info = None
        for entry in data.get('entry', []):
            if entry.get('name', '').lower() == email.lower():
                info = entry.get('content', {})
                break
        if not info:
            logger.error(f'Sender cert stanza not found for {email}')
            return None, None
        cert_pem = info.get('cert_pem', '').replace('\\n', '\n')
        if not cert_pem:
            logger.error(f'Sender cert PEM is empty for {email}')
            return None, None
        key_pem = _get_password(f'smime_sender_key__{email}', session_key)
        if not key_pem:
            logger.error(
                f'Sender private key not found in credential store for {email}. '
                f'The certificate PEM is present in smime_sender_certs.conf, but the '
                f'private key is missing from storage/passwords. '
                f'Re-upload the sender certificate (.pfx/.pem) via the S/MIME Mailer '
                f'configuration page to restore the private key.'
            )
            return cert_pem, None
        logger.info(f'Loaded sender cert and key for {email}')
        return cert_pem, key_pem
    except Exception as e:
        logger.error(f'Failed to load sender cert for {email}: {e}')
        return None, None


def validate_all_recipients(recipients, session_key):
    """
    Check that every recipient in the list has a valid, enabled certificate.
    
    Args:
        recipients: list of email addresses.
        session_key: Splunk session key.
    
    Returns:
        (all_valid: bool, details: dict)
        details maps email -> {has_cert, enabled, error}
    """
    all_certs = get_all_recipient_certs(session_key)
    details = {}
    all_valid = True

    for rcpt in recipients:
        rcpt_lower = rcpt.strip().lower()
        if rcpt_lower in all_certs:
            cert_info = all_certs[rcpt_lower]
            enabled = cert_info.get('enabled', '1') not in ('0', 'false', 'False')
            if not enabled:
                details[rcpt_lower] = {'has_cert': True, 'enabled': False, 'error': 'Certificate disabled'}
                all_valid = False
            else:
                details[rcpt_lower] = {'has_cert': True, 'enabled': True, 'error': None}
        else:
            details[rcpt_lower] = {'has_cert': False, 'enabled': False, 'error': 'No certificate configured'}
            all_valid = False

    return all_valid, details


def build_recipient_cert_map(recipients, session_key):
    """
    Build a {email: pem_string} map for the given recipients.
    Only includes recipients that have valid, enabled certs.
    """
    all_certs = get_all_recipient_certs(session_key)
    cert_map = {}
    for rcpt in recipients:
        rcpt_lower = rcpt.strip().lower()
        if rcpt_lower in all_certs:
            info = all_certs[rcpt_lower]
            if info.get('enabled', '1') not in ('0', 'false', 'False'):
                cert_map[rcpt_lower] = info.get('cert_pem', '')
    return cert_map


def _get_password(name, session_key):
    """
    Retrieve a clear-text password from Splunk's credential store.
    Uses list-based lookup to avoid '@' and special chars in URI paths.
    """
    realm = APP_NAME
    uri = f'/servicesNS/nobody/{APP_NAME}/storage/passwords?output_mode=json&count=0&search={realm}'
    try:
        response, content = rest.simpleRequest(uri, sessionKey=session_key, method='GET')
        status = response.get('status', 'unknown') if hasattr(response, 'get') else getattr(response, 'status', 'unknown')
        data = json.loads(content)
        entries = data.get('entry', [])
        for entry in entries:
            ec = entry.get('content', {})
            if ec.get('realm') == realm and ec.get('username') == name:
                return ec.get('clear_password')

        # Not found -- log diagnostics to help troubleshoot
        found_usernames = [
            entry.get('content', {}).get('username', '?')
            for entry in entries
            if entry.get('content', {}).get('realm') == realm
        ]
        if not entries:
            logger.warning(
                f'Password not found in credential store: realm={realm}, name={name}. '
                f'The credential store returned 0 entries (HTTP {status}). '
                f'This typically means all stored passwords for {APP_NAME} are missing. '
                f'If you recently upgraded the app, you need to re-enter passwords '
                f'(SMTP password, sender private keys) via the configuration page.'
            )
        else:
            logger.warning(
                f'Password not found in credential store: realm={realm}, name={name}. '
                f'HTTP {status}, {len(entries)} total entries, '
                f'{len(found_usernames)} in realm {realm}: {found_usernames}'
            )
        return None
    except Exception as e:
        logger.error(f'Failed to retrieve password realm={realm}, name={name}: {e}')
        return None
