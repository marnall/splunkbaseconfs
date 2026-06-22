# =========================================================
# smime_recipient_certs.conf.spec
# =========================================================
# Stores public certificate (PEM) data for each recipient email address.
# Each stanza name is the recipient email address.

[<email_address>]
cert_pem = <string>
# PEM-encoded public certificate for this recipient (X.509).
# Newlines in the PEM are stored as literal \n sequences.

cn = <string>
# Common Name extracted from the certificate subject.

serial = <string>
# Certificate serial number (hex).

not_after = <string>
# Certificate expiry date (ISO 8601).

not_before = <string>
# Certificate validity start date (ISO 8601).

issuer = <string>
# Certificate issuer distinguished name.

fingerprint_sha256 = <string>
# SHA-256 fingerprint of the certificate.

enabled = <bool>
# Whether this certificate is active. Default: true.

notify_on_expiry = <bool>
# When true, the certificate owner will receive an encrypted email
# notification when their certificate is about to expire or has expired.
# Requires expiry_notification_emails to be configured.
# Default: false
