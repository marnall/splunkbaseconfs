# Dashboard Health Checker for Splunk

**Find the dashboards that are quietly hurting your search head — and know exactly why.**

Dashboard Health Checker scans every dashboard across your Splunk apps,
reads the SPL inside each panel, and grades each dashboard 0–100 against a
transparent library of performance and best-practice rules. The result is a
single admin view that ranks your worst dashboards and tells you, in plain
language, what to fix.

---

## Why you want it

Dashboards accumulate. Over months and years you end up with hundreds of them,
many written long ago, some with `index=*`, `join`, `transaction`, all-time
ranges, or unbounded sorts buried in a panel nobody has opened in a year — yet
they still run on a schedule and still tax your search head. Dashboard Health
Checker makes that hidden cost visible and prioritised.

---

## Features

- **Automatic discovery** of every Simple XML and Dashboard Studio view across
  all apps the running user can see.
- **SPL extraction** from inline panel searches, base/saved-search references,
  and Studio data sources.
- **Transparent rule engine** — 23 rules spanning data selection, time bounds,
  expensive commands, pipeline ordering, and acceleration opportunities.
- **0–100 health score** per dashboard with a clear Critical/Poor/Fair/Good/
  Excellent risk band. Every point of the score is explainable.
- **Overview dashboard** — KPIs, health distribution, top risky SPL patterns,
  and a ranked "worst dashboards" table.
- **Detail drilldown** — per-search scores, the full SPL, and the specific
  issues with remediation guidance for any dashboard.
- **Optional trend & usage** — historical score trending via a summary index,
  and runtime/usage enrichment from the audit log.
- **Sample data generator** for an instant, no-data demo.

---

## Built for Splunk Cloud

100% SPL. **No** custom search commands, scripted inputs, custom REST
endpoints, or external network calls. Results are stored in the KV store, so
there is **no index to provision**. The app ships no `indexes.conf`. This keeps
the Cloud vetting / AppInspect path clean.

---

## Requirements

- Splunk Enterprise or Splunk Cloud **9.x**.
- KV store enabled (default on).
- The build searches should run as an admin user so dashboards owned privately
  by other users are included (uses `| rest data/ui/views`).
- Optional runtime enrichment requires read access to the `_audit` index.

---

## Quick start

1. Install the app and restart (Enterprise) or upload via Manage Apps (Cloud).
2. Run the three **Dashboard Health - Build *** searches once, in order, as an
   admin (or wait for the nightly schedule).
3. Open **Dashboard Health Overview**.

Prefer a demo first? Run the three **Generate Sample Data** searches and open
the overview — no real data required.

---

## Scoring

Each dashboard starts at 100. Penalties per finding: Critical −25, High −15,
Medium −7, Low −3, clamped to 0–100. Bands: Excellent ≥90, Good ≥75, Fair ≥50,
Poor ≥25, Critical below 25. Nothing is hidden — the score is just the sum of
its findings.

---

## Support

This app is provided as-is. Issues, rule suggestions, and false-positive
reports are welcome through the support channel listed on the Splunkbase
listing page. See the bundled `README.md` for the full rule catalogue,
configuration macros, permissions, and known limitations.
