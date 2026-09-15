# EventTimeline Release Notes

## 1.0.20

Build 73 improves repeated API-call handling in the Investigation Timeline.
Matching calls are grouped only when the timeline phase, action, outcome, and
available identity, source IP, resource, account, session, user-agent, and
error context agree. Sparse events without a reliable entity or resource
discriminator remain separate, and the alert trigger is never folded into a
repeated-event group. Collapsed groups display the exact occurrence count and
retain their individual event details when expanded.

Timeline hydration now persists additional principal, resource, error, event
category, management-event, and read-only fields needed to prevent materially
different CloudTrail activity from being grouped together. The hydration
search removes sequential per-row ranking while preserving bounded result and
truncation behavior. Client grouping also avoids unnecessary copies and
re-sorting for already chronological results. Expanded edge coverage includes
sparse data, phase boundaries, out-of-order input, discriminator persistence,
and a 5,000-event grouping matrix.

## 1.0.19

Build 72 fixes the Investigation Timeline scope selector. Resource Activity is
now available only when a finding contains a usable `cl_resource_id`; otherwise
the workspace explains why the pivot is unavailable and prevents an incorrect
user-scoped search from being dispatched. User and resource fetch requests now
retain separate entity pivots throughout the compact timeline workflow.

Hydration no longer treats Splunk `host` metadata as an AWS resource. This
prevents service names and collection hosts from appearing as affected
resources or producing misleading resource correlations.

## 1.0.18

Build 71 promotes **Manual Timeline Generator** to a direct top-level navigation
destination. **Investigation Timeline** remains under **Investigate**, preserving
the alert-investigation workflow while making ad hoc entity and resource
timeline generation easier to find.

The Setup and Get Started pages also identify planned Azure Activity Logs,
Google Cloud Audit Logs, and Windows Sysmon support as **Coming soon**. AWS
CloudTrail remains the only supported and configurable data source in this
release; no future-source integrations or runtime behavior are included.

## 1.0.17

Build 70 hardens Triggered Alerts, Investigation Timeline, and Manual Timeline
Generator through expanded UI and correctness edge-case testing. Responsive
layouts now adapt earlier on tablet-sized screens, long investigation values
remain readable, and explicit text indicators preserve outcome meaning without
depending on color alone.

Investigation events with missing or malformed timestamps are retained as
context instead of being incorrectly placed after the alert. Manual timeline
results preserve unknown outcomes instead of reporting them as successful,
calendar input rejects impossible dates, and additional valid Splunk REST
result payload shapes are accepted. The release also includes dedicated runtime
edge suites for timeline placement, outcome handling, result parsing, bounded
search behavior, compact searches, and opt-in role lineage.

## 1.0.16

Build 57 redesigns Triggered Alerts as a focused investigation queue. The page
now provides at-a-glance alert, severity, ownership, and retention counts;
resource, username, role, source-IP, detection, and identifier search; and
status filters with live result counts. Each alert presents the finding,
trigger time, complete identity/resource/IP context, owner, status, and a clear
Open investigation action in a more readable six-column layout.

Selection-aware bulk actions, clearer empty states, keyboard-openable rows,
screen-reader status updates, visible focus treatment, full long-value wrapping,
and responsive tablet and narrow-screen layouts improve analyst usability. Alert
retrieval, retention, triage writes, deletion permissions, and investigation
behavior are unchanged.

## 1.0.15

Build 55 adds a compact contact and support section to the bottom of the Get
Started page. It also hardens the release archive against hidden macOS metadata:
all dot-prefixed paths, AppleDouble `._*` files, Finder metadata, local
configuration, tests, caches, and development artifacts are excluded. The
archive is generated with macOS metadata copying disabled and contains exactly
one `cloudlens/` top-level directory.

## 1.0.14

