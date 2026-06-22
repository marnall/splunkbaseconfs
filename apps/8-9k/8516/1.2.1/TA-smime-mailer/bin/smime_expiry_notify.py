#!/usr/bin/env python
"""
Splunk Custom Search Command: smimeexpirynotify

Checks certificate, token, and secret expiry status and sends
S/MIME encrypted notification emails to configured administrators
and (optionally) to individual certificate owners.

The command is designed to run as a scheduled saved search.

Notification schedule (pre-expiry):
    - 21 days before expiry
    - 14 days before expiry
    - 7 days before expiry
    - 24 hours before expiry
After expiry: every 2 days.

Usage in SPL:
    | smimeexpirynotify
"""

import csv
import io
import json
import logging
import os
import sys
import time
import datetime

# Setup paths
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
lib_dir = os.path.join(app_dir, 'lib')
sys.path.insert(0, lib_dir)
sys.path.insert(0, os.path.join(app_dir, 'bin'))

from splunklib.searchcommands import (
    dispatch, GeneratingCommand, Configuration, Option, validators
)
import splunklib.client as client

from splunk_config_helper import (
    get_smtp_settings, get_smtp_password, get_oauth2_client_secret, get_hf_token,
    get_all_recipient_certs, get_sender_cert, build_recipient_cert_map
)
from smime_mailer_lib import SmimeMailer

logger = logging.getLogger('smime_mailer.expiry_notify')

APP_NAME = 'TA-smime-mailer'
LOOKUP_FILENAME = 'smime_expiry_notify_tracker.csv'


def _get_milestone(days):
    """Return the notification milestone for the given days-to-expiration.

    Returns None if no notification is needed (days > 21).
    """
    if days is None:
        return None
    if days < 0:
        return 'expired'
    elif days <= 1:
        return '24h'
    elif days <= 7:
        return '7d'
    elif days <= 14:
        return '14d'
    elif days <= 21:
        return '21d'
    return None


def _should_notify(days, last_milestone, last_notified_epoch, now_epoch):
    """Decide whether a notification should be sent.

    Returns (should_send: bool, milestone: str|None).
    """
    milestone = _get_milestone(days)
    if milestone is None:
        return False, None

    if milestone == 'expired':
        # After expiry: notify every 48 hours
        if last_milestone == 'expired' and last_notified_epoch:
            hours_since = (now_epoch - last_notified_epoch) / 3600
            if hours_since < 48:
                return False, None
        return True, milestone

    # Pre-expiry: only notify once per milestone
    if milestone == last_milestone:
        return False, None

    return True, milestone


def _build_subject(milestone, entry):
    """Build the email subject line."""
    cert_type = entry.get('cert_type', 'certificate')
    name = entry.get('cert_name', '') or entry.get('email', 'unknown')
    email = entry.get('email', '')
    label = f'{cert_type}: {name}'
    if email and email != name:
        label += f' ({email})'

    if milestone == 'expired':
        return f'[EXPIRED] {label}'
    elif milestone == '24h':
        return f'[URGENT] Expires in <24 hours: {label}'
    else:
        days = entry.get('days_to_expiration', '?')
        return f'[Expiry Warning] {label} — {days} days remaining'


