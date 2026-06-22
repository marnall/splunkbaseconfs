# =========================================================
# smime_mailer_settings.conf.spec
# =========================================================
# Settings for the S/MIME Mailer Splunk App (TA-smime-mailer)

[smtp]
smtp_host = <string>
# SMTP server hostname or IP address.

smtp_port = <integer>
# SMTP server port. Common values: 25 (SMTP+STARTTLS), 465 (SMTPS), 587 (Submission).
# Default: 25

smtp_security = <string>
# Connection security mode.
# Valid values: none, starttls, ssl
#   none     = plain SMTP (port 25, no encryption)
#   starttls = SMTP with STARTTLS upgrade (port 25 or 587)
#   ssl      = SMTPS (implicit TLS on port 465)
# Default: starttls

smtp_auth_type = <string>
# Authentication method for SMTP.
# Valid values: basic, oauth2
#   basic  = Username + password (or no auth if both are empty)
#   oauth2 = OAuth2 client credentials grant with XOAUTH2 SASL mechanism
# Default: basic

smtp_user = <string>
# Username for SMTP authentication (optional for basic, required for oauth2).
# For OAuth2 with Microsoft 365, this is typically the sender email address.

smtp_password = <string>
# Password for SMTP authentication. Stored encrypted via Splunk storage/passwords.
# Only used when smtp_auth_type = basic.

oauth2_client_id = <string>
# OAuth2 application (client) ID. Required when smtp_auth_type = oauth2.
# For Microsoft 365 / Azure AD, this is the Application (client) ID from App Registrations.

oauth2_tenant_id = <string>
# OAuth2 tenant ID (for Microsoft 365 / Azure AD).
# Used to construct the token URL if oauth2_token_url is not explicitly set.

oauth2_token_url = <string>
# Full OAuth2 token endpoint URL. If empty and oauth2_tenant_id is set,
# defaults to https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token

oauth2_scope = <string>
# OAuth2 scope(s) to request. Space-separated if multiple.
# Default for M365 (Graph API): https://graph.microsoft.com/.default

sender_email = <string>
# Default sender (From) email address.

sender_name = <string>
# Display name for the sender.

splunk_hostname = <string>
# External base URL of this Splunk instance used in email links (View Alert, View Results).
# Example: https://splunk.example.com:8000
# When set, overrides the server_uri from the alert payload, which may contain an
# internal hostname that recipients cannot reach from outside the network.
# Leave empty to use the URI Splunk provides automatically.

use_signing = <bool>
# Whether to S/MIME-sign outgoing emails. Requires a sender certificate.
# Default: true

use_encryption = <bool>
# Whether to S/MIME-encrypt outgoing emails. Requires recipient certificates.
# Default: true

verify_recipient_certs = <bool>
# When true, the command will refuse to send if ANY recipient is missing a
# valid public certificate. Required for ES integration.
# Default: true

use_hf_proxy = <bool>
# When true, email sending is routed through a Heavy Forwarder running
# TA-smime-mailer-hf. The Search Head sends the fully constructed MIME
# message to the HF via its management port (8089). All configuration
# (SMTP, certs, S/MIME options) stays on the Search Head.
# Default: false

hf_host = <string>
# Hostname or IP address of the Heavy Forwarder that will proxy email delivery.
# Only used when use_hf_proxy = true.

hf_port = <integer>
# Splunk management port on the Heavy Forwarder.
# Default: 8089

hf_token = <string>
# Splunk authentication token (bearer token) for the Heavy Forwarder.
# Used to authenticate REST API calls from the Search Head to the HF.
# Stored encrypted via Splunk storage/passwords.

expiry_notifications_enabled = <bool>
# When true, the scheduled saved search will send certificate, token, and
# secret expiry notifications. When false, notifications are globally disabled.
# Default: false

expiry_notification_emails = <string>
# Comma-separated list of admin email addresses that will receive
# certificate / token / secret expiry notifications.
# These addresses must have recipient certificates configured for
# S/MIME encryption. Leave empty to disable expiry notifications.