Build 54 refreshes the first-run **Get Started** workflow with eight current,
actionable steps covering prerequisites, role assignment, CloudTrail source and
retention configuration, manual or automatic timeline generation, Query
Converter validation, scheduled-alert creation, finding delivery, and timeline
health verification. The guide now includes 15-minute scheduling guidance,
alert throttling, the default 15-day retention period, and the compact timeline
engine with optional role lineage.

The saved-search example no longer carries `_raw` in every alert result. Raw
evidence remains available through Splunk Search when an analyst opens an event.
Numbered onboarding badges are centered consistently across desktop and narrow
layouts without horizontal overflow.

## 1.0.13

Build 53 hardens the Query Converter against result-loss and cross-environment
edge cases. Canonical fields are now preserved through every positive
projection, normalization is moved ahead of result shaping when an existing
macro was placed too late, and fields used by a `stats BY` clause are no longer
added again as conflicting aggregates. `_raw` preservation now applies to
existing negative `fields` stages as well as generated output.

The compatibility analyzer now understands pipes inside triple-backtick SPL
comments, rejects unbalanced quotes, parentheses, brackets, and comments, and
routes environment-specific generating commands to manual review rather than
producing misleading converted SPL. The converter remains source-independent:
it preserves the original index, sourcetype, macro, and base-search boundaries.

## 1.0.12

Build 52 adds a Query Converter for preparing existing AWS CloudTrail SPL for
EventTimeline. It supports event-level searches and searches with one `stats`
stage, adds the normalization and canonical finding fields, preserves required
fields through result projections and aggregation, and omits `_raw` by default.
The converter never changes, saves, schedules, or automatically executes the
original query. It reports unsupported or side-effecting SPL for manual review
and offers an explicit bounded validation using Fast mode, no preview, a
30-second limit, 50 result rows, and a user-selected recent time window.

Build 51 fixes EventTimeline visibility for accounts that have only Splunk's
standard `user` role. Standard users can now discover the app, open the analyst
views, read retained findings, settings, and investigation timelines, and save
their separate triage state. Setup, Timeline Health, alert deletion, retention
configuration, deduplication records, and server-owned finding or timeline
writes remain restricted to the existing administrative boundaries. Assign the
`cloudlens_analyst` role when an investigator also needs the app-specific
investigation capability and scheduled-search dispatch.

Build 49 improves Investigation Timeline related-finding correlation. AWS
account ID is no longer a related-finding signal or display value. Matches now
use exact role, username, identity, source IP, resource, and resource-name
evidence from retained triggered alerts, with stronger entity matches ranked
ahead of source-IP-only matches. Generic AWS service principals, service-valued
source addresses, and service endpoint placeholders are excluded. No CloudTrail
search is dispatched.

Build 48 restores the original EventTimeline blue timeline-node app icon across
the Splunk app drawer and app metadata assets. Application behavior is unchanged.

Build 47 optimizes Manual Timeline Generator searches for usernames, identity
ARNs, IAM roles, assumed-role sessions, and role-session names. Identity
searches now use indexed term pruning followed by a lightweight exact identity
match before the result cap and full CloudTrail normalization. This reduces
unnecessary normalization work and prevents unrelated raw-text matches from
consuming the candidate limit. Other manual entity searches and Investigation
Timeline behavior are unchanged.

Build 46 adds expandable related-finding context to the Investigation Timeline.
EventTimeline compares the selected finding with retained triggered alerts from
the past 30 days and explains exact matches on role or identity, source IP,
account, and resource. The badge reports the complete match count and the panel
shows the 100 strongest recent matches. This uses only the findings KV Store and
does not dispatch a CloudTrail or timeline search; available history remains
bounded by the configured 7-to-15-day finding-retention period.

Build 45 simplifies app navigation around the analyst workflow. **Get Started**
and **Triggered Alerts** remain immediately accessible; investigation timelines
are grouped under **Investigate**, while health diagnostics and Splunk search
are grouped under **Operations**. **Setup** remains a direct destination. The
hierarchy reduces visual crowding in classic horizontal navigation and renders
as accessible grouped drawers in Splunk's modern navigation.

