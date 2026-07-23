# Data Heartbeat for Splunk

**Detect when your source types stop sending data — before someone else does.**

Data Heartbeat monitors the freshness of every source type ingested by your Splunk environment, flags stalled feeds against configurable thresholds, routes consolidated alert digests (one per destination), and keeps an audit trail of every gap and recovery.

---

## What it does

- **Continuous gap detection** — a scheduled saved search compares each source type's last-seen time against a per-sourcetype threshold and marks it `good`, `flagged`, or `pending`.
- **Importance-aware monitoring** — mark sourcetypes `vip`, `critical`, `high`, `medium`, or `low`; thresholds and surfacing key off importance.
- **Discovery catalog** — a bundled catalog of well-known critical sourcetypes (CrowdStrike, Okta, Palo Alto, AWS CloudTrail, Azure AD, and more) plus environment auto-discovery, so you can opt sourcetypes into monitoring quickly.
- **Consolidated alert digests** — a custom alert action (`heartbeat_dispatch`) sends **one consolidated digest per destination** (email, Slack, Microsoft Teams, or a generic webhook) listing all flagged sourcetypes in a fire — not one message per source — with per-action concurrency caps, rate-limit backoff, and a Settings-page global-default fallback.
- **Self-monitoring** — a Health Metrics search records detection-run stats, and a "Detection Stalled" tracked alert fires (visible under Activity → Triggered Alerts) if the monitor itself stops running.
- **Backup & restore** — a nightly job snapshots the monitored-sourcetypes **list** (sourcetypes, thresholds, importance, notes, action names); a restore search re-seeds it from the snapshot. Note: alert **target secrets** (the `heartbeat_alert_actions` global config and the per-sourcetype `heartbeat_alert_targets` overrides) are **not** part of this snapshot — re-enter them after a restore. Restore also blanks any legacy per-row `alert_action_config` so a pre-v1.4.0 snapshot can never re-leak a secret into the world-readable collection.
- **Audit history** — every status change, threshold edit, and importance/VIP toggle is recorded.

## Architecture

Data Heartbeat is a search-head app. It contains:

- **Three Simple XML dashboards** — Monitor, Settings, Audit History — built on Splunk Web's own jQuery + SplunkJS MVC (loaded via `require()`; the app bundles no JS frameworks of its own).
- **Seven KV-store collections** (all replicate across a search head cluster) — `monitored_sourcetypes` (the source of truth), `heartbeat_alert_actions` (global per-action alert config), `heartbeat_alert_targets` (admin-only per-sourcetype alert target secrets — webhook URLs/recipients), `heartbeat_audit_log`, `heartbeat_metrics`, `heartbeat_settings`, and `monitored_sourcetypes_backup` (the nightly DR snapshot). Settings, alert-action config, audit history, and metrics were CSV lookups in earlier releases; they migrate into KV automatically on first dashboard load after upgrade.
- **CSV lookups** — `heartbeat_catalog` (the bundled, read-only sourcetype catalog) and the cold-start *defaults* seeds (`*_seed.csv`) used to populate the KV collections on a fresh install.
- **One custom alert action** — `bin/heartbeat_dispatch.py` — invoked by the "Flagged Sources" alert; it makes outbound HTTPS calls to the Slack/Teams/webhook targets you configure and dispatches email through Splunk's own SMTP via a one-shot `| sendemail` search.
- **One custom REST handler** — `bin/heartbeat_admin.py`, registered at `/services/data_heartbeat/admin` — used by the dashboard's "Enable Monitoring" and "Send Test Alert" buttons to toggle saved-search state reliably. It is POST-only and capability-gated: **Enable/Disable Monitoring** requires `edit_search_scheduler` or `admin_all_objects`, while **Send Test Alert** (which makes an outbound call to an operator-supplied target) requires the stricter `admin_all_objects`.

Both Python files target Python 3 and are invoked by Splunk itself (the alert action via `alert_actions.conf`, the handler in-process via `restmap.conf`). The app spawns no subprocesses and ships no scripted/modular inputs.

## Prerequisites

