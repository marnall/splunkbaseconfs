# EventTimeline

EventTimeline turns AWS CloudTrail saved-search alerts into evidence timelines. It
does not ship prebuilt detection content or external analysis integrations.

Configure a Splunk saved search over CloudTrail data, enable the **Create
EventTimeline Finding** custom alert action, and include `_time`, `index`, and
`sourcetype` in the final results. `_raw` is optional and is not required for
timeline generation. EventTimeline creates a finding immediately and hydrates
activity before and after the alert.

This distribution shares the `cloudlens` app ID with the paid edition. Install
only one edition on a Splunk instance.

## Requirements and compatibility

- Splunk Enterprise 9.4.6 or later, or Splunk Cloud Platform, on the search-head
  tier. EventTimeline is not an app for Universal Forwarders or indexer-only nodes.
- KV Store, scheduled searches, custom alert actions, Python 3, SplunkJS, and
  Simple XML must be available and enabled.
- AWS CloudTrail events must already be searchable by the Splunk search head.
- Splunk Cloud installation remains subject to the platform's private-app and
  AppInspect approval process.

This release is live-tested on Splunk Enterprise 9.4.6 for Linux amd64,
10.4.1 for macOS arm64, and 10.4.2 for Linux amd64. Splunk 10.2 and later are
the clean configuration baseline. Splunk 9.4.6 ignores the newer
`python.required` alert-action setting and emits a non-fatal `btool` warning;
the retained `python.version = python3` fallback is live-tested and the full
alert-to-timeline workflow remains functional. Earlier 9.x releases are not
part of this release's production support matrix.

## Installation

Install the release `.tgz` from **Apps > Manage Apps > Install app from file**,
or use the Splunk CLI:

```text
$SPLUNK_HOME/bin/splunk install app EventTimeline-1.0.20-build73.tgz -update 1
```

Restart Splunk when requested. EventTimeline opens the Saved Search Guide first.
Follow its first-run checklist to configure and test the CloudTrail source and
validate the complete alert-to-timeline workflow. The standard Splunk `user`
role can discover EventTimeline and read its investigation pages. Assign
`cloudlens_analyst` to investigators who also need EventTimeline's explicit
investigation capability and scheduled-search dispatch. Manual generation
is the default. Configure a saved search over
CloudTrail data and enable the **Create EventTimeline Finding** alert action.
Include `_time`, `index`, and `sourcetype` in the final alert results so
EventTimeline can preserve event timing and source boundaries. `_raw` is
optional; analysts can open the source event in Splunk Search when raw evidence
is needed.

In the default flow, the alert action creates only the normalized finding. An
analyst opens that finding, selects an investigation window, and chooses
**Fetch timeline**. Administrators can opt in to automatic generation from
Setup when search-head capacity and alert volume permit it.

Investigation fetching uses the compact engine by default and searches only the
selected user or resource. Enable **Include role lineage** in the workspace when
the investigation requires AssumeRole parent and child session correlation.
Role-lineage mode performs additional extraction and correlation and is expected
to consume more search-head resources than compact mode.

Setup also controls triggered-alert retention from 7 through 15 days. The
default is 15 days. A daily scheduled cleanup removes expired findings and then
removes associated triage, deduplication, and investigation records. Findings
in an active investigation or an in-flight timeline hydration are protected
until that work leaves its active state.

For a search-head cluster, deploy the app through the deployer and validate the
KV Store and alert-action workflow in that cluster before production rollout.

## Large CloudTrail environments

EventTimeline prefers the exact `index` and `sourcetype` carried by an alert result.
Only aggregate alerts that omit source metadata use the configured
`cloudlens_cloudtrail` macro. Keep that macro restricted to CloudTrail indexes
and sourcetypes; do not configure it as `index=*`.

Each alert-action invocation creates at most 100 findings. In the default
manual mode, it dispatches no timeline search. If automatic generation is
enabled in Setup, one invocation dispatches at most 10 immediate timeline
searches. Each manual or automatic hydration stores at most 2,000 events and
has a default five-minute runtime ceiling. These settings can be overridden
per saved search:

```ini
action.cloudlens_finding.param.max_findings_per_alert = 100
action.cloudlens_finding.param.max_hydrations_per_alert = 10
action.cloudlens_finding.param.max_timeline_events = 2000
action.cloudlens_finding.param.hydration_max_time_secs = 300
```

Use smaller values for high-frequency detections and shared entities such as
root principals, organization-wide roles, and NAT addresses. Open **Timeline
Health** as an EventTimeline administrator to review queued or failed hydration,
truncated timelines, scheduler lag, skipped executions, and search runtime.

The Manual Timeline Generator uses Fast-mode, preview-free Splunk jobs with a
two-minute server and client runtime ceiling. Windows longer than six hours are
searched newest-first in bounded six-hour or one-day slices. The first slice is
rendered immediately; analysts choose **Load older events** to expand coverage.
Completed investigations are cached only in page memory for five minutes and
are never written to browser storage.

For an optional accelerated path, override the `cloudlens_timeline_locator`
macro in `local/macros.conf` with a summary-index or accelerated-data-model
search that returns canonical `cl_*` fields. The default delegates to
`cloudlens_cloudtrail`. Auto mode detects a custom locator and falls back to the
raw source if the locator fails or returns no evidence.

## Compatibility namespace

The visible product name is EventTimeline. The app folder and ID remain
`cloudlens`, and existing `cloudlens_*` macros, lookups, roles, KV collections,
REST paths, alert-action ID, and internal saved-search titles are retained. This
allows an existing installation to upgrade without losing findings, timelines,
source configuration, role assignments, or saved-alert action wiring.
