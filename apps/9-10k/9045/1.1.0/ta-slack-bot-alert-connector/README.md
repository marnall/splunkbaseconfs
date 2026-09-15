# Slack Bot Alert Connector for Splunk

`TA-slack-bot-alert-connector` is a Splunk alert action app that sends saved-search notifications to Slack through a Slack App bot token. This repository is maintained as a Splunkbase-ready release source for Splunk Enterprise and Splunk Cloud search heads.

## Release Snapshot

- Public release version: `1.1.0`
- App ID: `ta-slack-bot-alert-connector`
- Splunk Web label: `Slack Bot Alert Connector for Splunk`
- Author: `Gopinath Jyothi`
- Company: `Cisco`

## Capabilities

- Sends alert notifications with Slack `chat.postMessage`
- Optionally joins a Slack channel and retries once on `not_in_channel`
- Supports formatted Slack attachment rendering with alert title, results link, body text, and selected result fields
- Separates the saved-alert link from the run-specific results link
- Supports emoji, bot username, and result-field selection from the alert action UI

## Compatibility

- Splunk Enterprise 10.x search heads
- Splunk Cloud Platform search heads
- Standalone search heads, distributed search, and search head clusters
- Python 3 runtime only

The app should be installed on search heads only.

## Security Posture

- Slack tokens are read from encrypted Splunk storage
- Slack tokens are sent in the `Authorization` header instead of form data
- Dynamic logs redact token-like values before writing to Splunk logs
- Alert message bodies and event payloads are intentionally not logged
- Source packaging excludes `local/`, `__pycache__/`, and compiled Python artifacts

The VULN-89099 remediation details are documented in [docs/SECURITY_REMEDIATION.md](docs/SECURITY_REMEDIATION.md).

## Project Documentation

- [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md)
- [docs/TEST_PLAN.md](docs/TEST_PLAN.md)
- [docs/TEST_REPORT_2026-07-07.md](docs/TEST_REPORT_2026-07-07.md)
- [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)
- [docs/SPLUNK_10_CLOUD_COMPATIBILITY.md](docs/SPLUNK_10_CLOUD_COMPATIBILITY.md)

## Local Build And Validation

```bash
./scripts/run_validation.sh
./scripts/build_release.sh
```

The build script creates a single clean `.spl` file in `../dist`.