- **Splunk Enterprise 8.2+** (8.x, 9.x, and 10.x supported) or **Splunk Cloud** (Victoria or Classic Experience).
- **Python 3** — provided by Splunk; no external Python install or pip packages required (the app imports only the standard library and Splunk-bundled modules).
- **KV Store enabled** — on by default on all modern Splunk deployments; the app stores its source-of-truth in a KV collection.
- A **search head** role (the app declares `targetWorkloads = _search_heads`); nothing deploys to indexers.

## Outbound Network Access

The custom alert action (`heartbeat_dispatch`) makes **outbound HTTPS calls only to the Slack, Microsoft Teams, and generic webhook URLs you explicitly configure**, and dispatches email through your Splunk instance's own SMTP relay over loopback (`127.0.0.1`). No data is sent to O11y Innovators Network or any third party you have not configured.

- **Splunk Cloud:** those destination hosts must be added to your outbound allow-list.
- **Splunk Enterprise:** ensure your search head's egress firewall permits HTTPS to those hosts.
- Outbound requests do **not** follow HTTP redirects, and validated public targets are checked against an SSRF blocklist (loopback / link-local / private / cloud-metadata ranges are refused).

## Installation

1. Download `SA-Data-Heartbeat-<version>.tar.gz` from the release page or Splunkbase.
2. Splunk Web → **Manage Apps → Install app from file** → upload the package → restart if prompted.
3. Open **Apps → Data Heartbeat** to land on the Monitor view.

### Splunk Cloud

- **Victoria Experience** — install via Self-Service App Install from Splunkbase, or upload a private vetted package.
- **Classic Experience** — install from Splunkbase through the Cloud Admin Console (support-assisted vetting).

