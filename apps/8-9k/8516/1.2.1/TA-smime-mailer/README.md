# TA-smime-mailer — S/MIME Mailer for Splunk

## Overview

Splunk Technology Add-on for sending **S/MIME signed and/or encrypted email** from:

- a custom SPL command (`smimemail`)
- a custom alert action (**Send S/MIME Email**) compatible with Splunk ES workflows

It includes UI pages for SMTP/OAuth2 setup and certificate management.

## Current Capabilities

| Capability | Status |
|---|---|
| S/MIME signing | PKCS#7 SignedData (detached), SHA-256 with RSA |
| S/MIME encryption | PKCS#7 EnvelopedData, AES-256-CBC content encryption |
| Recipient cert validation | Blocks send when recipient certs are missing/disabled (unless explicitly skipped in `smimemail`) |
| SMTP transport | `none`, `starttls`, `ssl` |
| OAuth2 mode | Uses client-credentials token and sends via **Microsoft Graph** raw MIME upload || Heavy Forwarder proxy | Route email delivery through an HF running **TA-smime-mailer-hf** || Alert action include options | Links, inline results, trigger metadata, CSV attachment |
| Certificate monitoring endpoint | `\| rest /servicesNS/nobody/TA-smime-mailer/smime_cert_monitor` |

## Installation

1. Copy app folder to Splunk apps directory:

  ```bash
  cp -r TA-smime-mailer $SPLUNK_HOME/etc/apps/
  ```

2. Install Python dependencies into app-local `lib/`:

  ```bash
  cd $SPLUNK_HOME/etc/apps/TA-smime-mailer
  pip install -r requirements.txt --target lib/
  pip install splunk-sdk --target lib/
  ```

3. Restart Splunk:

  ```bash
  $SPLUNK_HOME/bin/splunk restart
  ```

## Configuration

### SMTP / OAuth2 Setup

Navigate to **S/MIME Mailer → SMTP Setup**.

Important fields from `smime_mailer_settings.conf`:

- `smtp_host`, `smtp_port`, `smtp_security` (`none|starttls|ssl`)
- `smtp_auth_type` (`basic|oauth2`)
- `smtp_user`, `smtp_password` (basic auth)
- `oauth2_client_id`, `oauth2_tenant_id`, `oauth2_token_url`, `oauth2_scope` (OAuth2)
- `sender_email`, `sender_name`
- `use_signing`, `use_encryption`, `verify_recipient_certs`
- `use_hf_proxy` (`true|false`) — route delivery through a Heavy Forwarder
- `hf_host`, `hf_port`, `hf_token` — HF connection details (token stored in credential store)

### Heavy Forwarder Proxy

When **Route via Heavy Forwarder** is enabled, the Search Head builds and signs/encrypts
the MIME message locally, then sends the complete message along with all SMTP or Graph API
connection details to the HF over the encrypted management port (8089/tcp). The HF performs
only the final network delivery.

Requirements:

- Install **TA-smime-mailer-hf** on the Heavy Forwarder.
- Create a Splunk authentication token on the HF (assign the `smime_hf_proxy` role).
- Enter the HF hostname, port, and token on the setup page.

The **Test Connection** button performs an end-to-end test:  
SH → HF proxy → SMTP gateway **or** Graph API.  
It verifies not just that the HF is reachable, but that the HF can actually connect
to the mail server with the configured credentials.

### Transport Behavior

- If `smtp_auth_type=oauth2` and `oauth2_client_id` is set, sending is performed through **Graph API** (`/v1.0/users/{user}/sendMail`) with base64 MIME.
- Otherwise, sending uses SMTP (`SMTP`, `STARTTLS`, or `SMTP_SSL` depending on `smtp_security`).

### Certificate Management

Navigate to **S/MIME Mailer → S/MIME Certificate Management**.

- Recipient certs (`smime_recipient_certs.conf`): PEM public cert per recipient email
- Sender certs (`smime_sender_certs.conf`): PEM cert in conf + private key in Splunk credential store

## Usage

### `smimemail` Search Command

