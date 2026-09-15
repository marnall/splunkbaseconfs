# Release notes

## Version 1.4.1

- Added the supplied official PT NAD icon to both Splunk static asset paths.
- Added standard, Retina, alternate-menu, and app-bar PNG variants.
- Incremented the static asset build number so Splunk Web refreshes cached branding.

## Version 1.4.0

- Added Splunk CIM fields, event types, and tags for Intrusion Detection,
  Alerts, Authentication, and Change data models.
- Added parsing for combined incident payloads containing `alert[]`, `alerts[]`,
  or `rules[]` with multiple rule identifiers.
- Added `combined_event`, `nad_correlation_id`, `rule_count`,
  `related_rule_id`, and `related_rule_name` fields.
- Added CIM validation searches and documented customer-owned correlation scope.
- Explicitly excluded PT NAD asset discovery synchronization with the Splunk ES
  Asset and Identity Framework.
- Documented that automated playbooks and confidential Vectra integration
  mechanisms are not included.
- Added `smohebi@ptsecurity.com` as the support email.

## Version 1.3.0

- Prepared the add-on for public Splunkbase distribution.
- Added official Positive Technologies author and company metadata.
- Added Apache License 2.0 licensing.
- Added Splunk application icons based on the supplied PT NAD brand asset.
- Removed environment-specific addresses and replaced them with placeholders.
- Expanded installation, distributed deployment, validation, and troubleshooting guidance.
- Retained the `ptnad` index as the dashboard and documentation default.
- Retained support for the canonical `pt:nad:syslog` sourcetype and the legacy
  `pt:nad:syslog2` sourcetype.

## Version 1.2.0

- Added the PT NAD Security Overview dashboard.
- Added a visible navigation entry for the application.

## Version 1.1.0

- Added the `ptnad_parse_historical` search macro.

## Version 1.0.0

- Initial parser, normalized fields, and event types.