def _build_body_html(milestone, entry):
    """Build an HTML notification email body."""
    cert_type = entry.get('cert_type', 'certificate')
    name = entry.get('cert_name', '') or entry.get('email', '')
    email = entry.get('email', '')
    not_after = entry.get('not_after', 'N/A')
    days = entry.get('days_to_expiration', '?')
    issuer = entry.get('issuer', '')
    fingerprint = entry.get('fingerprint_sha256', '')
    status = entry.get('status', '')

    # Colour coding
    if milestone == 'expired':
        banner_color = '#cc0000'
        banner_text = 'EXPIRED'
        intro = (
            f'The following {cert_type} has <b>expired</b> and needs '
            f'immediate renewal to restore service.'
        )
    elif milestone == '24h':
        banner_color = '#e65100'
        banner_text = 'EXPIRES IN LESS THAN 24 HOURS'
        intro = (
            f'The following {cert_type} will expire <b>within 24 hours</b>. '
            f'Please renew it immediately.'
        )
    else:
        banner_color = '#f9a825'
        banner_text = f'EXPIRES IN {days} DAYS'
        intro = (
            f'The following {cert_type} is approaching its expiry date. '
            f'Please plan for renewal.'
        )

    # Type-specific description
    type_labels = {
        'recipient': 'Recipient Certificate (Public Key)',
        'sender': 'Sender Certificate (Signing Key)',
        'token': 'HF Proxy Bearer Token',
        'azure_secret': 'Azure App Client Secret',
    }
    type_label = type_labels.get(cert_type, cert_type)

    rows = f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Type</td>
            <td style="padding:8px;">{type_label}</td></tr>
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Name / CN</td>
            <td style="padding:8px;">{name}</td></tr>
    '''
    if email:
        rows += f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Email</td>
            <td style="padding:8px;">{email}</td></tr>
        '''
    rows += f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Expires</td>
            <td style="padding:8px;">{not_after}</td></tr>
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Days Remaining</td>
            <td style="padding:8px;">{days}</td></tr>
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Status</td>
            <td style="padding:8px;">{status}</td></tr>
    '''
    if issuer:
        rows += f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Issuer</td>
            <td style="padding:8px;">{issuer}</td></tr>
        '''
    if fingerprint:
        rows += f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Fingerprint (SHA-256)</td>
            <td style="padding:8px;font-family:monospace;font-size:0.85em;">{fingerprint}</td></tr>
        '''

    html = f'''<html>
<body style="font-family:Arial,Helvetica,sans-serif;color:#333;margin:0;padding:0;">
  <div style="background:{banner_color};color:#fff;padding:16px 24px;font-size:18px;font-weight:bold;">
    &#9888; {banner_text}
  </div>
  <div style="padding:24px;">
    <p style="font-size:14px;">{intro}</p>
    <table style="border-collapse:collapse;width:100%;border:1px solid #ddd;margin:16px 0;">
      {rows}
    </table>
    <p style="font-size:14px;">
      Please renew or replace this {cert_type} as soon as possible to avoid
      service disruption.
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0;" />
    <p style="color:#999;font-size:12px;">
      This is an automated notification from <b>S/MIME Mailer</b> (TA-smime-mailer).
      Configure notification recipients in the app setup page.
    </p>
  </div>
</body>
</html>'''
    return html


# ------------------------------------------------------------------
# CRL revocation notification helpers
# ------------------------------------------------------------------

# Maximum re-notify interval for revoked certs: once per 7 days (168 hours)
REVOKED_RENOTIFY_HOURS = 168


def _should_notify_revoked(last_milestone, last_notified_epoch, now_epoch):
    """Decide whether a revocation notification should be sent.

    Returns True if no previous 'revoked' notification was sent, or
    if at least REVOKED_RENOTIFY_HOURS have elapsed since the last one.
    """
    if last_milestone != 'revoked' or not last_notified_epoch:
        return True
    hours_since = (now_epoch - last_notified_epoch) / 3600
    return hours_since >= REVOKED_RENOTIFY_HOURS


def _build_subject_revoked(entry):
    """Build the email subject line for a revoked certificate."""
    cert_type = entry.get('cert_type', 'certificate')
    name = entry.get('cert_name', '') or entry.get('email', 'unknown')
    email = entry.get('email', '')
    label = f'{cert_type}: {name}'
    if email and email != name:
        label += f' ({email})'
    return f'[REVOKED] Certificate revoked: {label}'


def _build_body_html_revoked(entry):
    """Build an HTML notification email body for a revoked certificate."""
    cert_type = entry.get('cert_type', 'certificate')
    name = entry.get('cert_name', '') or entry.get('email', '')
    email = entry.get('email', '')
    not_after = entry.get('not_after', 'N/A')
    issuer = entry.get('issuer', '')
    fingerprint = entry.get('fingerprint_sha256', '')
    crl_reason = entry.get('crl_reason', 'unspecified')
    crl_revocation_date = entry.get('crl_revocation_date', 'unknown')
    crl_url = entry.get('crl_url', '')

    type_labels = {
        'recipient': 'Recipient Certificate (Public Key)',
        'sender': 'Sender Certificate (Signing Key)',
    }
    type_label = type_labels.get(cert_type, cert_type)

    rows = f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Type</td>
            <td style="padding:8px;">{type_label}</td></tr>
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Name / CN</td>
            <td style="padding:8px;">{name}</td></tr>
    '''
    if email:
        rows += f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Email</td>
            <td style="padding:8px;">{email}</td></tr>
        '''
    rows += f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Revocation Reason</td>
            <td style="padding:8px;color:#cc0000;font-weight:bold;">{crl_reason}</td></tr>
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Revocation Date</td>
            <td style="padding:8px;">{crl_revocation_date}</td></tr>
    '''
    if crl_url:
        rows += f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">CRL Source</td>
            <td style="padding:8px;font-family:monospace;font-size:0.85em;">{crl_url}</td></tr>
        '''
    rows += f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Expires</td>
            <td style="padding:8px;">{not_after}</td></tr>
    '''
    if issuer:
        rows += f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Issuer</td>
            <td style="padding:8px;">{issuer}</td></tr>
        '''
    if fingerprint:
        rows += f'''
        <tr><td style="padding:8px;font-weight:bold;background:#f5f5f5;">Fingerprint (SHA-256)</td>
            <td style="padding:8px;font-family:monospace;font-size:0.85em;">{fingerprint}</td></tr>
        '''

    html = f'''<html>
