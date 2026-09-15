# Defaults stanzas
# ----------------
# The bare-scheme stanzas below ([veza_events] / [veza_audit_logs]) provide
# defaults inherited by every [scheme://<name>] instance. Splunk's modular-input
# framework knows about python.version / python.required / interval implicitly,
# but the SLIM validator (used by Splunkbase / Splunk Cloud SSAI) only recognizes
# settings declared in this spec — so we document them explicitly here.

[veza_events]
* Defaults for all veza_events modular input instances. Each setting here is
* inherited by every [veza_events://<name>] stanza unless overridden.

python.version = <string>
* Splunk Python interpreter version selector (legacy). Set to "python3".

python.required = <string>
* Required Python version on Splunk Enterprise 10.2+. Set to "3.13".

interval = <integer>
* Polling interval in seconds. Defaults to 60.

index = <string>
* Splunk index to write events to. Defaults to "main".

sourcetype = <string>
* Splunk sourcetype. Defaults to "veza:events".

page_size = <integer>
* Default max items per page; overridden per-instance.

verify_tls = <boolean>
* Default TLS verification; overridden per-instance.


[veza_audit_logs]
* Defaults for all veza_audit_logs modular input instances.

python.version = <string>
* Splunk Python interpreter version selector (legacy). Set to "python3".

python.required = <string>
* Required Python version on Splunk Enterprise 10.2+. Set to "3.13".

interval = <integer>
* Polling interval in seconds. Defaults to 60.

index = <string>
* Splunk index to write events to. Defaults to "main".

sourcetype = <string>
* Splunk sourcetype. Defaults to "veza:audit".

page_size = <integer>
* Default max items per page; overridden per-instance.

verify_tls = <boolean>
* Default TLS verification; overridden per-instance.


# Per-instance stanzas
# --------------------

[veza_events://<name>]
* Modular input that ingests Veza platform events from /api/v1/events/export.
* Authenticates to the tenant via the OAuth2 client_credentials grant.
* Drains all available pages on each scheduled invocation, persists the
* cursor between runs, and writes one Splunk event per Veza event.

tenant_url = <string>
* Base URL of the Veza tenant, e.g. https://yourtenant.cookieai.com.
* No trailing slash. Required.

client_id = <string>
* Veza OAuth2 client_id. Create the client under Settings → OAuth in the
* Veza UI, choosing the client_credentials grant and the Auditor role (or
* a custom role with at least the events:view scope). Required.

client_secret = <string>
* Veza OAuth2 client_secret matching client_id. Stored encrypted in Splunk's
* credential store on first run; the value in inputs.conf is replaced with
* a placeholder. Required on first save.

scope = <string>
* Optional OAuth2 scope string. Leave blank to use the OAuth client's
* default configured scopes.

page_size = <integer>
* Maximum number of events per page. Defaults to 1000.
* Veza enforces an upper bound; values above 1000 are clamped server-side.

verify_tls = <boolean>
* Whether to verify the TLS certificate of the tenant. Defaults to true.
* Set to false ONLY for self-signed development tenants.


[veza_audit_logs://<name>]
* Modular input that ingests Veza audit log entries from
* /api/v1/system/audit/export. Same operational shape and OAuth flow as
* veza_events.

tenant_url = <string>
* Base URL of the Veza tenant. Required.

client_id = <string>
* Veza OAuth2 client_id. Required.

client_secret = <string>
* Veza OAuth2 client_secret. Required on first save.

scope = <string>
* Optional OAuth2 scope string. Leave blank to use the OAuth client's
* default configured scopes.

page_size = <integer>
* Maximum entries per page. Defaults to 1000.

verify_tls = <boolean>
* Whether to verify the TLS certificate of the tenant. Defaults to true.