Build 44 reorganizes the Investigation Workspace around a sticky investigation
toolbar with the window selector, optional role-lineage correlation, a prominent
**Fetch timeline** action, and an in-progress **Stop search** control. Secondary
commands are grouped into an accessible Actions menu, while coverage, event
counts, truncation, and data-quality details move into an expandable section.

The alert trigger now remains visible as analysts scroll through long timelines.
Timeline processing reports distinct searching, normalizing, storing, stopped,
timed-out, truncated, completed, and failed states through both visible labels
and screen-reader announcements. Outcome badges include text and symbols instead
of relying on color alone. Keyboard navigation is available for timeline tabs,
event cards, and the actions menu, and long usernames, role ARNs, resources,
IP addresses, and risk explanations wrap without losing evidence.

## 1.0.10

Build 43 makes **Fetch timeline** the clear primary action in the Investigation
Workspace. The button now uses a larger, solid high-contrast treatment with
distinct hover, pressed, keyboard-focus, and disabled/loading states, while
leaving timeline search behavior unchanged.

## 1.0.9

Build 42 replaces the low-contrast application icon with a bold EventTimeline
mark optimized for Splunk's 36 px and 72 px app drawer sizes. All standard and
alternate icon variants are included in the app's `static` directory, and the
version/build increment forces Splunk Web to invalidate previously cached icon
assets after upgrade.

## 1.0.8

Build 41 adds native UTC calendar and time controls to the Manual Timeline
Generator. Selecting **Custom range** enables explicit start and end pickers,
while anchor-based windows provide a calendar picker for the investigation
anchor. EventTimeline converts the selected values to UTC Splunk time bounds,
keeps the controls synchronized, and blocks incomplete or reversed ranges before
dispatching a search.

## 1.0.7

Build 40 fixes successful CloudTrail events being displayed as failed when a
Splunk search-time field extraction supplies `errorCode=success`. Both timeline
normalizers now discard explicit success markers while preserving real AWS error
codes and error messages. The Investigation Workspace also corrects legacy
stored rows whose outcome was previously saved as failure with `cl_error=success`,
so existing timelines render accurately after upgrade.

## 1.0.6

Build 39 adds administrator-controlled deletion to the Triggered Alerts queue.
Splunk administrators and users with the `cloudlens_admin` role can delete one
finding or bulk-delete selected findings after an explicit confirmation. The
operation removes the finding, generated investigation timeline, analyst triage
state, and deduplication claim with bounded, query-scoped KV Store requests.
Deletion controls remain hidden for analyst users, and Splunk collection ACLs
provide the server-side authorization boundary.

## 1.0.5

Build 38 hardens the macOS release process so AppleDouble `._*` metadata files
cannot be included in the app archive and misidentified by Splunk as XML views.
The release archive contains one `cloudlens/` root and no AppleDouble entries,
Finder metadata, local configuration, tests, or development files.

Build 37 fixes manual timeline searches that completed successfully in Splunk
but displayed no events in EventTimeline. The browser now tracks the dispatched
Splunk SDK job through completion and reads results from that same job, avoiding
the lifecycle race that could discard valid username, role, bucket, and resource
matches. **Stop search** cancels the active job directly.

The compact timeline profile remains the default and now performs bounded,
entity-specific candidate filtering before lightweight normalization. AssumeRole
expansion is excluded from this path. Analysts can opt into the enriched profile
with **Include role lineage** when parent and child role-session correlation is
needed; lineage UI is hidden for compact investigations.

## 1.0.4

Build 36 adds two investigation engines. The default compact engine searches
only the selected user or resource and omits AssumeRole expansion, account-wide
tamper correlation, and unused STS response extraction. Analysts can enable
**Include role lineage** before fetching when parent and child role-session
correlation is required. The query inspector always opens the selected engine's
resolved SPL in Splunk Search.

