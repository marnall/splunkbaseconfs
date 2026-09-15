# Slack Bot Alert Connector for Splunk

## Release 1.1.0

This minor release addresses Splunkbase Developer Advisory feedback while preserving the Slack alert action behavior.

### Highlights

- Restored the standard UCC `import_declare_test.py` import path order.
- Updated shipped UCC framework metadata from `6.0.1` to `6.5.2`.
- Sends alert notifications with Slack Web API `chat.postMessage`.
- Optionally joins a Slack channel and retries once when Slack returns `not_in_channel`.
- Renders richer Slack alert cards with an alert link, a run-specific results link, and selected result fields.
- Protects secrets by redacting token-like values in logs and sending the bot token in the HTTP Authorization header.
- Enforces HTTPS Slack API endpoints and bounded outbound request timeouts.

### Compatibility

- Python 3 alert action and REST handler remain enabled.
- The app is intended for Splunk 10 and Splunk Cloud search-head deployments.
- The app should be installed on search heads only.

### Validation

Local validation covers:

- Slack alert message post behavior.
- Auto-join and retry behavior.
- Token absence from Slack request form data.
- Token and alert payload absence from app logs.
- Redaction of token-like values in dynamic log messages.
- HTTPS base URL enforcement and bounded Slack request timeout behavior.
- Standard UCC import path order.

Runtime validation in a non-production Splunk environment is still required before production deployment.
