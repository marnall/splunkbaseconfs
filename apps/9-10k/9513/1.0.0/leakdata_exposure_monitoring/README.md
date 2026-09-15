# LeakData Exposure Monitoring App

LeakData Exposure Monitoring App is a search-and-dashboard package for reviewing security exposure events delivered by LeakData to Splunk's HTTP Event Collector (HEC). It displays reported signals, affected counts, and canonical risk context. It does not treat exposure as proof that an account, device, or organization was compromised.

## Developer and support

- Developer: CyberVisir Solutions Ltd
- Product: https://leakdata.io
- Support: https://leakdata.io/contact
- Privacy: https://leakdata.io/privacy
- Terms: https://leakdata.io/terms

## Package contents

- Three Simple XML dashboards: Exposure Overview, Target Exposure, and Event Explorer.
- Search macros that normalize the documented LeakData monitoring fields.
- Event types for all LeakData events and the narrower exposure-signal set.
- One disabled-by-default critical exposure review search.
- No scripted inputs, binaries, custom commands, credential stores, or outbound network calls.

## Prerequisites

- Splunk Enterprise or Splunk Cloud Platform with an enabled HEC JSON event endpoint.
- Permission to install an app and search the index selected for the HEC token.
- A LeakData plan and contract that enable webhook and SIEM integration access.
- A public HTTPS HEC endpoint reachable from LeakData.

## Install

1. Install the `.tar.gz` package from **Apps > Manage Apps > Install app from file**, or use your organization's approved Splunk Cloud app-installation workflow.
2. Restart Splunk only if your environment asks for it.
3. Grant intended analysts read access to the app and to the index used by your HEC token.
4. If that index is not among the analyst role's default search indexes, override the `leakdata_base` macro locally to include `index=<your_index>`.

The package does not create or modify indexes. Index lifecycle, retention, and role access remain under the Splunk administrator's control.

## Configure HEC delivery in LeakData

1. In Splunk, create or select an HEC token with access to the intended index. Keep the token enabled.
2. Use the JSON event endpoint ending in `/services/collector/event`; the versioned `/services/collector/event/1.0` form is also accepted. Do not use `/services/collector/raw`.
3. Keep indexer acknowledgment disabled for this integration. LeakData verifies the immediate HEC HTTP response but does not poll the HEC acknowledgment endpoint.
4. In LeakData, open **Dashboard > API & Webhooks**, create a webhook, and select **Splunk HEC**.
5. Paste the public HTTPS event endpoint and HEC token. The token is encrypted before storage and is not returned to the browser after saving.
6. Start with the default monitoring events: `breach.detected`, `domain.alert`, and `monitoring.alert`.
7. Send a test notification, then confirm indexing with a search such as:

   ```spl
   sourcetype="leakdata:webhook" source="leakdata"
   | sort - _time
   | head 20
   ```

An HTTP 2xx delivery result means the HEC endpoint accepted the request. It does not by itself prove that the event was indexed, retained, or searchable by a particular role. Verify those conditions in Splunk.

## Event schema

HEC receives an event object with these stable envelope fields:

| Field | Meaning |
| --- | --- |
| `id` | Unique LeakData delivery event ID. |
| `type` | LeakData event type. |
| `created` | Event creation time in epoch milliseconds. |
| `data` | Event-specific, minimized payload. |
| indexed field `leakdata_event_id` | Correlation copy of the event ID. |
| indexed field `leakdata_event_type` | Correlation copy of the event type. |
| indexed field `leakdata_preset` | Always `splunk_hec` for this path. |

The default monitoring payloads can report `data.domain`, `data.target`, `data.companyName`, `data.severity`, `data.riskScore`, `data.riskLevel`, `data.breachCount`, `data.affectedEmailCount`, `data.dataTypes`, and `data.detectedAt`. A missing field remains missing; the app does not invent a score, severity, affected count, or compromise state.

Risk bands in the overview use the same canonical boundaries as LeakData: Low 0–24, Medium 25–49, High 50–74, and Critical 75–100. These bands prioritize review and are not a declaration of compromise.

## Data minimization and analyst review

- The default monitoring events emphasize counts, categories, masked values, and monitored targets. They do not include a raw list of affected email addresses.
- Selecting additional event types can introduce event-specific values, including a search query. Enable only the events needed for the documented use case.
- The app's default tables omit the raw event body. Authorized analysts can still search indexed data under normal Splunk role controls.
- Repeated events can refer to the same underlying exposure. Do not add counts across time without checking deduplication and event semantics.
- The packaged critical review search is disabled. If an administrator enables it, it only selects `domain.alert` or `monitoring.alert` events explicitly marked with severity `critical` and a reported affected count above zero. A human must validate every result before response.
- No packaged search performs remediation, account actions, ticket creation, or external notification.

## Security and operations

- LeakData sends `Authorization: Splunk <token>` only to the configured HEC event endpoint.
- The token is not included in the event body, dashboard, or client API response.
- LeakData blocks private-network destinations and plain HTTP in production and does not follow delivery redirects.
- This Splunk app contains configuration, searches, dashboards, and static images only. It does not initiate network traffic.
- Scope the HEC token to the required index and rotate it under your organization's credential policy. Replacing the token in LeakData does not expose the previously stored value.

## Troubleshooting

- **No events:** confirm the exact `/services/collector/event` URL, token state, HEC TLS reachability, selected LeakData events, and webhook delivery history.
- **HEC accepts but searches are empty:** verify the token's target index, index retention, and the analyst role's searchable/default indexes.
- **Dashboards are empty but manual search works:** update the local `leakdata_base` macro to add the correct index constraint.
- **403 or plan message in LeakData:** webhook and SIEM integration entitlements are evaluated separately; contact your LeakData account owner.
- **Review search does not fire:** it ships disabled and intentionally excludes missing, non-critical, and zero-affected-count events.

## License

Copyright 2026 CyberVisir Solutions Ltd. All rights reserved. Use of this package and the LeakData service is subject to the applicable LeakData agreement and the terms published at https://leakdata.io/terms.