Each fetch now receives a unique hydration generation and profile. Timeline
rows are isolated to the active generation, stale completion callbacks cannot
replace a newer investigation, and both engines deduplicate CloudTrail event IDs
before storing rows or reporting the result count. This prevents mixed compact
and enriched results and keeps the displayed count aligned with stored events.

Build 35 displays complete affected user, role, source IP, resource, and account
values in the Investigation Workspace. Long IAM and STS ARNs wrap within the
Key Entities panel instead of being shortened at 90 characters.

Build 34 prevents investigation timelines from scanning every CloudTrail event
in a matching AWS account. Exact event, principal, username, source IP, and
resource terms are applied to the base source search before normalization.
Account ID remains a post-normalization correlation boundary, and placeholder
entity values are converted to nonmatching search terms. When exact event or
resource evidence exists, shared AWS service identities such as
`lambda.amazonaws.com` are excluded from the candidate terms. AssumeRole and
logging-tamper events are correlated only when they also match the selected
identity or resource, avoiding an unrelated account-wide candidate pass.

Build 33 ships `default/app.conf` with setup incomplete, as required by
Splunk AppInspect. Saving EventTimeline Setup marks the installed app configured
in `local/app.conf`, after the source and retention settings are persisted.

Build 32 improves Investigation Workspace timeline performance and reduces the
amount of sensitive CloudTrail data retained by EventTimeline.

- Applies inexpensive source, account, event, identity, IP, resource, and
  high-signal activity filters before CloudTrail normalization.
- Adds a focused timeline normalizer that extracts only the fields required for
  chronology, entity correlation, assumed-role lineage, outcomes, and pivots.
- Removes `_raw` before centralized correlation, sorting, and KV Store output.
- Stops persisting `cl_raw_event` in investigation records. Existing legacy raw
  payloads are removed in bounded, in-place migration batches during upgrade.
- Stores the source index and sourcetype with each normalized timeline event.
- Changes **Open Raw Event** to run a bounded Splunk search against the event's
  exact source, timestamp, account, and event ID. Raw evidence remains in the
  customer's Splunk indexes and is retrieved only when an analyst requests it.
- Preserves assumed-role lineage, resource and identity pivots, chronological
  CloudTrail event time, truncation reporting, and manual timeline generation.
- Adds regression coverage for candidate ordering, raw-payload exclusion,
  source metadata, migration safety, and on-demand evidence searches.

## 1.0.3

Build 31 adds an **Open query in Search** action to the Investigation Workspace.
It resolves the same saved-search SPL, entity arguments, source constraints, and
time bounds used by Fetch timeline, while removing the KV-write completion stage
so analysts can troubleshoot the query safely in Splunk Search.

Build 30 adds configurable triggered-alert retention to Setup. Administrators
can retain alerts for 7 through 15 days, with a 15-day default. The alert queue
and bounded daily cleanup use the same validated setting, while active
investigations and in-flight timeline hydration remain protected from deletion.

Build 29 hardens manual timeline identity matching across CloudTrail schemas.
Username, IAM identity, role, and role-session investigations now correlate
case-normalized aliases derived from principal, assumed-role, session issuer,
request target, and ARN path fields while preserving bounded candidate pruning.
Raw searches now explicitly invoke the Splunk `search` command before expanding
the source macro, ensuring identity candidate terms are applied instead of
scanning the full CloudTrail source.
Wildcard entity input is rejected so an analyst cannot accidentally dispatch an
unbounded identity search.

Build 28 adds an always-available Splunk query inspector to the manual timeline.
Every bounded window and fallback search shows its time bounds, acceleration mode,
SID, lifecycle status, progress, scan count, runtime, full SPL, and a safe local
link for opening the query in Splunk Search. Cached timelines retain the query
history that produced them.

- Renamed the user-facing product from CloudLens to EventTimeline.
- Renamed the saved-search alert action to **Create EventTimeline Finding**.
- Retained the `cloudlens` app namespace and internal knowledge-object names so
  existing installations and saved alerts continue to work after upgrade.
- Build 18 adds the EventTimeline app icon in all four Splunk standard and
  high-resolution app-list and menu variants.
