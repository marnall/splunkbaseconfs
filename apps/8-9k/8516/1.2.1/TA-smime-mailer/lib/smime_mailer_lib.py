"""
S/MIME email construction and sending library.

Supports:
  - S/MIME signing (using sender's private key + cert)
  - S/MIME encryption (using recipient public certs)
  - Both signing + encryption
  - SMTP (port 25), SMTP+STARTTLS (port 25/587), SMTPS (port 465)
  - Basic (username/password) and OAuth2 (XOAUTH2) authentication
"""

import email
import email.mime.multipart
import email.mime.text
import email.mime.base
import email.mime.application
import email.utils
import json
import smtplib
import ssl
import os
import io
import tempfile
import logging

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

# We use asn1crypto for building S/MIME PKCS#7 ASN.1 structures
# since the cryptography library does not provide high-level S/MIME support.
# Signing/encryption operations use the cryptography library (Rust backend).
from asn1crypto import cms, core, algos, x509 as asn1_x509, pem as asn1_pem

logger = logging.getLogger('smime_mailer')


class _ExactBytesMessage:
    """
    Lightweight message wrapper that returns pre-built raw MIME bytes.

    Used by _sign_message to guarantee the exact bytes that were hashed
    appear in the final message, preventing re-serialization issues.
    Supports the subset of email.message.Message API used by
    _encrypt_message, _graph_send, and _smtp_send.
    """

    def __init__(self, raw_bytes):
        self._raw = raw_bytes
        # Parse headers from the raw bytes for header access
        self._parsed = email.message_from_bytes(raw_bytes)

    def as_bytes(self, *args, **kwargs):
        return self._raw

    def as_string(self, *args, **kwargs):
        return self._raw.decode('utf-8', errors='replace')

    def __getitem__(self, name):
        return self._parsed[name]

    def __setitem__(self, name, val):
        self._parsed[name] = val

    def __delitem__(self, name):
        del self._parsed[name]

    def __contains__(self, name):
        return name in self._parsed

    def get(self, name, failobj=None):
        return self._parsed.get(name, failobj)

    def get_all(self, name, failobj=None):
        return self._parsed.get_all(name, failobj)

    def keys(self):
        return self._parsed.keys()

    def items(self):
        return self._parsed.items()