<body style="font-family:Arial,Helvetica,sans-serif;color:#333;margin:0;padding:0;">
  <div style="background:#b71c1c;color:#fff;padding:16px 24px;font-size:18px;font-weight:bold;">
    &#9888; CERTIFICATE REVOKED
  </div>
  <div style="padding:24px;">
    <p style="font-size:14px;">
      The following {cert_type} has been <b style="color:#cc0000;">revoked</b> by its
      Certificate Authority and should be replaced immediately. Using a revoked
      certificate may compromise message security and trust.
    </p>
    <table style="border-collapse:collapse;width:100%;border:1px solid #ddd;margin:16px 0;">
      {rows}
    </table>
    <p style="font-size:14px;">
      <b>Action required:</b> Replace this certificate with a newly issued one
      and upload it in the S/MIME Mailer Certificate Management page.
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0;" />
    <p style="color:#999;font-size:12px;">
      This is an automated notification from <b>S/MIME Mailer</b> (TA-smime-mailer).
      You will receive this alert at most once per week until the certificate is replaced.
    </p>
  </div>
</body>
</html>'''
    return html


@Configuration(type='reporting')
class SmimeExpiryNotifyCommand(GeneratingCommand):
    """
    Generating command that checks certificate / token / secret expiry
    and sends S/MIME encrypted notification emails.
    """

    dryrun = Option(
        doc='If true, only report what would be sent without actually sending.',
        require=False,
        default='false',
    )

    def generate(self):
        """Main entry point — called by Splunk search pipeline."""
        session_key = self.metadata.searchinfo.session_key
        is_dryrun = str(self.dryrun).lower() in ('true', '1', 'yes')
        now_epoch = time.time()
        now_dt = datetime.datetime.now(datetime.timezone.utc)

        # ----------------------------------------------------------
        # 1. Load settings
        # ----------------------------------------------------------
        settings = get_smtp_settings(session_key)

        # Check global enable flag
        notifications_enabled = (settings.get('expiry_notifications_enabled', 'false') or 'false').lower() in ('true', '1', 'yes')
        if not notifications_enabled and not is_dryrun:
            yield self._event(
                action='skipped',
                detail='Expiry notifications are globally disabled. Enable them in Certificate Management.',
                _time=now_epoch,
            )
            return

        admin_emails_raw = settings.get('expiry_notification_emails', '') or ''
        admin_emails = [e.strip().lower() for e in admin_emails_raw.split(',') if e.strip()]

        if not admin_emails and not is_dryrun:
            yield self._event(
                action='skipped',
                detail='No admin notification emails configured. Skipping.',
                _time=now_epoch,
            )
            return

        # ----------------------------------------------------------
        # 2. Query cert monitor REST endpoint
        # ----------------------------------------------------------
        try:
            monitor_entries = self._query_cert_monitor(session_key)
        except Exception as e:
            yield self._event(
                action='error',
                detail=f'Failed to query cert monitor: {e}',
                _time=now_epoch,
            )
            return

        if not monitor_entries:
            yield self._event(
                action='skipped',
                detail='No certificates/tokens/secrets found.',
                _time=now_epoch,
            )
            return

        # ----------------------------------------------------------
        # 3. Load tracking state
        # ----------------------------------------------------------
        tracker = self._load_tracker()

        # ----------------------------------------------------------
        # 4. Initialize mailer (lazily, only if needed)
        # ----------------------------------------------------------
        mailer = None

        # ----------------------------------------------------------
        # 5. Process each entry
        # ----------------------------------------------------------
        notifications_sent = 0
        tracker_updated = False

        for entry in monitor_entries:
            content = entry.get('content', {})
            entry_key = entry.get('name', '')
            days_str = content.get('days_to_expiration', '')
            status = content.get('status', '')
            cert_type = content.get('cert_type', '')
            email = content.get('email', '')
            notify_on_expiry = content.get('notify_on_expiry', '0')

            # ------ CRL Revocation alert (separate from expiry) ------
            crl_revoked = str(content.get('crl_revoked', 'false')).lower() in ('true', '1', 'yes')
            if crl_revoked and cert_type in ('recipient', 'sender'):
                revoke_key = f'revoked__{entry_key}'
                track_info_rev = tracker.get(revoke_key, {})
                last_mile_rev = track_info_rev.get('last_milestone', '')
                try:
                    last_epoch_rev = float(track_info_rev.get('last_notified_epoch', 0))
                except (ValueError, TypeError):
                    last_epoch_rev = 0

                if _should_notify_revoked(last_mile_rev, last_epoch_rev, now_epoch):
                    # Determine recipients for revocation alert
                    rev_recipients = list(admin_emails)
                    rev_notify_user = (
                        str(notify_on_expiry).lower() in ('true', '1', 'yes')
                        and email
                    )
                    if rev_notify_user and email.lower() not in rev_recipients:
                        rev_recipients.append(email.lower())

                    if rev_recipients:
                        rev_subject = _build_subject_revoked(content)
                        rev_body = _build_body_html_revoked(content)

                        if is_dryrun:
                            yield self._event(
                                action='dryrun_revoked',
                                entry_key=entry_key,
                                milestone='revoked',
                                recipients=', '.join(rev_recipients),
                                subject=rev_subject,
                                cert_type=cert_type,
                                email=email,
                                crl_reason=content.get('crl_reason', ''),
                                crl_revocation_date=content.get('crl_revocation_date', ''),
                                _time=now_epoch,
                            )
                            tracker[revoke_key] = {
                                'last_milestone': 'revoked',
                                'last_notified_epoch': str(now_epoch),
                            }
                            tracker_updated = True
                        else:
                            # Initialize mailer on first actual send
                            if mailer is None:
                                try:
                                    mailer = self._init_mailer(session_key, settings)
                                except Exception as e:
                                    yield self._event(
                                        action='error',
                                        detail=f'Failed to initialize mailer: {e}',
                                        _time=now_epoch,
                                    )
                                    return

                            # Build recipient cert map for encryption
                            try:
                                all_rcpt_certs = get_all_recipient_certs(session_key)
                                rev_cert_map = {}
                                for r in rev_recipients:
                                    r_lower = r.lower()
                                    if r_lower in all_rcpt_certs:
                                        info = all_rcpt_certs[r_lower]
                                        if info.get('enabled', '1') not in ('0', 'false', 'False'):
                                            rev_cert_map[r_lower] = info.get('cert_pem', '')
                            except Exception:
                                rev_cert_map = {}

                            try:
                                result = mailer.send(
                                    to=rev_recipients,
                                    subject=rev_subject,
                                    body=rev_body,
                                    content_type='html',
                                    recipient_certs=rev_cert_map,
                                )
                                rev_status = 'sent_revoked'
                                rev_detail = result.get('message', 'OK')
                                notifications_sent += 1
                            except Exception as e:
                                rev_status = 'send_error'
                                rev_detail = str(e)
                                logger.error(f'Failed to send revocation notification for {entry_key}: {e}')

                            if rev_status == 'sent_revoked':
                                tracker[revoke_key] = {
                                    'last_milestone': 'revoked',
                                    'last_notified_epoch': str(now_epoch),
                                }
                                tracker_updated = True

                            yield self._event(
                                action=rev_status,
                                entry_key=entry_key,
                                milestone='revoked',
                                recipients=', '.join(rev_recipients),
                                subject=rev_subject,
                                cert_type=cert_type,
                                email=email,
                                crl_reason=content.get('crl_reason', ''),
                                crl_revocation_date=content.get('crl_revocation_date', ''),
                                detail=rev_detail,
                                _time=now_epoch,
                            )

            # ------ Expiry notification (existing logic) ------

            # Skip entries without expiry data or that are still valid
            if not days_str and status not in ('expired', 'expiring_soon'):
                continue

            try:
                days = int(days_str) if days_str else -1
            except (ValueError, TypeError):
                continue

            # Only process items within notification window
            milestone = _get_milestone(days)
            if milestone is None:
                continue

            # Check tracking
            track_info = tracker.get(entry_key, {})
            last_milestone = track_info.get('last_milestone', '')
            try:
                last_epoch = float(track_info.get('last_notified_epoch', 0))
            except (ValueError, TypeError):
                last_epoch = 0

            should_send, effective_milestone = _should_notify(
                days, last_milestone, last_epoch, now_epoch
            )

            if not should_send:
                continue

            # ----- Determine recipients -----
            recipients = list(admin_emails)

            # For cert types, optionally include the cert owner
            notify_user = (
                str(notify_on_expiry).lower() in ('true', '1', 'yes')
                and cert_type in ('recipient', 'sender')
                and email
            )
            if notify_user and email.lower() not in recipients:
                recipients.append(email.lower())

            if not recipients:
                continue

            # ----- Build email -----
            subject = _build_subject(effective_milestone, content)
            body_html = _build_body_html(effective_milestone, content)

            # ----- Send or dry-run -----
            if is_dryrun:
                yield self._event(
                    action='dryrun',
                    entry_key=entry_key,
                    milestone=effective_milestone,
                    recipients=', '.join(recipients),
                    subject=subject,
                    cert_type=cert_type,
                    email=email,
                    days_to_expiration=days_str,
                    status=status,
                    _time=now_epoch,
                )
                # Update tracker even in dryrun so repeated dryruns show progression
                tracker[entry_key] = {
                    'last_milestone': effective_milestone,
                    'last_notified_epoch': str(now_epoch),
                }
                tracker_updated = True
                continue

            # Initialize mailer on first actual send
            if mailer is None:
                try:
                    mailer = self._init_mailer(session_key, settings)
                except Exception as e:
                    yield self._event(
                        action='error',
                        detail=f'Failed to initialize mailer: {e}',
                        _time=now_epoch,
                    )
                    return

            # Build recipient cert map for encryption
            try:
                all_rcpt_certs = get_all_recipient_certs(session_key)
                rcpt_cert_map = {}
                for r in recipients:
                    r_lower = r.lower()
                    if r_lower in all_rcpt_certs:
                        info = all_rcpt_certs[r_lower]
                        if info.get('enabled', '1') not in ('0', 'false', 'False'):
                            rcpt_cert_map[r_lower] = info.get('cert_pem', '')
            except Exception:
                rcpt_cert_map = {}

            try:
                result = mailer.send(
                    to=recipients,
                    subject=subject,
                    body=body_html,
                    content_type='html',
                    recipient_certs=rcpt_cert_map,
                )
                send_status = 'sent'
                send_detail = result.get('message', 'OK')
                notifications_sent += 1
            except Exception as e:
                send_status = 'send_error'
                send_detail = str(e)
                logger.error(f'Failed to send expiry notification for {entry_key}: {e}')

            # Update tracker
            if send_status == 'sent':
                tracker[entry_key] = {
                    'last_milestone': effective_milestone,
                    'last_notified_epoch': str(now_epoch),
                }
                tracker_updated = True

            yield self._event(
                action=send_status,
                entry_key=entry_key,
                milestone=effective_milestone,
                recipients=', '.join(recipients),
                subject=subject,
                cert_type=cert_type,
                email=email,
                days_to_expiration=days_str,
                status=status,
                detail=send_detail,
                _time=now_epoch,
            )

        # ----------------------------------------------------------
        # 6. Save tracker
        # ----------------------------------------------------------
        if tracker_updated:
            self._save_tracker(tracker)

        # Summary event
        yield self._event(
            action='summary',
            detail=f'Processed {len(monitor_entries)} entries, sent {notifications_sent} notification(s).',
            _time=now_epoch,
        )

    # =============================================================
    # Helper methods
    # =============================================================

    def _event(self, **kwargs):
        """Build a result event dict for yielding."""
        return kwargs

    def _query_cert_monitor(self, session_key):
        """Query the smime_cert_monitor REST endpoint."""
        import splunk.rest as rest

        uri = (
            f'/servicesNS/nobody/{APP_NAME}/smime_cert_monitor'
            f'?output_mode=json&count=0'
        )
        response, content = rest.simpleRequest(
            uri, sessionKey=session_key, method='GET',
        )
        data = json.loads(content)
        return data.get('entry', [])

    def _init_mailer(self, session_key, settings):
        """Initialize the SmimeMailer with current settings."""
        smtp_password = get_smtp_password(session_key)
        oauth2_client_secret = get_oauth2_client_secret(session_key)
        hf_token = get_hf_token(session_key)
        sender_email = settings.get('sender_email', '')
        sender_cert_pem, sender_key_pem = get_sender_cert(sender_email, session_key)

        return SmimeMailer(
            smtp_host=settings.get('smtp_host', 'localhost'),
            smtp_port=int(settings.get('smtp_port', 25)),
            smtp_security=settings.get('smtp_security', 'starttls'),
            smtp_user=settings.get('smtp_user', ''),
            smtp_password=smtp_password or '',
            smtp_auth_type=settings.get('smtp_auth_type', 'basic'),
            oauth2_client_id=settings.get('oauth2_client_id', ''),
            oauth2_client_secret=oauth2_client_secret or '',
            oauth2_tenant_id=settings.get('oauth2_tenant_id', ''),
            oauth2_token_url=settings.get('oauth2_token_url', ''),
            oauth2_scope=settings.get('oauth2_scope', 'https://graph.microsoft.com/.default'),
            sender_email=sender_email,
            sender_name=settings.get('sender_name', ''),
            sender_cert_pem=sender_cert_pem,
            sender_key_pem=sender_key_pem,
            sign=settings.get('use_signing', 'true').lower() in ('true', '1', 'yes'),
            encrypt=settings.get('use_encryption', 'true').lower() in ('true', '1', 'yes'),
            use_hf_proxy=settings.get('use_hf_proxy', 'false'),
            hf_host=settings.get('hf_host', ''),
            hf_port=settings.get('hf_port', '8089'),
            hf_token=hf_token or '',
        )

    # ----- Tracking lookup I/O -----

    def _tracker_path(self):
        """Return the full path to the tracking CSV lookup file."""
        return os.path.join(app_dir, 'lookups', LOOKUP_FILENAME)

    def _load_tracker(self):
        """Load the notification tracking data from the CSV lookup.

        Returns a dict:  {entry_key: {'last_milestone': ..., 'last_notified_epoch': ...}}
        """
        tracker = {}
        path = self._tracker_path()
        if not os.path.isfile(path):
            return tracker

        try:
            with open(path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = row.get('entry_key', '')
                    if key:
                        tracker[key] = {
                            'last_milestone': row.get('last_milestone', ''),
                            'last_notified_epoch': row.get('last_notified_epoch', '0'),
                        }
        except Exception as e:
            logger.warning(f'Failed to read tracker file: {e}')

        return tracker

    def _save_tracker(self, tracker):
        """Persist the notification tracking data to the CSV lookup."""
        path = self._tracker_path()
        # Ensure lookups directory exists
        lookup_dir = os.path.dirname(path)
        os.makedirs(lookup_dir, exist_ok=True)

        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['entry_key', 'last_milestone', 'last_notified_epoch'],
                )
                writer.writeheader()
                for key, info in sorted(tracker.items()):
                    writer.writerow({
                        'entry_key': key,
                        'last_milestone': info.get('last_milestone', ''),
                        'last_notified_epoch': info.get('last_notified_epoch', '0'),
                    })
        except Exception as e:
            logger.error(f'Failed to write tracker file: {e}')


if __name__ == '__main__':
    dispatch(SmimeExpiryNotifyCommand, sys.argv, sys.stdin, sys.stdout, __name__)
