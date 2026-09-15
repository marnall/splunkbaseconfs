# WALLIX Advanced Monitoring (`SA-wallix-advanced-monitoring`)

Dashboards and detections for **WALLIX Bastion** privileged access. Companion
to `TA-wallix-bastion`, which does the parsing and the CIM mapping. Install
that add-on first: without it these views have nothing to read.

| | |
|---|---|
| Version | 1.0.0 |
| Splunk | Enterprise >= 8.2, Splunk Cloud |
| Requires | `TA-wallix-bastion` >= 1.0.0, on the same search heads |
| Install on | search heads only |
| Scripts / binaries | **none** — dashboards, searches and macros only |
| License | Apache-2.0 |

---

## 1. What you get

**Four Dashboard Studio views**

| View | Answers |
|---|---|
| Privileged Access Overview | Who is connected right now, what is trending, which privileged accounts are hottest |
| Session Investigation | What happened *inside* a session — commands, windows, file transfers, clipboard, recording integrity |
| Administration Audit Trail | Who changed the Bastion's own configuration, and what they deleted |
| Security Signals | Forbidden patterns, clipboard exfiltration, integrity failures, file transfers, killed sessions |

**Nine detections**, shipped unscheduled: ordinary alerts over the
sourcetypes and eventtypes the add-on produces. They are enabled as knowledge
objects, so you can run each one by hand and judge its threshold before
turning scheduling on.

---

## 2. Setup

Install `TA-wallix-bastion` first. This app reads the sourcetypes and
eventtypes that add-on produces.

**Splunk Cloud.** Install from the Splunkbase tab in Splunk Web.

**Splunk Enterprise, from Splunkbase.** *Apps > Find More Apps*, search
`WALLIX Advanced Monitoring`, *Install*. Or download the archive and use
*Apps > Manage Apps > Install app from file*.

**Splunk Enterprise, by hand.**

```bash
sudo tar -xzf SA-wallix-advanced-monitoring-1.0.0.tar.gz -C $SPLUNK_HOME/etc/apps/
sudo $SPLUNK_HOME/bin/splunk restart
```

**Search head cluster.** Place it in the deployer's `etc/shcluster/apps/` and
push with `splunk apply shcluster-bundle`.

Install on the **search heads** only. Nothing in this app belongs on an
indexer, and it carries no configuration of its own: the index is selected by
`TA-wallix-bastion`'s `wallix_bastion_index` macro, which you override there if
you use a different index name.

Two macros are yours to set, in `local/macros.conf`, before the detections that
depend on them mean anything:

| Macro | What it defines |
|---|---|
| `wallix_business_hours` | the hours outside which a privileged session is worth an alert |
| `wallix_critical_targets` | the targets whose first-time access is worth an alert |

---

## 3. Detections

The nine detections ship with `enableSched = 0`, which is what keeps them from
firing; the cron line is the cadence they will use once you turn scheduling on.
Each is an ordinary alert: it produces result rows, and can fire any alert
action installed on this search head.

They are listed under **Detections > Detection searches**, which is the app's
Reports page filtered to this app. The second entry, *Manage detections*, is
Splunk's own saved-search manager - use it for permissions and scheduling, and
be aware of one trap there: it has an **Owner** filter that Splunk remembers
per user and that defaults to your own account. The detections are owned by
`nobody`, as every app-shipped object is, so an Owner filter left on your
account shows *0 Searches, Reports, and Alerts*. Set **Owner: All**. The
Detection searches page has no owner filter and is the reliable list.

They are **not** shipped `disabled = 1`. That would disable the knowledge
object, so the search would not appear and `| savedsearch "<name>"` would
answer *Unable to find saved search* - leaving you no way to run one by hand
and see what it returns before deciding to enable it. Run each one first:

```spl
| savedsearch "WALLIX - Clipboard data copied out of a privileged session"
```

It uses the detection's own 60-minute window ending 10 minutes ago, so no time
picker is involved.

Review each threshold against your own volume before enabling; the two most
volume-sensitive are *New operator to target pair* (noisy for the first month
while the baseline fills) and *Burst of vault credential checkouts* (whose
threshold of five depends entirely on whether you have automation checking
out secrets).

Two things about running them by hand. `| savedsearch` takes its time range
from the **search bar's time picker**, not from the detection's own
`dispatch.earliest_time` - set the picker to *Last 60 minutes*, or the
detection will be evaluated over a window it was never written for, and the
ones that reason about a burst will return nothing. And *New operator to target
pair* comparing against 30 days of history returns nothing once every pair in
your data has been seen before: that is the detection working, not failing.

---

## 4. Checking the install

The four views draw on the add-on's macros and eventtypes, so a blank dashboard
almost always means the data is not there yet rather than the app being broken.
Work down in this order:

```spl
index=wallix_bastion | stats count by sourcetype
`wallix_bastion_sessions` | stats count
| tstats count from datamodel=Authentication
  where Authentication.authentication_service="wallix:bastion"
```

The first empty one names the layer at fault: no events at all is collection,
events on the bare `wallix:bastion` sourcetype is the add-on missing from the
parsing tier, and an empty data model with a populated macro is the CIM index
scope - all three are covered in the add-on's own README, section 2.

---

## 5. Extending it

The four views are Dashboard Studio JSON under
`default/data/ui/views/`. Clone one into `local/` before changing it: an app
upgrade replaces everything in `default/`.

A new detection is one stanza in `local/savedsearches.conf`. Write it
`disabled = 0` with `enableSched = 0` - enabled as a knowledge object so it can
be run by hand, not scheduled - with a `dispatch.earliest_time` /
`latest_time` pair matching its cron, and state its threshold in the
description so whoever enables it knows what they are agreeing to.
