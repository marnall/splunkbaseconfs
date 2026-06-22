# =========================================================
# smime_cert_monitor (REST endpoint – read-only)
# =========================================================
# Returns certificate inventory with calculated expiration info.
#
# Usage:
#   | rest /servicesNS/nobody/TA-smime-mailer/smime_cert_monitor splunk_server=local
#
# Each entry represents one certificate (sender or recipient).
# The entry key is formatted as  <cert_type>__<email>.

[<cert_type>__<email>]

email = <string>
# Email address associated with this certificate.

cert_type = <string>
# "sender" or "recipient".

cert_name = <string>
# Common Name (CN) from the certificate subject.

not_after = <string>
# Certificate expiry date (ISO 8601 UTC).

not_before = <string>
# Certificate validity start date (ISO 8601 UTC).
# May be empty for sender certificates.

days_to_expiration = <integer>
# Number of days remaining until the certificate expires.
# Negative values mean the certificate is already expired.

status = <string>
# Calculated status: "valid", "expiring_soon" (<=30 days), "expired", "revoked", or "unknown".

issuer = <string>
# Certificate issuer distinguished name.

fingerprint_sha256 = <string>
# SHA-256 fingerprint of the certificate.

serial = <string>
# Certificate serial number (hex).
# May be empty for sender certificates.

enabled = <bool>
# Whether this certificate is active.

crl_checked = <bool>
# Whether a CRL Distribution Point was successfully downloaded and checked.

crl_revoked = <bool>
# Whether the certificate serial appears on its issuer's CRL.

crl_reason = <string>
# CRL revocation reason (e.g. "key_compromise", "unspecified").
# Empty if not revoked.

crl_revocation_date = <string>
# ISO 8601 UTC date the certificate was revoked.
# Empty if not revoked.

crl_error = <string>
# Error message if the CRL check could not be performed.

crl_url = <string>
# The CRL Distribution Point URL that was checked.
