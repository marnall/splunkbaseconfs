# =========================================================
# smime_sender_certs.conf.spec
# =========================================================
# Stores sender signing certificate + private key.
# Each stanza name is the sender email address.

[<email_address>]
cert_pem = <string>
# PEM-encoded signing certificate (X.509).

key_pem = <string>
# PEM-encoded private key. Stored encrypted via Splunk passwords.

cn = <string>
# Common Name from the certificate subject.

not_after = <string>
# Certificate expiry date (ISO 8601).

fingerprint_sha256 = <string>
# SHA-256 fingerprint of the certificate.

enabled = <bool>
# Whether this sender certificate is active. Default: true.

notify_on_expiry = <bool>
# When true, the certificate owner will receive an encrypted email
# notification when their certificate is about to expire or has expired.
# Requires expiry_notification_emails to be configured.
# Default: false