- Build 19 makes timeline generation manual by default. Setup now provides an
  explicit automatic-generation toggle, alert ingestion no longer creates or
  retries timeline work in manual mode, and the workspace guides analysts to
  choose a window and fetch the timeline on demand.
- Build 20 corrects manual-fetch completion messaging by reading the hydration
  result count instead of the saved-search completion-row count. A successful
  zero-match investigation now reports that no additional activity was found.
- Build 21 installs the standard and high-resolution icon variants in both
  Splunk static-asset locations so the app navigation displays EventTimeline's
  icon instead of the generic app placeholder.
- Build 22 corrects the `hydration_truncated` KV Store schema type from
  `boolean` to AppInspect's supported `bool` declaration.
- Build 23 makes the Saved Search Guide the first page after installation,
  removes the blocking setup gate, and adds complete first-run instructions for
  prerequisites, roles, CloudTrail source validation, alert creation, manual
  timeline fetching, cluster deployment, and troubleshooting.
- Build 24 batches alert ingestion and hydration completion KV operations,
  separates analyst triage from server-owned hydration state, preserves
  CloudTrail event time for chronology, bounds correlation work, removes a
  redundant JSON parse, and paginates investigation timelines at 100 events.

## 1.0.2

This production-hardening release improves saved-search ingestion, CloudTrail
normalization, timeline hydration, deduplication, bounded UI rendering,
retention safety, assumed-role correlation, MITRE metadata persistence,
deterministic chronology, and Markdown export escaping.

Build 9 adds large-volume safeguards: exact alert-source searches when source
metadata is available, a macro fallback for aggregate alerts, a configurable
2,000-row hydration ceiling, a five-minute search runtime ceiling, visible
truncation diagnostics, and bounded manual-timeline sorting. Retry and
alert-anchor repair searches remain staggered to reduce scheduler contention
on shared Splunk search heads.

Build 10 adds an in-app Saved Search Guide with the result contract, a complete
CloudTrail role-activity example, alert-action setup steps, duplicate-control
guidance, and focused troubleshooting checks.

Build 11 makes the guide responsive within Splunk Web's fixed-width shell so
requirements, examples, and troubleshooting remain usable on narrow screens.

Build 12 contains narrow-screen overflow from Splunk's global navigation while
retaining local horizontal scrolling for the requirements table.

Build 13 hardens the manual timeline with early candidate filtering,
CloudTrail event-time provenance, event-ID deduplication, explicit truncation,
bounded cancellation, role-session evidence, anchor-relative chronology,
search telemetry, pagination, lazy raw events, accessible controls, and a
responsive investigation layout.

Build 14 corrects successful-event error normalization and preserves the total
duplicate count even when a manual timeline is capped.

Build 15 collapses Splunk's app rail on phone-sized screens so the manual
investigation controls retain a practical working width.

Build 16 applies the phone-width rail rule to Splunk versions that mount the
application navigation beside, rather than inside, the global navigation root.
Build 25 fixes manual identity searches for assumed-role activity. The timeline
now matches session issuer names and ARNs, role-session names, and the common
Splunk `user_name` extraction while retaining the bounded raw candidate filter.

Build 26 accelerates manual timelines by applying safe TERM and native
CloudTrail field predicates before normalization and by bounding candidates
before the expensive canonical extraction pass. The analyst-facing Stop search
control is always visible and cancels and disposes the active Splunk job.

Build 27 adds the Adaptive Hybrid Timeline Engine. Manual investigations use
Fast-mode, preview-free, server-bounded searches; large windows are divided into
newest-first slices; the first slice renders before analysts load older
coverage; all child SIDs remain visible and cancelable; completed searches use
a bounded five-minute memory-only cache; and the UI reports coverage, mode,
slice progress, scan count, runtime, truncation, and cache state. An optional
canonical locator macro supports summary-index or accelerated-data-model paths
with automatic raw-CloudTrail fallback.
