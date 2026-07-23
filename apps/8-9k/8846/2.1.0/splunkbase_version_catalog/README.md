# Splunkbase Version Catalog

A small Splunk app that builds and maintains a **local catalogue of Splunkbase
app versions** in a KV Store, and lets you compare the apps installed on your
search head against the latest releases published on Splunkbase.

It is written entirely with the Python 3 standard library (no bundled
third‑party packages), which keeps it self‑contained and straightforward for
Splunk Cloud AppInspect vetting.

## Version 2.1.0

- Adds a **Splunkbase Catalog Troubleshoot** menu item: a direct link to the
  modular input's configuration page in Settings > Data inputs, a table of
  every configured stanza and its `run_at`/`app_ids`/`fetch_all`/`max_apps`/
  `disabled` settings (pulled live via `| rest`, so it always reflects the
  current configuration), and a one-line catalogue freshness summary.

## Version 2.0.0

A deliberate reset back to a single modular input with two dashboards - no
SPL command, no import/export, no online/offline mode. Those were removed,
not merely hidden, because they added real complexity (and at least one
still-undiagnosed HTTP 404) on top of a scheduling bug in the input itself
that predates all of it.

- **Fixes the actual scheduling bug.** The input has shipped with
  `use_single_instance = true` since the very first version, which tells
  Splunk "don't restart this on a timer, I'll manage my own repeat schedule."
  But the script did a single pass and exited - there was no internal loop.
  Combined with an `interval` setting that was never even declared as a
  recognized argument, the net effect was unreliable, timer-independent
  scheduling. The input is now a genuine persistent daemon: it wakes up
  about once a minute and fires each configured stanza once at its
  `run_at` time (a fixed 24-hour `HH:MM`, default `03:15`, in the search
  head's local time zone), tracked in a small per-stanza checkpoint file so
  a mid-day restart (the process's own, or Splunk's) never causes a double
  run or a skipped day. This logic is unit-tested, including simulated
  restarts and an outage that spans past `run_at`.
- **Replaces `interval` (seconds) with `run_at` (HH:MM).** A seconds-based
  interval measured from "last run" drifts and doesn't match a fixed daily
  refresh; `run_at` does what people actually expect. Existing installs need
  to reconfigure this one field - see [Configure the input](#configure-the-input).
- **Removes** the `splunkbasecatalog` / `splunkbaseimport` SPL commands, the
  daily saved search, the Splunkbase Catalog Debug dashboard, the Overview
  dashboard's Update now / Import / Export / Configured-profiles panels, the
  run-status KV Store collection, and the online/offline `mode` setting.
  None of that is needed for the app's core job, and removing it also
  removes an entire class of failure (a live REST call from the SPL command
  to Splunk's own API to auto-select an input stanza) that was the leading
  suspect for a 404 report this version doesn't have the code path to
  reproduce.

If you need any of what was removed, it's still in git history; this version
prioritizes a small, reliable core over that feature surface.

## What it does

- A modular input (`splunkbase_catalog`) polls the public Splunkbase v1 API
  (`https://splunkbase.splunk.com/api/v1/app/...`) once a day at a fixed time.
- For each tracked app it records the latest release: version, release date,
  compatible Splunk platform versions, cloud‑compatibility and FedRAMP flags,
  whether the app is **archived** on Splunkbase (`is_archived` / `archive_status`),
  and the Splunkbase URL.
- The current state is upserted into a KV Store collection
  (`splunkbase_catalog`), keyed by the Splunkbase numeric app id, so re‑runs
  update in place instead of creating duplicates. This is the "catalogue".
- One event per app is also written to the index on every run
  (`sourcetype=splunkbase:catalog`) so you retain a version history over time.

## Install

1. Upload `splunkbase_version_catalog-2.1.0.spl` via **Apps > Manage Apps >
   Install app from file** (Splunk Cloud: **Manage Apps > Browse More Apps**
   for vetted apps, or the self‑service app install for private apps).
2. Restart Splunk if prompted.

The KV Store collection, lookup, dashboards and (disabled) input ship with the
app; nothing else needs to be created by hand.

## Configure the input

Go to **Settings > Data inputs > Splunkbase Version Catalog > New**, or clone
the shipped `splunkbase_catalog://default` stanza, and set:

| Setting     | Meaning |
|-------------|---------|
| `app_ids`   | Comma‑separated Splunkbase numeric IDs to track, e.g. `833,2890,2919`. The number is the one in the app's Splunkbase URL. |
| `fetch_all` | If `true`, paginate the entire Splunkbase listing instead of `app_ids`. Heavy — roughly one request per app. |
| `max_apps`  | Cap on apps retrieved when `fetch_all` is on. Default `200`. |
| `proxy_url` | Optional outbound proxy, e.g. `https://proxy.example.com:8080`. |
| `verify_ssl`| Verify TLS on Splunkbase calls. Default `true`. |
| `run_at`    | Fixed daily time to refresh, 24-hour `HH:MM` in the search head's local time zone. Default `03:15` if left blank. |

Enable the input. The process starts immediately but only *collects* at the
next `run_at`; it won't run right away on enable. If you want to see it work
sooner for testing, temporarily set `run_at` to a couple of minutes from now,
confirm data shows up, then set it back.

After the first run, open the **Splunkbase Catalog Overview** dashboard.

### Finding an app id

Open the app on Splunkbase; the id is the number in the URL, e.g.
`https://splunkbase.splunk.com/app/2919/` → id `2919`.

## Important: Splunk Cloud outbound network access

The input makes outbound HTTPS calls to `splunkbase.splunk.com`. Splunk Cloud
Platform restricts egress, so you may need to request that this destination be
allowed for your stack (Splunk Support / your stack's allow‑list), or set
`proxy_url` to an approved egress proxy. On Splunk Enterprise, just ensure the
search head (or wherever the input runs) can reach Splunkbase.

If outbound access is not possible from the indexing tier, run this app on a
heavy forwarder / search head that does have egress; the KV Store and
dashboards live with the app.

## Dashboards

- **Splunkbase Catalog Overview** — totals plus a filterable table of every
  catalogued app and its latest version. Click a row to open it on Splunkbase.
- **Installed Apps vs Splunkbase** — joins the apps installed on this search
  head to the catalogue and flags where a newer version exists.
- **Splunkbase Catalog Troubleshoot** — a link to the modular input's
  configuration page, a live table of every configured stanza's settings,
  and a catalogue freshness summary.

## Useful searches

Current catalogue:

    | inputlookup splunkbase_catalog_lookup

Installed apps with an available update:

    | `splunkbase_installed_compare` | search update_available="Yes"

Tracked apps that have been archived on Splunkbase:

    | inputlookup splunkbase_catalog_lookup
    | where in(lower(tostring(is_archived)),"true","1") OR lower(archive_status)="archived"
    | table title appid latest_version archive_status app_url

Installed apps that are archived upstream (migration candidates):

    | `splunkbase_installed_compare` | search archived="Yes"

## Archived status

Splunkbase marks apps that are no longer maintained as **archived**. The app
object exposes this as `is_archived` (boolean) and `archive_status` (e.g.
`live`). Both are stored in the catalogue, shown as a Status column and an
"Archived apps" tile on the overview, and surfaced as an "Archived?" column and
tile on the Installed‑vs‑Splunkbase dashboard so you can spot installed apps
that have been retired upstream.

Note: when tracking explicit `app_ids`, archived status is always returned by
the per‑app endpoint. In `fetch_all` mode the catalogue reflects whatever the
Splunkbase listing returns; archived apps may be under‑represented there, so
add their ids explicitly if you need to monitor them.

Version history of one app over time:

    sourcetype=splunkbase:catalog
    | spath appid | search appid="splunk_app_for_*"
    | timechart latest values(latest_version) by appid

## How matching works (and its limits)

The "Installed vs Splunkbase" comparison matches an installed app to a
catalogue entry when the **installed app's folder name** equals the
**Splunkbase string app id** (`appid`). This holds for many official add‑ons
but not for every app, because an installed directory name does not always
equal its Splunkbase id. Apps that do not match simply do not appear in the
comparison; track them explicitly by id to catalogue their versions.

## How scheduling works now

The input runs as a single persistent process per Splunk instance
(`use_single_instance = true` in the modular input scheme), not one process
per stanza restarted on a timer. On start it reads all enabled stanzas once,
then loops: every ~60 seconds it checks each stanza's `run_at` against the
current local time and a small JSON checkpoint file
(`<checkpoint dir>/splunkbase_catalog_<stanza>.json`, holding just
`{"last_run_date": "YYYY-MM-DD"}`) recording the last date it actually ran.
It fires a stanza when the current time is at or past `run_at` **and** it
hasn't already run today. This means:

- A restart at any point during the day (the process's own, or a full Splunk
  restart) never causes a duplicate run for that day - the checkpoint already
  shows today's date.
- If the process happens to be down exactly at `run_at` and comes back later
  the same day, it still catches up and runs as soon as it polls again -
  it doesn't wait for the next day.
- Multiple stanzas are checked independently in the same process and can
  have different `run_at` times.

## Notes for AppInspect / Cloud review

- Python 3 only; the input forces `python.version = python3`.
- No third‑party libraries are bundled.
- This is a `use_single_instance = true` modular input: a single long-running
  process per Splunk instance, expected behaviour for this scheme setting.
  It sleeps between checks (`time.sleep`) rather than busy-looping.
- The only persistent writes are to the KV Store (via the splunkd REST API
  using the session key passed to the input) and a small per-stanza JSON
  checkpoint file under the input's own checkpoint directory (never under
  `$SPLUNK_HOME/etc/apps` directly - Splunk supplies that path at runtime).
  The input also emits event output on stdout.
- TLS verification is disabled **only** for the loopback management endpoint
  (`https://127.0.0.1:8089`), which presents a self‑signed certificate.
  Outbound Splunkbase calls are verified unless `verify_ssl` is set to false.

## Uninstall / reset

Disable or delete the input, then delete the app. To clear the catalogue
without uninstalling:

    | outputlookup splunkbase_catalog_lookup
    (run against an empty result set, e.g. `| makeresults | where false | ...`)

or delete the collection contents from **Settings > Lookups**.
