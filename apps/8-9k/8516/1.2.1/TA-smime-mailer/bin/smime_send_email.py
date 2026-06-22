#!/usr/bin/env python
"""
Splunk Alert Action: smime_send_email

Sends S/MIME signed and encrypted email as an alert action.
Can be triggered from Splunk Enterprise Security notable events,
correlation searches, or standard Splunk alerts.

All recipients are validated for S/MIME certificates before sending.
"""

import csv
import gzip
import html
import io
import json
import logging
import os
import sys
import traceback
from urllib.parse import quote, urlparse, urlunparse

# Setup paths
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
lib_dir = os.path.join(app_dir, 'lib')
sys.path.insert(0, lib_dir)
sys.path.insert(0, os.path.join(app_dir, 'bin'))

from splunk_config_helper import (
    get_smtp_settings, get_smtp_password, get_oauth2_client_secret, get_hf_token,
    validate_all_recipients, build_recipient_cert_map, get_sender_cert
)
from smime_mailer_lib import SmimeMailer

LOG_FILE = os.path.join(os.environ.get('SPLUNK_HOME', '/opt/splunk'),
                        'var', 'log', 'splunk', 'smime_send_email_alert.log')

# Do NOT rely on basicConfig — Splunk's Python environment may have already
# configured root-level handlers, making basicConfig a silent no-op.
logger = logging.getLogger('smime_mailer.alert')
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    try:
        _fh = logging.FileHandler(LOG_FILE)
        _fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(_fh)
    except Exception:
        # Last resort: write to stderr so Splunk captures it in splunkd.log
        logger.addHandler(logging.StreamHandler(sys.stderr))


