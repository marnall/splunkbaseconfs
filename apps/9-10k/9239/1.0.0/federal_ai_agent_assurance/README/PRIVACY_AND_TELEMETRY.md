# Privacy and Telemetry

No telemetry. No analytics, crash reporting, update polling, CDN, external
font, license ping, or any other outbound call. The app is fully
functional with no route off the search head.

All data stays in your Splunk deployment (faaa_* KV collections and
`$SPLUNK_HOME/var/log/splunk/faaa.log`). The only optional outbound
connection is the administrator-configured behind-the-firewall LLM
endpoint, invoked only when a user with `faaa_use_ai` explicitly requests
an AI review; the prompt then contains release metadata, deterministic
evidence IDs/findings/diff summaries, and the release description marked
as untrusted data — never Splunk credentials, session tokens, or secrets.

Uninstalling the app leaves KV collections until an administrator removes
them (`splunk clean kvstore -app federal_ai_agent_assurance`); the
optional AI credential remains in the Splunk credential store until
deleted. Back up evidence by exporting bundles or backing up KV Store.