```spl
| makeresults
| eval message="Alert at " . now()
| smimemail to="alice@example.com,bob@example.com" subject="Security Alert" body="<p>$message$</p>" content_type="html"
```

Common options:

- Required: `to`, `subject`
- Optional: `body`, `body_field`, `content_type`, `cc`, `bcc`, `send_per_event`, `skip_validation`

When `content_type="html"`, the message body may contain HTML tags for formatting:

| Tag | Purpose |
| --- | --- |
| `<b>` | bold |
| `<i>` | italic |
| `<u>` | underline |
| `<s>` | strikethrough |
| `<br>` | line break |
| `<p>` | paragraph |
| `<h1>`–`<h3>` | headings |
| `<a href="...">` | link |
| `<table>` / `<tr>` / `<th>` / `<td>` | table |
| `<ul>` / `<ol>` / `<li>` | list |
| `<code>` | inline code |
| `<hr>` | horizontal rule |
| `<span style="color:red;">` | colored text |

### Alert Action

Action name: **Send S/MIME Email** (`smime_send_email`).

Supports:

- token replacement (`$result.field$`, `$field$`, alert metadata tokens)
- include links and inline results
- `attach_csv=true` attachment
- `attach_pdf=true` UI flag (currently logged and skipped; not implemented yet)

## REST Endpoints

### Certificate Management API

Endpoint:

```text
/services/smime_mailer/cert_manager
```

Actions:

- `GET action=list_recipients`
- `GET action=list_senders`
- `GET action=validate_recipients&to=a@b.com,c@d.com`
- `POST action=add_recipient`
- `POST action=add_sender`
- `DELETE action=delete_recipient&email=a@b.com`
- `DELETE action=delete_sender&email=a@b.com`

### Certificate Monitoring Endpoint

Query from SPL:

```spl
| rest /servicesNS/nobody/TA-smime-mailer/smime_cert_monitor splunk_server=local
| table email, cert_type, cert_name, not_after, days_to_expiration, status, issuer, fingerprint_sha256, serial, enabled
```

Returned fields include:

- `email`, `cert_type` (`recipient|sender|token|azure_secret`), `cert_name`
- `not_after`, `not_before`, `days_to_expiration`
- `status` (`valid|expiring_soon|expired|unknown|check_error`)
- `issuer`, `fingerprint_sha256`, `serial`, `enabled`

When `use_hf_proxy=true`, an additional row with `cert_type=token` is returned
for the Heavy Forwarder bearer token. The JWT `exp` claim is decoded to
populate `not_after` and `days_to_expiration`, so you can alert on token expiry
the same way you alert on certificate expiry:

```spl
| rest /servicesNS/nobody/TA-smime-mailer/smime_cert_monitor splunk_server=local
| where cert_type="token" AND (status="expired" OR status="expiring_soon")
```

### Azure App Secret Monitoring

When `smtp_auth_type=oauth2` is configured, the monitoring endpoint automatically
queries the Microsoft Graph API for the Azure AD application's
`passwordCredentials` (client secrets) and reports each secret's expiration date.

If the Search Head uses the HF proxy (`use_hf_proxy=true`), the Graph API call
is routed through the Heavy Forwarder (action `check_secrets`), so the SH does
not need direct internet access.

**Prerequisites:**

- The Azure app registration must have the **`Application.Read.All`** API
  permission (application type) with admin consent granted.

The rows appear with `cert_type=azure_secret`:

```spl
| rest /servicesNS/nobody/TA-smime-mailer/smime_cert_monitor splunk_server=local
| where cert_type="azure_secret"
| table email, cert_name, not_after, days_to_expiration, status, serial
```

If the Graph API call fails (expired secret, missing permission, network error),
a single error row is returned with `status=check_error` and the error details
in `cert_name`. This never blocks the return of certificate and token rows.

## Security Notes

- Sender private keys are stored in `storage/passwords` (encrypted by Splunk), not in clear text conf files.
- SMTP password and OAuth2 client secret are stored in `storage/passwords`.
- Recipient validation is enabled by default and can block sending when cert prerequisites are not met.
- Endpoint ACLs are defined in `metadata/default.meta`:
  - `script:smime_cert_manager` readable broadly
  - `script:smime_cert_monitor` readable by `admin, sc_admin`
