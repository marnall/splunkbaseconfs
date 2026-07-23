# Dashboard Health Checker for Splunk

Inventories the dashboards across your Splunk apps, extracts the SPL inside
them, scores each dashboard's health from 0–100 with a transparent rules
engine, and surfaces risky SPL patterns in an admin dashboard.

- **App folder:** `dashboard_health_checker`
- **App label:** Dashboard Health Checker
- **Version:** 1.0.0
- **Design:** 100% SPL. No custom search commands, no scripted inputs, no
  custom REST endpoints, no external network calls. Splunk Cloud / AppInspect
  friendly.
- **Storage:** KV store (primary). Optional summary index for historical trend.

---

## How it works

```
| rest data/ui/views        -> dhc_get_dashboards        (one row per view)
   -> regex/JSON extraction  -> dhc_extract_searches      (one row per search)
      -> rule battery        -> dhc_apply_search_rules    (per-search findings)
                             -> dhc_apply_dashboard_rules (dashboard findings)
         -> weighted score   -> Build Scores              (0–100 per dashboard)
            -> KV store       -> 3 collections
               -> Simple XML  -> Overview + Detail dashboards
```

Three scheduled searches run nightly (staggered) and write three KV collections:

| Saved search | Writes | Default schedule |
|---|---|---|
| Dashboard Health - Build Inventory | `dashboard_health_inventory` | 02:00 |
| Dashboard Health - Build Findings | `dashboard_health_findings` | 02:05 |
| Dashboard Health - Build Scores | `dashboard_health_scores` | 02:10 |

Build order matters (Scores reads Inventory + Findings), hence the stagger.

---

## Installation

1. Install the app:
   - **Enterprise:** unzip into `$SPLUNK_HOME/etc/apps/` (or install the
     `.tar.gz`/`.spl` via *Apps → Manage Apps → Install app from file*), then
     restart Splunk.
   - **Splunk Cloud:** upload the package through *Apps → Manage Apps → Install
     app from file*, or submit via the Cloud vetting workflow.
2. Confirm the KV store collections were created:
   `| inputlookup dashboard_health_scores` (empty result, no error = good).
3. Run the three build searches once, in order, as an admin user
   (*Settings → Searches, reports, and alerts → Run*), or wait for the schedule.
4. Open **Dashboard Health Checker → Dashboard Health Overview**.

### Want an instant demo (no real data)?

Run these once from *Settings → Searches, reports, and alerts*:

- `Dashboard Health - Generate Sample Data - Inventory`
- `Dashboard Health - Generate Sample Data - Findings`
- `Dashboard Health - Generate Sample Data`

The four shipped `sample_*` dashboards are also analysed live by the normal
build searches, so you get real findings on top of the seeded demo rows.

---

## Configuration

All tunables are macros (*Settings → Advanced search → Search macros*):

| Macro | Purpose | Default |
|---|---|---|
| `dhc_app_exclusions` | Apps to skip during discovery | a short list of noisy system apps |
| `dhc_max_searches` | Panel/search count that triggers the "too many searches" rule | `20` |
| `dhc_summary_index` | Summary index for optional trending | `summary` |

### Optional: historical trend line

1. (Recommended) create a dedicated index `dashboard_health` and point the
   `dhc_summary_index` macro at it. On Splunk Cloud, create the index via ACS /
   the Cloud console — this app does **not** ship `indexes.conf`.
2. Enable **Dashboard Health - Snapshot to Summary**.
3. The "Health score over time" panel populates as snapshots accumulate.

### Optional: runtime & usage enrichment

1. Enable **Dashboard Health - Enrich Runtime (optional)**.
2. The owner/run-as user needs read access to the `_audit` index.
3. It associates completed searches to dashboards via the audit `provenance`
   field (`UI:Dashboard:<id>`) and fills `avg_runtime`, `daily_runs`,
   `user_count` on the scores collection. Empty result is fine — those columns
   simply stay at 0.

---

## Permissions