The app declares `Enterprise` in `platformRequirements` and includes `_search_head_clustering` in `supportedDeployments`. Cloud compatibility is established by passing AppInspect cloud-vetting (the Splunkbase listing's `cloud_compatible` label), **not** a `platformRequirements` "Cloud" key — "Cloud" is not a valid key. See **Outbound Network Access** above for the egress allow-listing requirement on Cloud.

## First-run configuration

All scheduled searches ship **disabled** so nothing runs against your data without sign-off.

1. Open **Settings** in the app — set the detection threshold and cadence.
2. Use **Enable Monitoring** (Monitor view banner) or the per-search toggles in Settings to enable the scheduled searches.
3. On the Monitor view, click **Run Discovery** to scan for active sourcetypes, or **Add Sourcetype** to pick from the catalog / paste a list.
4. (Optional) Configure email/Slack/Teams/webhook targets in **Settings → Alert Actions**.

## Views

| View | Purpose |
|---|---|
| **Monitor** | Live status of every monitored sourcetype, stat cards, inline filters, per-row threshold/importance/alert-action editing. |
| **Settings** | Detection cadence, default threshold, scheduled-search toggles, global alert-action configuration. |
| **Audit History** | Log of every status change, threshold edit, and importance/VIP toggle. |

## Scheduled searches

All ship disabled; enable them from the app:

| Search | Cadence | Purpose |
|---|---|---|
| Source Type Monitor (Detection) | every 5 min | Recompute status for every monitored sourcetype. |
| Flagged Sources (Alert) | every 10 min | Fire the `heartbeat_dispatch` alert action with a consolidated digest of all flagged sources (1-hour per-sourcetype suppression). |
| Auto Discovery | daily | Surface candidate sourcetypes from saved searches, dashboards, and audit logs. |
| Health Metrics | every 5 min | Record detection-run health to the `heartbeat_metrics` KV collection. |
| Detection Stalled | every 15 min | Tracked alert if the Detection search hasn't run recently. |
| Nightly KV Backup / Restore from Backup | nightly / on-demand | Snapshot and restore the monitored-sourcetypes collection. |

## Permissions

- **Read:** all authenticated users (except the `heartbeat_alert_actions` collection — see below).
- **Write:** `admin` and `sc_admin` only. Non-admins get a clearly-labeled **read-only view**: every write control (add/remove sourcetypes; edit threshold/importance/notes/alert-action; change settings; toggle scheduled searches) is hidden or inert, and the KV-store collections are write-restricted to `admin`/`sc_admin`. The custom REST endpoint additionally requires a capability: **Enable/Disable Monitoring** needs `edit_search_scheduler` or `admin_all_objects`; **Send Test Alert** requires the stricter `admin_all_objects`.
- **Secrets:** alert target secrets (Slack/Teams/webhook URLs, email recipients) live in two **admin-read-only** KV collections — `heartbeat_alert_actions` (global per-action config) and `heartbeat_alert_targets` (per-sourcetype overrides). Non-admins cannot read either, even though they keep the read-only Monitor view (which shows only the non-secret action *name*). The nightly DR copy `monitored_sourcetypes_backup` is likewise admin-read-only.

## Troubleshooting

**Dashboard stuck "Loading…"** — check the browser console for a JS error; KV-store may still be initializing on a fresh install (wait ~60 s).

**Empty dashboard / "Couldn't load source types"** — confirm the KV collection exists:
`| rest /servicesNS/nobody/SA-Data-Heartbeat/storage/collections/config | search title="monitored_sourcetypes"`

**Saved searches won't run** — all scheduled searches ship disabled. Enable them from the app's Settings page (which sets both `disabled` and `is_scheduled`).

**Discovery / Detection returns nothing for internal sourcetypes** — Detection uses `| tstats` and the on-demand **Run Discovery** button uses `| metadata`; both only return sourcetypes in indexes the running user can search. (The scheduled daily **Auto Discovery** search instead reads `| rest` over saved/correlation searches and dashboards plus `index=_audit`.) The detection user needs read on `index=*` and `index=_*`.

## FAQ

**Does it consume a lot of search resources?** No — Detection uses `| tstats` over tsidx (not an event scan) every 5 minutes by default. The on-demand **Run Discovery** button uses `| metadata` (bucket metadata only); the scheduled **Auto Discovery** search (daily) instead uses `| rest` over saved/correlation searches and dashboards plus `index=_audit`. All are tunable.

**Can I extend the catalog?** Yes — edit `lookups/heartbeat_catalog.csv`. Format: `category,match_type,sourcetype,importance,threshold,notes`; `match_type` is `exact` or `regex`.

**Does it touch ingestion?** No. It reads bucket metadata and lookups; it does not modify `props.conf`/`transforms.conf` for indexing.

**Multi-search-head?** KV-store collections replicate across a search head cluster. Deploy via the SHC deployer.

## Uninstall

Removing the app does **not** automatically delete its KV-store data, lookups, or logs. To clean up fully:

1. **Disable monitoring first** — in the app, use the Settings toggles (or the Monitor "Enable Monitoring" control) to disable all scheduled searches, so nothing fires during removal.
2. **Delete the stored data BEFORE removing the app.** **All app state — including saved Slack/Teams/webhook URLs and email recipient lists — lives in KV-store collections, which are NOT deleted when the app directory is removed.** Until you delete them, those secrets persist on the instance. Delete each collection via REST **while the app still exists** (the path is namespaced to the app, so it returns 404 once the app is gone):
   `/servicesNS/nobody/SA-Data-Heartbeat/storage/collections/data/<name>` (HTTP DELETE) for each of:
   `monitored_sourcetypes`, `heartbeat_alert_actions` (webhook/recipient secrets), `heartbeat_alert_targets` (per-sourcetype webhook/recipient secrets), `heartbeat_audit_log`, `heartbeat_metrics`, `heartbeat_settings`, and `monitored_sourcetypes_backup`.
3. Now remove the app (Splunk Web → **Manage Apps**, or `./splunk remove app SA-Data-Heartbeat`; on Cloud, via ACS).
4. App logs (`heartbeat_dispatch.log`, `heartbeat_admin.log`) remain under `$SPLUNK_HOME/var/log/splunk/` and can be removed manually on Enterprise.

## Support

- **Vendor:** O11y Innovators Network
- **Issues:** https://o11yinnovatorsnetwork.com
- **Email:** support@o11yinnovatorsnetwork.com

## License

Apache License 2.0 — see `LICENSE.txt`. Third-party notices in `NOTICE`.