- HF proxy token is stored in `storage/passwords`; its JWT expiration is included
  in the certificate monitoring endpoint for unified expiry alerting.

## File Layout

```text
TA-smime-mailer/
├── bin/
│   ├── smime_send_command.py
│   ├── smime_send_email.py
│   ├── smime_cert_manager_rest.py
│   └── smime_cert_monitor_rest.py
├── lib/
│   ├── smime_mailer_lib.py
│   ├── smime_cert_utils.py
│   └── splunk_config_helper.py
├── default/
│   ├── app.conf
│   ├── commands.conf
│   ├── alert_actions.conf
│   ├── restmap.conf
│   ├── web.conf
│   ├── smime_mailer_settings.conf
│   ├── smime_recipient_certs.conf
│   ├── smime_sender_certs.conf
│   └── data/ui/
├── metadata/
│   ├── default.meta
│   └── local.meta
├── README/
│   ├── smime_mailer_settings.conf.spec
│   ├── smime_recipient_certs.conf.spec
│   ├── smime_sender_certs.conf.spec
│   └── smime_cert_monitor.conf.spec
├── requirements.txt
└── README.md
```

## Dependencies

From `requirements.txt`:

- `cryptography>=41.0.0`
- `asn1crypto>=1.5.0`
- `oscrypto>=1.3.0` (kept in requirements)

Plus Splunk search command SDK module (`splunklib`, provided by `splunk-sdk`).

## Troubleshooting

Alert action log file:

```text
$SPLUNK_HOME/var/log/splunk/smime_send_email_alert.log
```

Typical checks:

- OAuth2/Graph auth errors (`AADSTS*`): verify stored client secret value and tenant/client IDs.
- Cert validation failures: confirm recipient stanzas exist and are enabled.
- Signature trust warnings: verify sender cert chain/trust on recipient client.
- REST monitor output empty: confirm cert stanzas exist in recipient/sender conf files.

### Message field in the Splunk ES detection editor

The **Message** box renders narrower than the other fields (To, Subject, …) when the
alert action is configured from the **Splunk Enterprise Security** *Edit detection*
(`correlation_search_edit`) page. This is a rendering behavior of the ES React editor:
it converts the alert-action HTML into its own React components and renders multi-line
`<textarea>` controls with a fixed (narrow) wrapper, while single-line `<input>` controls
get a full-width wrapper. The add-on cannot override this — ES strips the form's inline
`style`, `id`, `class`, and `cols`, and does not load the add-on's `appserver/static` CSS
on ES pages.

The box is fully functional regardless (editable, auto-grows in height, supports token
and HTML markup). If you prefer a full-width editor, configure the action from the
**classic** alert editor (Settings → *Searches, reports, and alerts* → *Edit alert*),
where the textarea renders full width, or edit `action.smime_send_email.param.body`
directly in `savedsearches.conf`.

> Note: do **not** use `<splunk-text-area>` / `<splunk-control-group>` web components in
> `default/data/ui/alerts/smime_send_email.html` — the ES editor does not register those
> custom elements and the Message field disappears entirely. The add-on uses a plain
> `<textarea>` for this reason.

## Changelog

### 1.2.1

- Splunkbase AppInspect compliance: declare `python.version = python3` and
  `python.required = 3.13` for the alert action, custom commands, and REST handlers.
- Package hygiene: exclude `*.pyc`/`*.pyo` and `__pycache__/`; ship all files with
  `0644` permissions (directories `0755`, no execute bit) to pass Splunk Cloud checks.
- Fixed the **Message** field disappearing in the ES detection editor by reverting it
  to a standard `<textarea>` (the `<splunk-text-area>` web component is not rendered by
  the ES editor). See *Troubleshooting* for the remaining ES-side width limitation.

### 1.2.0

- HTML formatting support for the message body (`content_type = html`).
- Heavy Forwarder proxy delivery, OAuth2/Graph sending, certificate & token/secret
  expiry monitoring endpoint.

## License

Internal use — Service & Support spol. s r. o.
