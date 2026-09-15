# Data handling and privacy

This document states what data leaves your Splunk environment when you use
Kyberis Threat Intelligence, what Kyberis does with it, what the app keeps
locally, and the controls you have. It expands the summary in
[Network requirements](network.md#what-data-leaves-splunk).

## Summary

| Data | Where it goes | When |
| --- | --- | --- |
| Indicator values from the event fields you select | Kyberis API (`base_url`, default `api.kyberis.ai`) | Only when `\| kyberis` runs or the alert action fires, and only for cache misses |
| Agent context (objective string, fixed stage strings, search id, batch counter) | Kyberis API | With every enrichment request |
| Your Kyberis API key | Kyberis API (`Authorization` header) | With every enrichment request |
| Indicator + verdict fields | Your own KV Store cache and (alert action only) an index you choose | Stays inside your Splunk environment |

Nothing is sent anywhere unless you invoke the command or the alert action:
the app ships no scheduled searches, no telemetry, and no background jobs.
`| kyberischeck` validates configuration locally and makes no API call.

## What is sent to Kyberis

Each enrichment request (`POST <base_url><api_prefix>/assessments/batch`,
up to 50 indicators per call) contains exactly:

- **Indicator values** — the deduplicated contents of the fields you point
  `| kyberis field=` or the alert action's *Fields* parameter at. Nothing
  else from the events: no other fields, no `_raw`, no host/source/sourcetype
  metadata, no usernames.
- **Agent context** — request metadata Kyberis uses for attribution and
  support:
  - `objective`: a fixed default string, or the `objective=` text typed by
    the user (validated 8–280 characters);
  - `requested_outcome` and `workflow_stage`: fixed strings compiled into
    the app;
  - `run_id`: the Splunk search id, sanitized to a safe character set —
    useful for correlating a support question with a specific search;
  - `step_id`: a per-search batch counter (`batch-1`, `batch-2`, …).
- **Authentication** — the `Authorization` header carrying the selected
  profile's API key.

### The raw SPL of your searches is never sent

This is runtime-enforced, not just policy: before every request, every
string in the outgoing payload is checked against the SPL text of the
running search, and a request that would contain it is blocked before
sending — the search fails with an explicit privacy error rather than
transmitting search text. The guard is covered by the app's test suite.

## Transport

All requests go directly from your search heads (never indexers or
forwarders) to `base_url` over HTTPS on port 443. Plaintext `http://` is
rejected except for local-development targets that never leave the machine,
and TLS certificate verification is always on, with no option to disable
it. See [Network requirements](network.md) for the full policy.

## What Kyberis does with the data

- **Verdict computation.** Indicator values are assessed against Kyberis's
  threat-intelligence holdings, which include licensed third-party
  intelligence sources — an indicator may be queried against those sources
  to produce its verdict.
- **Usage and billing records.** Kyberis records request metadata per API
  key — endpoint, batch size, timings, response status, and the agent
  context's `run_id`/`step_id` — for metering and plan enforcement. These
  usage records do not contain indicator values.
- **Investigation history.** Request and response bodies (indicators,
  verdicts, and the agent context including the objective string) may be
  retained by Kyberis as assessment history associated with your account,
  grouped by `run_id`.
- Retention periods for these records are governed by your Kyberis service
  agreement. For data-deletion requests, contact <support@kyberis.ai>.

## What stays in your Splunk environment

- **KV Store cache** — successful verdicts are cached in your own Splunk KV
  Store (`kyberis_ioc_cache`: indicator, verdict fields, fetch timestamp,
  the `base_url` they came from), expiring after `cache_ttl_seconds`
  (default 24 hours). See the
  [cache section of the command reference](kyberis-command.md).
- **Indexed events** — the alert action writes one event per enriched
  indicator (indicator + verdict fields + a link back to the triggering
  search) into an index you choose, subject to your own retention policies.
  See the [alert action reference](alert-action.md).
- **Search artifacts and logs** — enriched fields appear in search results
  and dispatch artifacts like any other search output. App logs are
  scrubbed of credential material as a hard guarantee and contain no
  indicator verdict payloads at the default log level.

None of this local data is transmitted to Kyberis.

## Credential handling

API keys are stored only in Splunk secure storage (`storage/passwords`),
encrypted at rest by Splunk. Keys never appear in `.conf` files,
dashboards, saved searches, search results, or logs — log output is
scrubbed of key material, including inside tracebacks. Named credential
profiles exist for per-team usage attribution. Full details in
[Credential setup](credentials.md).

## Your controls

- **What is sent**: you choose the fields; only their values are sent.
- **Whether anything is sent**: enrichment happens only when explicitly
  invoked; cached indicators are answered locally with zero API calls.
- **Objective text**: leave the default (recommended), or override with
  `objective=` — never paste sensitive material into it; it is transmitted
  and may be retained as described above.
- **Volume**: the alert action's *Max indicators* parameter caps how many
  indicators a single alert may send (default 100).
- **Cache**: `cache_ttl_seconds` bounds verdict staleness and local
  retention; `cache=false` bypasses reads for one search; deleting
  collection entries removes cached verdicts immediately.
- **Local cleanup**: cached verdicts live in your KV Store and indexed
  events in your indexes — both are yours to delete or age out.

## Questions

Contact <support@kyberis.ai> for privacy questions, data-deletion
requests, or a copy of Kyberis's data-processing terms.