class SmimeMailer:
    """
    Construct and send S/MIME signed and/or encrypted emails.
    """

    def __init__(self, smtp_host='localhost', smtp_port=25, smtp_security='starttls',
                 smtp_user=None, smtp_password=None, smtp_auth_type='basic',
                 oauth2_client_id=None, oauth2_client_secret=None,
                 oauth2_tenant_id=None, oauth2_token_url=None,
                 oauth2_scope=None,
                 sender_email=None, sender_name=None,
                 sender_cert_pem=None, sender_key_pem=None,
                 sign=True, encrypt=True,
                 use_hf_proxy=False, hf_host=None, hf_port=8089, hf_token=None):
        """
        Args:
            smtp_host:            SMTP server hostname.
            smtp_port:            SMTP server port (25, 465, 587, etc.).
            smtp_security:        'none', 'starttls', or 'ssl'.
            smtp_user:            SMTP auth username (optional).
            smtp_password:        SMTP auth password (optional, for basic auth).
            smtp_auth_type:       'basic' or 'oauth2'.
            oauth2_client_id:     OAuth2 client ID (for oauth2 auth).
            oauth2_client_secret: OAuth2 client secret (for oauth2 auth).
            oauth2_tenant_id:     Azure AD tenant ID (for oauth2 auth).
            oauth2_token_url:     OAuth2 token endpoint URL.
            oauth2_scope:         OAuth2 scope(s).
            sender_email:         From email address.
            sender_name:          From display name.
            sender_cert_pem:      PEM str of sender's signing certificate.
            sender_key_pem:       PEM str of sender's private key.
            sign:                 Whether to S/MIME-sign the message.
            encrypt:              Whether to S/MIME-encrypt the message.
            use_hf_proxy:         Route delivery through a Heavy Forwarder.
            hf_host:              HF hostname or IP.
            hf_port:              HF Splunk management port (default 8089).
            hf_token:             Bearer token for HF REST authentication.
        """
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.smtp_security = self._normalize_smtp_security(smtp_security, self.smtp_port)
        self.smtp_auth_type = smtp_auth_type or 'basic'
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.oauth2_client_id = oauth2_client_id
        self.oauth2_client_secret = oauth2_client_secret
        self.oauth2_tenant_id = oauth2_tenant_id
        self.oauth2_token_url = oauth2_token_url
        self.oauth2_scope = oauth2_scope or 'https://graph.microsoft.com/.default'
        self.sender_email = sender_email
        self.sender_name = sender_name or sender_email
        self.sender_cert_pem = sender_cert_pem
        self.sender_key_pem = sender_key_pem
        self.sign = sign
        self.encrypt = encrypt
        self.use_hf_proxy = str(use_hf_proxy).lower() in ('true', '1', 'yes')
        self.hf_host = hf_host
        self.hf_port = int(hf_port) if hf_port else 8089
        self.hf_token = hf_token

    @staticmethod
    def _normalize_smtp_security(smtp_security, smtp_port):
        security = (smtp_security or 'starttls').strip().lower()
        if security == 'submission':
            security = 'starttls'
        return security

    def send(self, to, subject, body, content_type='html',
             cc=None, bcc=None, attachments=None, recipient_certs=None,
             priority=None):
        """
        Build and send an S/MIME email.
        
        Args:
            to:              list of recipient email addresses.
            subject:         email subject.
            body:            email body text.
            content_type:    'html' or 'plain'.
            cc:              list of CC addresses (optional).
            bcc:             list of BCC addresses (optional).
            attachments:     list of dicts {'filename': str, 'data': bytes, 'mime_type': str}.
            recipient_certs: dict {email: pem_string} for encryption.
        
        Returns:
            dict: {'success': bool, 'message': str, 'message_id': str}
        """
        if not to:
            raise ValueError('At least one recipient is required')
        if not self.sender_email:
            raise ValueError('Sender email is required')

        # Normalize
        if isinstance(to, str):
            to = [t.strip() for t in to.split(',') if t.strip()]
        cc = cc or []
        if isinstance(cc, str):
            cc = [c.strip() for c in cc.split(',') if c.strip()]
        bcc = bcc or []
        if isinstance(bcc, str):
            bcc = [b.strip() for b in bcc.split(',') if b.strip()]
        attachments = attachments or []
        recipient_certs = recipient_certs or {}

        # Build MIME message
        msg = self._build_mime(to, cc, subject, body, content_type, attachments, priority)

        # ----- CRL revocation checks (warn only, never block) -----
        try:
            from smime_cert_utils import check_crl_revocation
            # Check sender cert
            if self.sender_cert_pem:
                crl_res = check_crl_revocation(self.sender_cert_pem, timeout=8)
                if crl_res.get('revoked'):
                    logger.warning(
                        f'CRL WARNING: Sender certificate for {self.sender_email} '
                        f'has been REVOKED (reason={crl_res.get("reason", "unspecified")}, '
                        f'date={crl_res.get("revocation_date", "unknown")}, '
                        f'crl={crl_res.get("crl_url", "")}). '
                        f'Email will still be sent.'
                    )
                elif crl_res.get('error'):
                    logger.debug(
                        f'CRL check for sender {self.sender_email}: {crl_res["error"]}'
                    )
            # Check recipient certs
            for rcpt_email, rcpt_pem in recipient_certs.items():
                try:
                    crl_res = check_crl_revocation(rcpt_pem, timeout=8)
                    if crl_res.get('revoked'):
                        logger.warning(
                            f'CRL WARNING: Recipient certificate for {rcpt_email} '
                            f'has been REVOKED (reason={crl_res.get("reason", "unspecified")}, '
                            f'date={crl_res.get("revocation_date", "unknown")}, '
                            f'crl={crl_res.get("crl_url", "")}). '
                            f'Email will still be sent.'
                        )
                except Exception:
                    pass
        except ImportError:
            logger.debug('smime_cert_utils not available for CRL check during send')
        except Exception as e:
            logger.debug(f'CRL check during send failed: {e}')

        # Sign if requested
        if self.sign:
            if self.sender_cert_pem and self.sender_key_pem:
                msg = self._sign_message(msg)
            else:
                missing = []
                if not self.sender_cert_pem:
                    missing.append('sender_cert_pem')
                if not self.sender_key_pem:
                    missing.append('sender_key_pem')
                logger.error(
                    f'Signing requested but skipped — missing: {", ".join(missing)}. '
                    f'Check sender certificate configuration for {self.sender_email}. '
                    f'If you recently upgraded TA-smime-mailer, the private key stored '
                    f'in Splunk credential store (storage/passwords) may have been lost. '
                    f'Re-upload the sender certificate to restore it.'
                )

        # Encrypt if requested
        if self.encrypt and recipient_certs:
            all_recipients = to + cc + bcc
            msg = self._encrypt_message(msg, all_recipients, recipient_certs)

        # Send via HF proxy, Graph API, or direct SMTP
        all_rcpts = to + cc + bcc
        if self.use_hf_proxy and self.hf_host:
            return self._hf_proxy_send(msg, all_rcpts)
        elif self.smtp_auth_type == 'oauth2' and self.oauth2_client_id:
            return self._graph_send(msg, all_rcpts)
        else:
            return self._smtp_send(msg, all_rcpts)

    def _build_mime(self, to, cc, subject, body, content_type, attachments, priority=None):
        """Build a standard MIME email message."""
        if attachments:
            msg = email.mime.multipart.MIMEMultipart('mixed')
            body_part = email.mime.text.MIMEText(body, content_type, 'utf-8')
            msg.attach(body_part)
            for att in attachments:
                part = email.mime.base.MIMEBase(
                    *(att.get('mime_type', 'application/octet-stream').split('/', 1))
                )
                part.set_payload(att['data'])
                email.encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment',
                                filename=att.get('filename', 'attachment'))
                msg.attach(part)
        else:
            msg = email.mime.text.MIMEText(body, content_type, 'utf-8')

        msg['From'] = email.utils.formataddr((self.sender_name, self.sender_email))
        msg['To'] = ', '.join(to)
        if cc:
            msg['Cc'] = ', '.join(cc)
        msg['Subject'] = subject
        msg['Message-ID'] = email.utils.make_msgid(domain=self.sender_email.split('@')[-1])
        msg['Date'] = email.utils.formatdate(localtime=True)
        msg['MIME-Version'] = '1.0'

        # Priority header (1=highest, 3=normal, 5=lowest)
        if priority and str(priority) != '3':
            msg['X-Priority'] = str(priority)
            importance_map = {'1': 'high', '2': 'high', '4': 'low', '5': 'low'}
            if str(priority) in importance_map:
                msg['Importance'] = importance_map[str(priority)]

        return msg

    def _sign_message(self, msg):
        """
        S/MIME sign the message using PKCS#7 detached SignedData.
        Returns a multipart/signed MIME message per RFC 5751.

        The message is built as raw bytes with CRLF line endings to
        guarantee the exact bytes that were hashed appear in the final
        message. This avoids re-serialization issues where Python's
        email module could alter whitespace, header folding, etc.
        """
        try:
            import base64

            # Load cert and key via cryptography
            cert_pem = self.sender_cert_pem.encode('utf-8') if isinstance(self.sender_cert_pem, str) else self.sender_cert_pem
            key_pem = self.sender_key_pem.encode('utf-8') if isinstance(self.sender_key_pem, str) else self.sender_key_pem

            private_key = serialization.load_pem_private_key(key_pem, password=None, backend=default_backend())

            # Save and remove transport headers BEFORE serializing body-part.
            transport_headers = {}
            for hdr in ('From', 'To', 'Cc', 'Subject', 'Date', 'Message-ID',
                        'MIME-Version', 'X-Priority', 'Importance'):
                val = msg[hdr]
                if val:
                    transport_headers[hdr] = val
                    del msg[hdr]

            # Serialize the body-part and canonicalize to CRLF.
            # RFC 5751 Section 3.1.1 requires CRLF line endings.
            body_part_bytes = msg.as_bytes()
            body_part_bytes = body_part_bytes.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')

            # Build PKCS#7 detached signature over the canonical bytes
            signed_data_der = self._build_pkcs7_signed(body_part_bytes, private_key, cert_pem, 'sha256')

            # Base64 encode the signature (with CRLF line breaks)
            sig_b64 = base64.encodebytes(signed_data_der)
            sig_b64 = sig_b64.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')

            # Generate a boundary that won't appear in the body part
            boundary = email.utils.make_msgid(domain='smime').strip('<>').replace('@', '.').replace('+', '.')

            CRLF = b'\r\n'
            raw = bytearray()

            # ----- Outer message headers -----
            for hdr, val in transport_headers.items():
                raw += f'{hdr}: {val}'.encode('utf-8') + CRLF
            raw += b'Content-Type: multipart/signed;' + CRLF
            raw += b'\tprotocol="application/pkcs7-signature";' + CRLF
            raw += b'\tmicalg=sha-256;' + CRLF
            raw += b'\tboundary="' + boundary.encode('ascii') + b'"' + CRLF
            raw += b'MIME-Version: 1.0' + CRLF
            raw += CRLF  # end of headers

            # ----- Preamble -----
            raw += b'This is an S/MIME signed message' + CRLF + CRLF

            # ----- First body part: original content (exact signed bytes) -----
            raw += b'--' + boundary.encode('ascii') + CRLF
            raw += body_part_bytes + CRLF

            # ----- Second body part: detached signature -----
            raw += b'--' + boundary.encode('ascii') + CRLF
            raw += b'Content-Type: application/pkcs7-signature; name="smime.p7s"' + CRLF
            raw += b'Content-Transfer-Encoding: base64' + CRLF
            raw += b'Content-Disposition: attachment; filename="smime.p7s"' + CRLF
            raw += CRLF
            raw += sig_b64 + CRLF

            # ----- Closing boundary -----
            raw += b'--' + boundary.encode('ascii') + b'--' + CRLF

            # Return an _ExactBytesMessage so downstream code (encrypt, send)
            # always gets these exact bytes via as_bytes() / as_string().
            return _ExactBytesMessage(bytes(raw))

        except Exception as e:
            logger.error(f'S/MIME signing failed: {e}', exc_info=True)
            raise RuntimeError(f'S/MIME signing failed: {e}')

    def _build_pkcs7_signed(self, data, private_key, cert_pem, hash_algo):
        """Build a DER-encoded PKCS#7 detached SignedData structure (RFC 5652)."""
        import datetime
        from asn1crypto import cms, core, algos, x509 as asn1_x509

        # Load the certificate
        if isinstance(cert_pem, str):
            cert_pem = cert_pem.encode('utf-8')

        if asn1_pem.detect(cert_pem):
            _, _, cert_der = asn1_pem.unarmor(cert_pem)
        else:
            cert_der = cert_pem

        cert = asn1_x509.Certificate.load(cert_der)

        # Digest algorithm
        digest_algo = algos.DigestAlgorithm({'algorithm': hash_algo})

        # 1. Compute the message digest over the content
        content_digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        content_digest.update(data)
        message_digest_value = content_digest.finalize()

        # 2. Build signed attributes (required for proper S/MIME)
        signing_time = core.UTCTime(datetime.datetime.now(datetime.timezone.utc))
        signed_attrs = cms.CMSAttributes([
            cms.CMSAttribute({
                'type': 'content_type',
                'values': cms.SetOfContentType([cms.ContentType('data')]),
            }),
            cms.CMSAttribute({
                'type': 'signing_time',
                'values': cms.SetOfTime([cms.Time({'utc_time': signing_time})]),
            }),
            cms.CMSAttribute({
                'type': 'message_digest',
                'values': cms.SetOfOctetString([core.OctetString(message_digest_value)]),
            }),
        ])

        # 3. Sign the DER-encoded signed attributes (SET OF tag 0x31)
        attrs_to_sign = signed_attrs.dump()
        signature = private_key.sign(attrs_to_sign, padding.PKCS1v15(), hashes.SHA256())

        # 4. Build SignerInfo with signed attributes
        signer_info = cms.SignerInfo({
            'version': 'v1',
            'sid': cms.SignerIdentifier({
                'issuer_and_serial_number': cms.IssuerAndSerialNumber({
                    'issuer': cert.issuer,
                    'serial_number': cert.serial_number,
                }),
            }),
            'digest_algorithm': digest_algo,
            'signed_attrs': signed_attrs,
            'signature_algorithm': algos.SignedDigestAlgorithm({'algorithm': 'sha256_rsa'}),
            'signature': core.OctetString(signature),
        })

        # 5. SignedData — detached: encap_content_info has type but no content
        signed_data = cms.SignedData({
            'version': 'v1',
            'digest_algorithms': cms.DigestAlgorithms([digest_algo]),
            'encap_content_info': cms.ContentInfo({
                'content_type': 'data',
            }),
            'certificates': [cms.CertificateChoices({'certificate': cert})],
            'signer_infos': cms.SignerInfos([signer_info]),
        })

        # Wrap in ContentInfo
        content_info = cms.ContentInfo({
            'content_type': 'signed_data',
            'content': signed_data,
        })

        return content_info.dump()

    def _encrypt_message(self, msg, recipients, recipient_certs):
        """
        S/MIME encrypt the message using PKCS#7 EnvelopedData with each
        recipient's public key.
        """
        try:
            msg_bytes = msg.as_bytes()

            # Generate a random AES-256-CBC session key
            from cryptography.hazmat.primitives.ciphers import algorithms, modes
            session_key = os.urandom(32)  # AES-256
            iv = os.urandom(16)

            # Encrypt the message with AES-256-CBC
            from cryptography.hazmat.primitives.ciphers import Cipher
            from cryptography.hazmat.primitives import padding as sym_padding

            padder = sym_padding.PKCS7(128).padder()
            padded_data = padder.update(msg_bytes) + padder.finalize()

            cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            encrypted_content = encryptor.update(padded_data) + encryptor.finalize()

            # Encrypt the session key for each recipient
            recipient_infos = []
            for rcpt_email in recipients:
                rcpt_email_lower = rcpt_email.strip().lower()
                if rcpt_email_lower not in recipient_certs:
                    raise ValueError(f'No certificate found for recipient: {rcpt_email}')

                cert_pem = recipient_certs[rcpt_email_lower]
                if isinstance(cert_pem, str):
                    cert_pem = cert_pem.encode('utf-8')

                # Load certificate
                if asn1_pem.detect(cert_pem):
                    _, _, cert_der = asn1_pem.unarmor(cert_pem)
                else:
                    cert_der = cert_pem

                cert = asn1_x509.Certificate.load(cert_der)

                # Encrypt session key with recipient's public key
                crypto_cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
                encrypted_key = crypto_cert.public_key().encrypt(session_key, padding.PKCS1v15())

                ri = cms.RecipientInfo({
                    'ktri': cms.KeyTransRecipientInfo({
                        'version': 'v0',
                        'rid': cms.RecipientIdentifier({
                            'issuer_and_serial_number': cms.IssuerAndSerialNumber({
                                'issuer': cert.issuer,
                                'serial_number': cert.serial_number,
                            }),
                        }),
                        'key_encryption_algorithm': cms.KeyEncryptionAlgorithm({
                            'algorithm': 'rsaes_pkcs1v15',
                        }),
                        'encrypted_key': core.OctetString(encrypted_key),
                    }),
                })
                recipient_infos.append(ri)

            # Build EnvelopedData
            enveloped_data = cms.EnvelopedData({
                'version': 'v0',
                'recipient_infos': recipient_infos,
                'encrypted_content_info': cms.EncryptedContentInfo({
                    'content_type': 'data',
                    'content_encryption_algorithm': algos.EncryptionAlgorithm({
                        'algorithm': 'aes256_cbc',
                        'parameters': core.OctetString(iv),
                    }),
                    'encrypted_content': core.OctetString(encrypted_content),
                }),
            })

            content_info = cms.ContentInfo({
                'content_type': 'enveloped_data',
                'content': enveloped_data,
            })

            pkcs7_der = content_info.dump()

            # Build the encrypted MIME message
            enc_msg = email.mime.application.MIMEApplication(
                pkcs7_der,
                'pkcs7-mime',
                name='smime.p7m',
            )
            enc_msg.set_param('smime-type', 'enveloped-data')
            enc_msg.add_header('Content-Disposition', 'attachment', filename='smime.p7m')

            # Carry over headers from original
            for hdr in ('From', 'To', 'Cc', 'Subject', 'Date', 'Message-ID'):
                val = msg.get(hdr)
                if val:
                    enc_msg[hdr] = val

            enc_msg['MIME-Version'] = '1.0'
            enc_msg['Content-Type'] = 'application/pkcs7-mime; smime-type=enveloped-data; name="smime.p7m"'

            return enc_msg

        except Exception as e:
            logger.error(f'S/MIME encryption failed: {e}', exc_info=True)
            raise RuntimeError(f'S/MIME encryption failed: {e}')

    def _graph_send(self, msg, recipients):
        """
        Send the email via Microsoft Graph API using raw MIME upload.
        Uses the Mail.Send application permission with client_credentials grant.
        This avoids SMTP AUTH and CA/MFA issues entirely.

        For S/MIME signed/encrypted messages, we must send raw MIME because
        the Graph JSON payload does not support PKCS#7 structures.
        """
        import urllib.request
        import urllib.error
        import base64

        try:
            access_token = self._acquire_oauth2_token(scope='https://graph.microsoft.com/.default')
            message_id = msg.get('Message-ID', '')
            user_principal = self.smtp_user or self.sender_email

            # Microsoft Graph API accepts MIME content as base64-encoded body
            # via POST /users/{user}/sendMail with Content-Type: text/plain
            mime_bytes = msg.as_bytes()
            mime_b64 = base64.b64encode(mime_bytes)

            send_url = f'https://graph.microsoft.com/v1.0/users/{user_principal}/sendMail'
            req = urllib.request.Request(send_url, data=mime_b64, method='POST')
            req.add_header('Authorization', f'Bearer {access_token}')
            req.add_header('Content-Type', 'text/plain')

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    pass  # 202 Accepted = success
            except urllib.error.HTTPError as e:
                if e.code == 202:
                    pass  # 202 is success for sendMail
                else:
                    raise

            logger.info(f'Email sent via Microsoft Graph API to {len(recipients)} recipient(s)')
            return {
                'success': True,
                'message': f'Email sent via Graph API to {len(recipients)} recipient(s)',
                'message_id': message_id,
            }

        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'Graph API send failed ({e.code}): {body}')
        except Exception as e:
            raise RuntimeError(f'Failed to send email via Graph API: {e}')

    def _hf_proxy_send(self, msg, recipients):
        """
        Send the email by delegating to a Heavy Forwarder running TA-smime-mailer-hf.
        
        The SH POSTs the fully-constructed MIME message + SMTP connection details
        to the HF's /services/smime_proxy/send endpoint.  The HF performs the actual
        SMTP delivery and returns success/failure.
        """
        import urllib.request
        import urllib.parse
        import urllib.error

        if not self.hf_host or not self.hf_token:
            raise RuntimeError('HF proxy is enabled but hf_host or hf_token is missing.')

        url = f'https://{self.hf_host}:{self.hf_port}/services/smime_proxy/send'

        # Get raw MIME bytes
        if hasattr(msg, 'as_string'):
            mime_data = msg.as_string()
        elif hasattr(msg, '_raw'):
            mime_data = msg._raw.decode('utf-8', errors='replace') if isinstance(msg._raw, bytes) else str(msg._raw)
        else:
            mime_data = str(msg)

        payload_dict = {
            'mime_message': mime_data,
            'recipients': recipients,
            'sender_email': self.sender_email,
            'smtp_host': self.smtp_host,
            'smtp_port': self.smtp_port,
            'smtp_security': self.smtp_security,
            'smtp_auth_type': self.smtp_auth_type,
            'smtp_user': self.smtp_user or '',
            'smtp_password': self.smtp_password or '',
        }

        # Include OAuth2 details so the HF can relay via Graph API
        if self.smtp_auth_type == 'oauth2':
            payload_dict.update({
                'oauth2_client_id': self.oauth2_client_id or '',
                'oauth2_client_secret': self.oauth2_client_secret or '',
                'oauth2_tenant_id': self.oauth2_tenant_id or '',
                'oauth2_token_url': self.oauth2_token_url or '',
                'oauth2_scope': self.oauth2_scope or '',
            })

        payload = json.dumps(payload_dict)

        req = urllib.request.Request(url, data=payload.encode('utf-8'), method='POST')
        req.add_header('Authorization', f'Bearer {self.hf_token}')
        req.add_header('Content-Type', 'application/json')

        # Skip TLS verification for internal Splunk management port
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                if resp_data.get('status') == 'ok':
                    logger.info(f'Email sent via HF proxy ({self.hf_host}) to {len(recipients)} recipient(s)')
                    return {
                        'success': True,
                        'message': resp_data.get('message', f'Email sent via HF proxy to {len(recipients)} recipient(s)'),
                        'message_id': resp_data.get('message_id', ''),
                    }
                else:
                    raise RuntimeError(f'HF proxy returned error: {resp_data.get("message", "Unknown error")}')
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'HF proxy send failed (HTTP {e.code}): {body}')
        except urllib.error.URLError as e:
            raise RuntimeError(f'Cannot reach HF proxy at {self.hf_host}:{self.hf_port}: {e.reason}')
        except Exception as e:
            if 'HF proxy' in str(e):
                raise
            raise RuntimeError(f'HF proxy send failed: {e}')

    def _smtp_send(self, msg, recipients):
        """Send the email via SMTP."""
        context = ssl.create_default_context()

        try:
            if self.smtp_security == 'ssl':
                # SMTPS: implicit TLS (port 465)
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port,
                                          timeout=30, context=context)
            else:
                # Plain SMTP or STARTTLS (port 25 or 587)
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.ehlo()
                if self.smtp_security == 'starttls':
                    server.starttls(context=context)
                    server.ehlo()

            # Authenticate
            if self.smtp_auth_type == 'oauth2':
                access_token = self._acquire_oauth2_token()
                auth_string = self._build_xoauth2_string(self.smtp_user, access_token)
                server.ehlo()
                code, resp = server.docmd('AUTH', 'XOAUTH2 ' + auth_string)
                if code not in (235, 200):
                    raise RuntimeError(f'XOAUTH2 authentication failed: {code} {resp.decode()}')
            elif self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)

            # Send
            server.sendmail(self.sender_email, recipients, msg.as_string())
            message_id = msg.get('Message-ID', '')
            server.quit()

            return {
                'success': True,
                'message': f'Email sent to {len(recipients)} recipient(s)',
                'message_id': message_id,
            }

        except smtplib.SMTPAuthenticationError as e:
            raise RuntimeError(f'SMTP authentication failed: {e}')
        except smtplib.SMTPException as e:
            raise RuntimeError(f'SMTP error: {e}')
        except Exception as e:
            raise RuntimeError(f'Failed to send email: {e}')

    def _acquire_oauth2_token(self, scope=None):
        """
        Acquire an OAuth2 access token using the client_credentials grant.
        Works with Microsoft 365 / Azure AD and other OAuth2 providers.
        If scope is provided, it overrides the configured oauth2_scope.
        """
        import urllib.request
        import urllib.parse
        import urllib.error

        client_id = self.oauth2_client_id
        client_secret = self.oauth2_client_secret
        tenant_id = self.oauth2_tenant_id
        token_url = self.oauth2_token_url
        scope = scope or self.oauth2_scope

        if not client_id or not client_secret:
            raise ValueError('OAuth2 client_id and client_secret are required')

        # Build token URL from tenant_id if not explicitly provided
        if not token_url:
            if tenant_id:
                token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
            else:
                raise ValueError('Either oauth2_token_url or oauth2_tenant_id is required')
        elif '{tenant}' in token_url and tenant_id:
            # Replace placeholder {tenant} with actual tenant_id
            token_url = token_url.replace('{tenant}', tenant_id)

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
                    raise RuntimeError(f'No access_token in OAuth2 response')
                logger.info('OAuth2 access token acquired successfully')
                return access_token
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'OAuth2 token request failed ({e.code}): {body}')

    @staticmethod
    def _build_xoauth2_string(user, access_token):
        """Build the XOAUTH2 SASL authentication string for SMTP."""
        import base64
        auth_string = f'user={user}\x01auth=Bearer {access_token}\x01\x01'
        return base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