- **Run-as / scheduling:** the build searches use
  `| rest /servicesNS/-/-/data/ui/views`. To see dashboards owned privately by
  other users, the running user needs the `admin_all_objects` capability (or
  equivalent). App-shared and globally-shared dashboards are visible to any
  user with `rest_properties_get`/`list_settings`. Re-own the three build
  searches to an admin account, or run them as an admin role.
- **KV store:** `read : [ * ]`, `write : [ admin, power ]` (see
  `metadata/default.meta`). KV writes require the `edit_storage_passwords`-free
  default KV capabilities held by admin/power.
- **Optional enrichment:** read access to `_audit`.
- No other elevated permissions are required.

---

## The rules

Severity weights: **Critical −25, High −15, Medium −7, Low −3**, clamped 0–100.

| Rule | Severity | Flags |
|---|---|---|
| DHC-C001 | Critical | No `index=` constraint |
| DHC-C002 | Critical | `index=*` |
| DHC-C003 | Critical | No time bounds (gated by dashboard time input) |
| DHC-C004 | Critical | Real-time search |
| DHC-C005 | Critical | `map` |
| DHC-C006 | Critical | `join` |
| DHC-C007 | Critical | `transaction` |
| DHC-C008 | Critical | Leading-wildcard search term |
| DHC-H001 | High | Subsearch overuse (≥2) |
| DHC-H002 | High | `append` / `appendcols` |
| DHC-H003 | High | `table` too early in the pipeline |
| DHC-H004 | High | `sort` without a positive limit |
| DHC-H005 | High | `dedup` before filtering |
| DHC-H006 | High | `regex` where a simpler filter may work |
| DHC-H007 | High | Filter applied after aggregation (late) |
| DHC-H008 | High | Expensive command before narrowing |
| DHC-M001 | Medium | `fields *` |
| DHC-M002 | Medium | `table *` |
| DHC-M003 | Medium | Raw `stats` where `tstats`/DMA may fit |
| DHC-M004 | Medium | Duplicate/repeated searches in one dashboard |
| DHC-M005 | Medium | Too many searches in one dashboard |
| DHC-L001 | Low | Field selection after aggregation |
| DHC-L002 | Low | `head` without a preceding `sort` |

Each finding stores: `rule_id, category, severity, message, recommendation,
spl (affected_spl), dashboard_id, search_id`.

---

## Known limitations

- **Heuristic parsing.** Extraction uses regex / JSON field matching rather
  than a full XML/Studio parser. Common constructs (inline `<query>`, base and
  saved-search `ref=` searches, Dashboard Studio `ds.search` queries) extract
  reliably; unusual nesting, heavily templated tokens, or exotic Studio
  datasources may not. Panel-to-search title pairing is approximate (searches
  are labelled `Search N`).
- **Base vs chained classification** is approximate; both surface, but the
  base/child relationship is not reconstructed.
- **`join` / `map` "on large searches"** can't be sized statically, so those
  rules flag the command regardless of data volume.
- **Runtime/usage** depends on `_audit` and the `provenance` field, which may
  be restricted or absent on some stacks; the columns stay at 0 if so.
- **"Recommendations accepted"** is presented as "Top recommendations";
  acceptance tracking is on the roadmap.
- The scoring model is intentionally simple and additive; it is a triage aid,
  not a substitute for review.

---

## Future roadmap

- Optional Python generating command for exact XML/Studio parsing (separate,
  vetting-gated build).
- True base-search dependency graphs and accurate panel titles.
- Recommendation accept/dismiss workflow stored in KV store.
- Per-rule enable/disable and custom weighting via a setup view.
- Auto-remediation suggestions (rewritten SPL) where deterministic.
- Drilldown from a finding straight into the Search inspector.

---

## Uninstall / cleanup

Removing the app leaves the KV collections defined by it; to drop the data:

```
| outputlookup dashboard_health_inventory  (run on empty result to clear, or use the KV REST API)
```

or delete via `| rest /servicesNS/nobody/dashboard_health_checker/storage/collections/data/...`.