def parse_alert_payload(payload_file):
    """Parse the alert action payload from a UTF-8 JSON file."""
    with open(payload_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def _load_payload_from_stdin():
    """Try to read the JSON payload piped to stdin (ES/sendalert fallback)."""
    try:
        data = sys.stdin.read()
        if data.strip():
            return json.loads(data)
    except Exception:
        pass
    return None


def get_results(payload):
    """Read search results from the results file referenced in the payload."""
    results_file = payload.get('results_file', '')
    if not results_file or not os.path.exists(results_file):
        return []

    results = []
    try:
        if results_file.endswith('.gz'):
            opener = gzip.open(results_file, 'rt')
        else:
            opener = open(results_file, 'r')

        with opener as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
    except Exception as e:
        logger.error(f'Failed to read results: {e}')

    return results


def resolve_tokens(template, result, html_escape=False):
    """Replace $result.field$ tokens with actual values.

    Args:
        html_escape: when True, HTML-escape each substituted value so that
            field contents (e.g. raw Windows XML events) are not interpreted
            as HTML markup inside the email body.
    """
    if not template or not result:
        return template or ''

    output = template
    for key, value in result.items():
        safe = html.escape(str(value)) if html_escape else str(value)
        # Support both $result.field$ and $field$ patterns
        output = output.replace(f'$result.{key}$', safe)
        output = output.replace(f'${key}$', safe)
    return output


def format_results_as_csv(results):
    """Convert search results to CSV bytes for attachment."""
    if not results:
        return None

    output = io.StringIO()
    if results:
        writer = csv.DictWriter(output, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    return output.getvalue().encode('utf-8')


def format_results_as_html_table(results, max_rows=50):
    """Convert search results to an HTML table for the email body."""
    if not results:
        return '<p>No results.</p>'

    html = ['<table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;">']
    # Header
    html.append('<thead><tr>')
    for key in results[0].keys():
        if not key.startswith('_'):
            html.append(f'<th style="background:#f0f0f0;padding:8px;">{key}</th>')
    html.append('</tr></thead>')

    # Rows
    html.append('<tbody>')
    for i, row in enumerate(results[:max_rows]):
        bg = '#ffffff' if i % 2 == 0 else '#f9f9f9'
        html.append(f'<tr style="background:{bg};">')
        for key, value in row.items():
            if not key.startswith('_'):
                html.append(f'<td style="padding:6px;">{value}</td>')
        html.append('</tr>')
    html.append('</tbody></table>')

    if len(results) > max_rows:
        html.append(f'<p><i>Showing {max_rows} of {len(results)} results.</i></p>')

    return '\n'.join(html)


def format_results_as_raw_html(results, max_rows=50):
    """Format results as raw event display in HTML."""
    if not results:
        return '<p>No results.</p>'

    html = []
    for i, row in enumerate(results[:max_rows]):
        raw = row.get('_raw', '')
        if raw:
            html.append(f'<pre style="background:#f5f5f5;padding:8px;margin:4px 0;border:1px solid #ddd;">{raw}</pre>')
        else:
            parts = [f'{k}={v}' for k, v in row.items() if not k.startswith('_')]
            html.append(f'<pre style="background:#f5f5f5;padding:8px;margin:4px 0;border:1px solid #ddd;">{" ".join(parts)}</pre>')

    if len(results) > max_rows:
        html.append(f'<p><i>Showing {max_rows} of {len(results)} results.</i></p>')

    return '\n'.join(html)


def format_results_as_plain_text(results, fmt='table', max_rows=50):
    """Format results as plain text."""
    if not results:
        return 'No results.'

    if fmt == 'raw':
        lines = []
        for row in results[:max_rows]:
            raw = row.get('_raw', '')
            if raw:
                lines.append(raw)
            else:
                lines.append(' '.join(f'{k}={v}' for k, v in row.items() if not k.startswith('_')))
        return '\n'.join(lines)

    # Table format
    visible = {k for k in results[0].keys() if not k.startswith('_')}
    cols = [k for k in results[0].keys() if k in visible]

    if not cols:
        return 'No visible fields.'

    # Calculate column widths
    widths = {c: len(c) for c in cols}
    for row in results[:max_rows]:
        for c in cols:
            widths[c] = max(widths[c], len(str(row.get(c, ''))))

    # Header
    header = ' | '.join(c.ljust(widths[c]) for c in cols)
    separator = '-+-'.join('-' * widths[c] for c in cols)
    lines = [header, separator]

    for row in results[:max_rows]:
        lines.append(' | '.join(str(row.get(c, '')).ljust(widths[c]) for c in cols))

    if len(results) > max_rows:
        lines.append(f'\n[Showing {max_rows} of {len(results)} results]')

    return '\n'.join(lines)


def _build_incident_review_link(server_uri, alert_name, trigger_time):
    """
    Build an ES Incident Review URL for the given alert, with a ±24 h time
    window centred on the trigger time.

    Example result:
      https://splunk.example.com:8000/app/SplunkEnterpriseSecuritySuite/incident_review
        ?earliest=1747109003&latest=1747281803&search=My+Rule+Name&queueId=default
    """
    one_day = 86400  # seconds
    try:
        ts = float(trigger_time)
        earliest = int(ts - one_day)
        latest = int(ts + one_day)
        time_part = f'earliest={earliest}&latest={latest}'
    except (TypeError, ValueError):
        # trigger_time missing or non-numeric — use a relative 48 h window
        time_part = 'earliest=-24h%40h&latest=now'

    base = server_uri.rstrip('/')
    return (
        f'{base}/app/SplunkEnterpriseSecuritySuite/incident_review'
        f'?{time_part}&search={quote(alert_name)}&queueId=default'
    )


def run_alert_action():
    """Main entry point for the alert action."""
    logger.info(f'smime_send_email invoked: argv={sys.argv!r}')

    payload = None

    # Primary path: Splunk passes the JSON payload file path as sys.argv[1].
    if len(sys.argv) >= 2:
        payload_file = sys.argv[1]
        if os.path.isfile(payload_file):
            try:
                payload = parse_alert_payload(payload_file)
                logger.info(f'Loaded payload from file: {payload_file}')
            except Exception as e:
                msg = (
                    f'Failed to parse payload file {payload_file!r}: '
                    f'{type(e).__name__}: {e}\n{traceback.format_exc()}'
                )
                logger.error(msg)
                sys.stderr.write(f'ERROR smime_send_email: {msg}\n')
        else:
            logger.warning(
                f'sys.argv[1]={payload_file!r} is not a file. '
                f'Falling back to stdin. Full argv: {sys.argv!r}'
            )

    # Fallback: some Splunk ES / sendalert invocations pipe the payload via stdin.
    if payload is None:
        logger.info('Attempting to read payload from stdin')
        payload = _load_payload_from_stdin()
        if payload is not None:
            logger.info('Loaded payload from stdin')

    if payload is None:
        msg = f'No valid alert payload found. argv={sys.argv!r}'
        logger.error(msg)
        sys.stderr.write(f'ERROR smime_send_email: {msg}\n')
        sys.exit(2)

    # Extract configuration from the alert action params
    config = payload.get('configuration', {})
    session_key = payload.get('session_key', '')

    to_str = config.get('to', '')
    cc_str = config.get('cc', '')
    bcc_str = config.get('bcc', '')
    subject = config.get('subject', 'Splunk Alert: $name$')
    body = config.get('body', "The alert condition for '$name$' was triggered.")
    content_type = config.get('content_type', 'html')
    priority = config.get('priority', '3')
    result_format = config.get('format', 'table')

    # Include options (ES-compatible)
    include_link_to_alert = config.get('include_link_to_alert', 'true').lower() in ('true', '1', 'yes')
    include_link_to_results = config.get('include_link_to_results', 'true').lower() in ('true', '1', 'yes')
    include_search_string = config.get('include_search_string', 'false').lower() in ('true', '1', 'yes')
    include_inline = config.get('include_inline', 'false').lower() in ('true', '1', 'yes')
    include_trigger_condition = config.get('include_trigger_condition', 'false').lower() in ('true', '1', 'yes')
    include_trigger_time = config.get('include_trigger_time', 'false').lower() in ('true', '1', 'yes')
    attach_csv = config.get('attach_csv', 'false').lower() in ('true', '1', 'yes')
    attach_pdf = config.get('attach_pdf', 'false').lower() in ('true', '1', 'yes')

    # Legacy compatibility: old include_results param → attach_csv
    if config.get('include_results', 'false').lower() in ('true', '1', 'yes'):
        attach_csv = True

    if not to_str:
        logger.error('No recipients specified in alert action')
        sys.exit(3)

    # Parse recipients
    to_list = [t.strip() for t in to_str.split(',') if t.strip()]
    cc_list = [c.strip() for c in cc_str.split(',') if c.strip()] if cc_str else []
    bcc_list = [b.strip() for b in bcc_str.split(',') if b.strip()] if bcc_str else []
    all_recipients = to_list + cc_list + bcc_list

    logger.info(f'Recipients: to={to_list}, cc={cc_list}, bcc={bcc_list}')

    # Load SMTP settings first so we can conditionally fetch only needed credentials
    settings = get_smtp_settings(session_key)
    sender_email = settings.get('sender_email', '')
    smtp_auth_type = settings.get('smtp_auth_type', 'basic')
    smtp_user = settings.get('smtp_user', '')
    use_signing = settings.get('use_signing', 'true').lower() in ('true', '1', 'yes')
    use_hf_proxy = settings.get('use_hf_proxy', 'false').lower() in ('true', '1', 'yes')

    # Load only the credentials that are actually needed to avoid spurious
    # "not found" errors when a feature is disabled.
    smtp_password = (
        get_smtp_password(session_key)
        if smtp_auth_type == 'basic' and smtp_user
        else None
    )
    oauth2_client_secret = (
        get_oauth2_client_secret(session_key)
        if smtp_auth_type == 'oauth2'
        else None
    )
    hf_token = get_hf_token(session_key) if use_hf_proxy else None

    # Load sender certificate only when signing is enabled
    sender_cert_pem, sender_key_pem = None, None
    if use_signing:
        sender_cert_pem, sender_key_pem = get_sender_cert(sender_email, session_key)
        if not sender_cert_pem:
            logger.warning(f'Signing enabled but sender certificate PEM not found for {sender_email}')
        elif not sender_key_pem:
            logger.warning(f'Signing enabled but sender private key not found for {sender_email}')
        else:
            logger.info(f'Sender signing cert and key loaded for {sender_email}')

    # -----------------------------------------------------------------
    # VALIDATE ALL RECIPIENTS HAVE CERTIFICATES
    # -----------------------------------------------------------------
    verify = settings.get('verify_recipient_certs', 'true').lower() in ('true', '1', 'yes')
    if verify:
        all_valid, details = validate_all_recipients(all_recipients, session_key)
        if not all_valid:
            missing = [
                email for email, info in details.items()
                if not info.get('has_cert') or not info.get('enabled')
            ]
            error_msg = (
                f'S/MIME certificate validation failed. Missing certificates for: '
                f'{", ".join(missing)}. Email NOT sent.'
            )
            logger.error(error_msg)
            # Write error to Splunk internal logs for visibility in ES
            sys.stderr.write(f'ERROR {error_msg}\n')
            sys.exit(4)

    logger.info('All recipient certificates validated successfully')

    # Build recipient cert map
    recipient_cert_map = build_recipient_cert_map(all_recipients, session_key)

    # Load search results
    results = get_results(payload)

    # Resolve tokens in subject and body using the first result
    # Also resolve alert-level tokens from the payload
    first_result = results[0] if results else {}

    # Build alert metadata tokens
    alert_name = payload.get('search_name', config.get('name', ''))
    alert_app = payload.get('app', '')
    alert_owner = payload.get('owner', '')
    alert_sid = payload.get('sid', '')
    server_uri = payload.get('server_uri', payload.get('results_link', '').split('/app/')[0] if '/app/' in payload.get('results_link', '') else '')
    results_link = payload.get('results_link', '')

    # Override link base URL with the admin-configured external hostname
    # (Splunk's own server_uri is often an internal address unreachable by recipients)
    splunk_hostname = settings.get('splunk_hostname', '').rstrip('/')
    if splunk_hostname:
        hostname_base = splunk_hostname if '://' in splunk_hostname else f'https://{splunk_hostname}'
        h = urlparse(hostname_base)
        server_uri = f'{h.scheme}://{h.netloc}'
        if results_link:
            try:
                r = urlparse(results_link)
                results_link = urlunparse((h.scheme, h.netloc, r.path, r.params, r.query, r.fragment))
            except Exception:
                pass  # Keep original if parse fails
    search_string = payload.get('search', config.get('search', ''))
    trigger_time = payload.get('trigger_time', '')

    # Add alert-level token values to first_result for resolution
    alert_tokens = {
        'name': alert_name,
        'app': alert_app,
        'owner': alert_owner,
        'sid': alert_sid,
        'results_link': results_link,
        'server_uri': server_uri,
        'search_string': search_string,
        'trigger_time': trigger_time,
    }
    merged_tokens = {**alert_tokens, **first_result}

    subject = resolve_tokens(subject, merged_tokens)
    # For HTML content type, html-escape the *values* substituted from Splunk
    # fields (e.g. $result.src_ip$) so that raw field data cannot inject HTML.
    # The body template itself is preserved as-is, allowing users to write HTML
    # markup directly (e.g. <b>, <table>, <tr>, <td>, <u>, <i>, <a href="...">).
    # For plain text, resolve without escaping.
    body = resolve_tokens(body, merged_tokens, html_escape=(content_type == 'html'))

    logger.debug(f'[1.2.1] content_type={content_type!r} body_snippet={(body[:120] if body else "(empty)")!r}')

    # Build the email body with included sections
    if content_type == 'html':
        # The body template supports HTML markup. Token values have already been
        # html-escaped by resolve_tokens above. Newlines are converted to <br>
        # for correct rendering of plain-text lines that lack explicit HTML tags.
        body_html = body.replace('\r\n', '\n').replace('\n', '<br>\n') if body else ''
        body_parts = [body_html] if body_html else []

        if include_trigger_time and trigger_time:
            body_parts.append(f'<p><b>Trigger Time:</b> {trigger_time}</p>')

        if include_trigger_condition:
            trigger_cond = config.get('trigger_condition', '')
            if trigger_cond:
                body_parts.append(f'<p><b>Trigger Condition:</b> {trigger_cond}</p>')

        if include_search_string and search_string:
            body_parts.append(f'<p><b>Search:</b> <code>{search_string}</code></p>')

        if include_link_to_alert and alert_name and server_uri:
            body_parts.append(f'<p><a href="{_build_incident_review_link(server_uri, alert_name, trigger_time)}">View Alert</a></p>')

        if include_link_to_results and results_link:
            body_parts.append(f'<p><a href="{results_link}">View Results</a></p>')

        if include_inline and results:
            body_parts.append('<hr>')
            body_parts.append('<h3>Search Results</h3>')
            if result_format == 'raw':
                body_parts.append(format_results_as_raw_html(results))
            else:
                body_parts.append(format_results_as_html_table(results))

        body = '\n'.join(body_parts)
    else:
        # Plain text body
        body_parts = [body] if body else []

        if include_trigger_time and trigger_time:
            body_parts.append(f'\nTrigger Time: {trigger_time}')

        if include_trigger_condition:
            trigger_cond = config.get('trigger_condition', '')
            if trigger_cond:
                body_parts.append(f'\nTrigger Condition: {trigger_cond}')

        if include_search_string and search_string:
            body_parts.append(f'\nSearch: {search_string}')

        if include_link_to_alert and alert_name and server_uri:
            body_parts.append(f'\nView Alert: {_build_incident_review_link(server_uri, alert_name, trigger_time)}')

        if include_link_to_results and results_link:
            body_parts.append(f'\nView Results: {results_link}')

        if include_inline and results:
            body_parts.append('\n--- Search Results ---')
            body_parts.append(format_results_as_plain_text(results, result_format))

        body = '\n'.join(body_parts)

    # Build attachments
    attachments = []
    if attach_csv and results:
        csv_data = format_results_as_csv(results)
        if csv_data:
            attachments.append({
                'filename': 'search_results.csv',
                'data': csv_data,
                'mime_type': 'text/csv',
            })

    # Note: PDF attachment requires Splunk's PDF generation service.
    # If enabled but not available, log a warning.
    if attach_pdf:
        logger.warning('PDF attachment requested but PDF generation is not yet supported in this version. Skipping.')

    # Initialize mailer
    mailer = SmimeMailer(
        smtp_host=settings.get('smtp_host', 'localhost'),
        smtp_port=int(settings.get('smtp_port', 25)),
        smtp_security=settings.get('smtp_security', 'starttls'),
        smtp_auth_type=settings.get('smtp_auth_type', 'basic'),
        smtp_user=settings.get('smtp_user', ''),
        smtp_password=smtp_password or '',
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

    # Send the email
    try:
        result = mailer.send(
            to=to_list,
            subject=subject,
            body=body,
            content_type=content_type,
            cc=cc_list,
            bcc=bcc_list,
            attachments=attachments,
            recipient_certs=recipient_cert_map,
            priority=priority,
        )
        logger.info(f'Email sent successfully: {result}')
        print(f'S/MIME email sent to {len(all_recipients)} recipient(s)')
    except Exception as e:
        logger.error(f'Failed to send email: {e}\n{traceback.format_exc()}')
        sys.stderr.write(f'ERROR Failed to send S/MIME email: {e}\n')
        sys.exit(5)


if __name__ == '__main__':
    run_alert_action()
