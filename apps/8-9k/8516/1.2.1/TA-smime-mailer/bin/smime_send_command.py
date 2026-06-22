#!/usr/bin/env python
"""
Splunk Custom Search Command: smimemail

Sends S/MIME signed and encrypted emails from SPL.
Validates that ALL specified recipients have valid public certificates
before attempting to send.

Usage in SPL:
    | smimemail to="user@example.com,user2@example.com"
               subject="Alert: $result.title$"
               body="<h1>Alert Details</h1><p>$result.description$</p>"
               content_type="html"
               cc="cc@example.com"
               bcc="bcc@example.com"
               body_field="message"
               attachment_fields="filename,filedata"

    Or as a streaming command on search results:
    | search index=notable | smimemail to="user@example.com" subject="Notable" body_field="search_name"
"""

import csv
import json
import logging
import os
import sys
import traceback

# Setup paths
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
lib_dir = os.path.join(app_dir, 'lib')
sys.path.insert(0, lib_dir)
sys.path.insert(0, os.path.join(app_dir, 'bin'))

from splunklib.searchcommands import (
    dispatch, StreamingCommand, Configuration, Option, validators
)
import splunklib.client as client

from splunk_config_helper import (
    get_smtp_settings, get_smtp_password, get_oauth2_client_secret, get_hf_token,
    validate_all_recipients, build_recipient_cert_map, get_sender_cert
)
from smime_mailer_lib import SmimeMailer

logger = logging.getLogger('smime_mailer.command')


@Configuration()
class SmimeMailCommand(StreamingCommand):
    """
    S/MIME Email Custom Search Command.
    
    Sends an S/MIME signed/encrypted email. If used as a streaming command,
    one email is sent per event (or you can use body_field to pull the body
    from a field). All recipients are validated for certificates before sending.
    """

    to = Option(
        doc='Comma-separated list of recipient email addresses.',
        require=True,
    )
    cc = Option(
        doc='Comma-separated CC email addresses.',
        require=False,
        default='',
    )
    bcc = Option(
        doc='Comma-separated BCC email addresses.',
        require=False,
        default='',
    )
    subject = Option(
        doc='Email subject line. Supports $field$ token replacement.',
        require=True,
    )
    body = Option(
        doc='Email body text. Supports $field$ token replacement.',
        require=False,
        default='',
    )
    body_field = Option(
        doc='Field name to use as the email body (overrides body).',
        require=False,
        default='',
    )
    content_type = Option(
        doc='Content type: html or plain.',
        require=False,
        default='html',
    )
    attachment_fields = Option(
        doc='Comma-separated field names to include as attachments.',
        require=False,
        default='',
    )
    send_per_event = Option(
        doc='If true, sends one email per event. If false (default), sends one email total.',
        require=False,
        default='false',
    )
    skip_validation = Option(
        doc='If true, skip certificate validation (NOT recommended).',
        require=False,
        default='false',
    )

    def __init__(self):
        super().__init__()
        self._smtp_settings = None
        self._mailer = None
        self._recipients_validated = False
        self._recipient_cert_map = None
        self._sent_count = 0

    def _init_mailer(self):
        """Initialize the S/MIME mailer with Splunk configuration."""
        if self._mailer:
            return

        session_key = self.metadata.searchinfo.session_key
        settings = get_smtp_settings(session_key)
        smtp_password = get_smtp_password(session_key)
        oauth2_client_secret = get_oauth2_client_secret(session_key)
        hf_token = get_hf_token(session_key)

        sender_email = settings.get('sender_email', '')
        sender_cert_pem, sender_key_pem = get_sender_cert(sender_email, session_key)

        self._smtp_settings = settings
        self._mailer = SmimeMailer(
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

    def _validate_and_load_certs(self, all_recipients):
        """Validate all recipients have certificates and load them."""
        if self._recipients_validated:
            return

        session_key = self.metadata.searchinfo.session_key
        verify = self._smtp_settings.get('verify_recipient_certs', 'true').lower() in ('true', '1', 'yes')
        skip = self.skip_validation.lower() in ('true', '1', 'yes')

        if verify and not skip:
            all_valid, details = validate_all_recipients(all_recipients, session_key)
            if not all_valid:
                missing = [email for email, info in details.items() if not info.get('has_cert') or not info.get('enabled')]
                raise RuntimeError(
                    f'Certificate validation failed. The following recipients are missing '
                    f'valid S/MIME certificates: {", ".join(missing)}. '
                    f'Please add their certificates in the S/MIME Mailer configuration page.'
                )

        self._recipient_cert_map = build_recipient_cert_map(all_recipients, session_key)
        self._recipients_validated = True

    def _resolve_tokens(self, template, record):
        """Replace $field$ tokens in a string with values from the record."""
        result = template
        for key, value in record.items():
            token = f'${key}$'
            if token in result:
                result = result.replace(token, str(value))
        return result

    def stream(self, records):
        """
        Process search results and send emails.
        """
        try:
            self._init_mailer()
        except Exception as e:
            logger.error(f'Failed to initialize mailer: {e}')
            self.write_error('S/MIME Mailer initialization failed: ' + str(e).replace('{', '{{').replace('}', '}}'))
            return

        # Parse recipients
        to_list = [t.strip() for t in self.to.split(',') if t.strip()]
        cc_list = [c.strip() for c in self.cc.split(',') if c.strip()] if self.cc else []
        bcc_list = [b.strip() for b in self.bcc.split(',') if b.strip()] if self.bcc else []
        all_recipients = to_list + cc_list + bcc_list

        # Validate certificates
        try:
            self._validate_and_load_certs(all_recipients)
        except RuntimeError as e:
            logger.error(str(e))
            self.write_error(str(e).replace('{', '{{').replace('}', '}}'))
            return

        send_per_event = self.send_per_event.lower() in ('true', '1', 'yes')
        collected_bodies = []

        for record in records:
            if send_per_event:
                # Send one email per event
                body = self._get_body(record)
                subject = self._resolve_tokens(self.subject, record)

                try:
                    result = self._mailer.send(
                        to=to_list,
                        subject=subject,
                        body=body,
                        content_type=self.content_type,
                        cc=cc_list,
                        bcc=bcc_list,
                        recipient_certs=self._recipient_cert_map,
                    )
                    record['smime_status'] = 'sent'
                    record['smime_message_id'] = result.get('message_id', '')
                    self._sent_count += 1
                except Exception as e:
                    record['smime_status'] = 'error'
                    record['smime_error'] = str(e)
                    logger.error(f'Failed to send email: {e}')
            else:
                collected_bodies.append(record)
                record['smime_status'] = 'queued'

            yield record

        # If not send_per_event, send one consolidated email
        if not send_per_event and collected_bodies:
            body = self._get_body(collected_bodies[0])
            subject = self._resolve_tokens(self.subject, collected_bodies[0])

            try:
                result = self._mailer.send(
                    to=to_list,
                    subject=subject,
                    body=body,
                    content_type=self.content_type,
                    cc=cc_list,
                    bcc=bcc_list,
                    recipient_certs=self._recipient_cert_map,
                )
                self._sent_count += 1
                logger.info(f'Consolidated email sent: {result}')
            except Exception as e:
                logger.error(f'Failed to send consolidated email: {e}')
                self.write_error('Failed to send email: ' + str(e).replace('{', '{{').replace('}', '}}'))

    def _get_body(self, record):
        """Get the email body from field or template."""
        if self.body_field and self.body_field in record:
            return str(record[self.body_field])
        elif self.body:
            return self._resolve_tokens(self.body, record)
        else:
            # Default: format the record as a table
            lines = ['<table border="1" cellpadding="4" cellspacing="0">']
            for k, v in record.items():
                if not k.startswith('_') and not k.startswith('smime_'):
                    lines.append(f'<tr><td><b>{k}</b></td><td>{v}</td></tr>')
            lines.append('</table>')
            return '\n'.join(lines)


if __name__ == '__main__':
    dispatch(SmimeMailCommand, sys.argv, sys.stdin, sys.stdout, __name__)
