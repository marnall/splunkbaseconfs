# Criminal IP TI Feed

Downloads the Criminal IP malicious-address feed, matches it against your firewall
traffic logs every 10 minutes, and reports what it finds on seven dashboards plus
optional Slack alerts.

This file is for whoever is holding the app's files: installing it, keeping it running,
or working out why a screen reads zero. It is not a description of how the app is built.
Every check named below is one the app performs on itself, so you should not have to
write SPL to answer any of the questions here. It is also the release notes file that
`app.manifest` points to; the version table is under **Upgrading**.

## Before you install

- **Splunk Enterprise, self-managed, on Linux.** Collection runs as a shell script
  (`bin/ti_feed_sync.sh`), so Windows indexers and Splunk Cloud are not supported.
  Splunk's bundled Python 3 is used; nothing is installed with pip.
- **A single instance, or a search head that also indexes.** `default/indexes.conf`
  creates the summary index. On a distributed install create `cip_ti_matches` on the
  indexers as well, or matches are written nowhere and every screen reads zero with no
  error.
- **A Criminal IP TI Feed License (API Key)**, the CTIDB license key, and outbound HTTPS from the Splunk host to
  `dl.criminalip.io:443`. The download runs on the search head that hosts the app.
- **For Slack alerts**, outbound HTTPS from the same search head to
  `hooks.slack.com:443`. The alert action runs there, not on an indexer.
- **An account with `admin_all_objects`** to save the Set up screen once. Nothing
  narrower can do it: saving writes three conf files and one credential.
- **FortiGate is the reference product.** Other products get detection, alerts and the
  dashboards through a field mapping macro (see **A firewall that is not FortiGate**).
  One feature stays FortiGate only: the **Raw firewall events** workflow action
  matches on FortiGate raw field names. The **Investigate** screen classifies
  through the same adapter as detection, so it works on any product you have
  adapted; only its vendor-native forensic columns (service, application,
  policy, duration, country) stay blank.

## Getting to a working detection

1. Install the `.spl` (Splunk Web, **Apps > Manage Apps > Install app from file**, or
   `splunk install app TA-cip-ti-feed.spl`).
2. Open the app. Splunk sends you to **Set up**, because nothing is configured yet.
3. Fill in Set up top to bottom and press **Save**:
   - **Criminal IP TI Feed License (API Key).** Required. This is the TI Feed product
     license, not a key for another Criminal IP product. Nothing downloads without it,
     and the app will still let you save, so check Overview afterwards.
   - **Firewall product.** This decides how the log source is narrowed. Getting it wrong
     makes detections zero with no error.
   - **Log sources.** The index and sourcetype your firewall actually writes to, one row
     per source. The **What will be searched** box shows the exact two lines that will be
     saved; if they look wrong, the product selector above is the usual cause, not the
     index.
   - **Slack.** Leave the webhook empty to use the dashboards without Slack.
4. **Start the first feed download.** Saving the key does not run the download. The
   scripted input runs on its own schedule, every 3 hours, so on a fresh install the
   feed can stay empty for up to 3 hours after Save and Overview keeps saying the feed is
   empty. To run it now: **Settings > Data inputs > Scripts**, open
   `ti_feed_sync.sh` and press Save; that reloads the input and reschedules it.
   **Health > Collection status** shows the run once it has happened.
5. Open **Overview**. Within about 10 minutes of the feed arriving it either shows
   detections or names which precondition is missing.

Detections land in `index=cip_ti_matches`, one row per asset, malicious address and
10-minute window.

## When a screen reads zero

Zero is a legitimate answer, so the app separates "nothing happened" from "nothing was
checked". Read these in order; each one is a banner or panel that tells you which case
you are in.

| Where | What it means | What to do |
|---|---|---|
| Overview: *The threat feed is empty* | No license key, or the first download has not run yet | Enter the key in Set up, then reload the input (step 4 above) |
| Overview: *Detection is stopped … reset to the shipped placeholder* | An upgrade overwrote what gets searched | Open Set up and press Save |
| Overview: *No firewall traffic in the last 30 minutes* | The searched sources are wrong, or the logs stopped | Check the log sources in Set up |
| Overview: *This account cannot check whether detection is running* | Your role cannot search `_internal` | See **Permissions** below |
| Health: **Collection status** | The state of the download itself | Follow the status word |
| Health: **Traffic source fields** | Whether your logs carry the fields detection needs | See **A firewall that is not FortiGate** |
| Health: **Scheduler coverage** | Whether the six scheduled searches actually ran | A gap here is traffic that was never examined |
| Health: **Log arriving, by firewall** | Per-device arrival, so one dead firewall is visible | LATE or missing rows name the device |

A quiet Overview is not a quiet network. Health exists to be read before concluding that
no detections means no threats.

## Files you may edit

| Path | What it is |
|---|---|
| `lookups/internal_networks.csv` | Your internal CIDRs. Traffic between two internal addresses is dropped before the feed is consulted. This is a cost filter and does not change results. |
| `lookups/ti_egress_allowlist.csv` | Outbound destinations to ignore. Optional; empty is normal. |

**An upgrade reverts both of these**, because they ship in the package at the same
paths. Keep your version at `local/internal_networks.csv` and
`local/ti_egress_allowlist.csv`. The app copies from `local/` on the next collection run
and never deletes, so your rows come back on their own.

## Files you should not edit

| Path | Why |
|---|---|
| anything in `default/` | Set up writes `local/`, and `local/` wins. Editing `default/` is undone by the next upgrade. |
| `lookups/cip_ti_inbound.csv`, `lookups/cip_ti_outbound.csv` | The downloaded feed. Replaced every 3 hours. |
| `lookups/cip_ti_roster.csv`, `cip_ti_self_egress.csv`, `cip_ti_retro_seen.csv` | Written by scheduled searches. `cip_ti_retro_seen` is the one file that grows without bound; see **Capacity**. |
| the saved searches, through Splunk Web | Editing one in the UI copies the whole stanza into `local/savedsearches.conf`. From then on reinstalling the app never updates that search, and it keeps running the old version forever. Health detects this for the detection search only; for the others compare `local/savedsearches.conf` against the shipped file after each upgrade (see the checklist under **Upgrading**). |

## A firewall that is not FortiGate

FortiGate is the reference product and needs nothing extra. For Palo Alto PAN-OS or
Cisco ASA/FTD, Set up shows a ready block under **Adapter for this product**: copy it
into `local/macros.conf`. For anything else the same box lists what your own version has
to produce. Three macros go together; changing one alone makes detections zero with no
error:

| Macro | What it is | If you skip it |
|---|---|---|
| `cip_ti_traffic` | The search base (index, sourcetype, traffic filter) | Nothing is searched |
| `cip_ti_traffic_local` | Traffic where the firewall itself is the endpoint | The detection search scans the wrong index every 10 minutes. A product with no such surface needs a valid search that matches nothing, not an empty macro |
| `cip_ti_normalize` | Maps vendor field names and action words to the contract fields below | `fw_class` reads `unknown` on every row, so no alert scope matches and the screens say no contact |

After that macro runs, these fields must exist:

- `srcip`, `dstip`, `dstport`: addresses and destination port
- `devname`: the firewall that logged it
- `fw_class`: `established` | `attempted` | `blocked` | `neutral` | `unknown`
- `fw_path`: `internet` | `site-to-site` | `remote-access`
- `fw_surface`: `perimeter` | `firewall-itself`
- `sentbyte`, `rcvdbyte`: byte volume. Set one to `null()` if your product reports a
  single total; detection is unaffected and two columns read blank.

Two rules hold whatever the product is. Received bytes above one control packet mean the
session completed: for reset/timeout endings the shipped rule is `rcvdbyte` of at least
`cip_ti_established_min_rcvdbyte` (61 bytes, overridable in `local/macros.conf`), so a
bare RST reply is a refusal while data that arrived before a reset still counts. And if
you cannot tell, it is `unknown`; never guess `established`.

**Checklist before pasting a PAN-OS adapter.** Each of these differs per site, and a
wrong value fails silently:

1. Whether `action` carries raw values (`allow`, `deny`, `drop`, `reset-*`) or CIM values
   (`allowed`, `blocked`). It depends on the add-on version. A wrong choice makes denied
   sessions `unknown`, and severity then rates them one tier higher, not lower.
2. The real value list of `session_end_reason` (`aged-out`, `policy-deny`,
   `tcp-rst-from-*`).
3. Which side the byte counters describe. Swapping direction turns a 260-byte scan with
   no reply into a completed session.
4. What `dest_translated_ip` reads when there is no NAT. Some deployments send `0.0.0.0`;
   left as is, the our asset column reads `0.0.0.0` on every row.
5. Zone names. The `fw_path` expressions in the adapter are examples; GlobalProtect and
   IPsec both use `tunnel.N` interfaces, so split on zone, not on interface.

PAN-OS writes management, IKE and portal traffic to system and GlobalProtect logs, not to
`pan:traffic`, so the `firewall-itself` surface covers only data-plane traffic into the
management zone.

**Cisco ASA/FTD.** One session is two messages (`302013` built, `302014` teardown); the
adapter keeps teardown and deny messages only. `rcvdbyte` cannot be filled: teardown
reports one total, which the adapter puts in `sentbyte`, and Health reports `rcvdbyte`
as missing, which is expected on ASA. Source and destination are inferred from the lower
port on teardown, so peer-to-peer sessions on two high ports can come out reversed.
Bytes are reported at teardown, so a long session is detected when it ends, not when it
starts.

After editing `local/macros.conf`, restart Splunk or open `/debug/refresh` in Splunk
Web so the new definitions are read. Confirm the result on **Health > Traffic source
fields**. Every required field must read OK before the numbers on the other screens
mean anything.

## Permissions

- **Saving Set up** requires `admin_all_objects`.
- **Collection status on Health and Overview, and Slack delivery on Alerts,**
  require a role that can search `_internal` (its `srchIndexesAllowed` must include
  `_*`). Splunk's stock `user` and `power` roles cannot: `index=_internal` returns zero
  rows to them with no error. Without it the app **hides** those judgments and says
  which ones it hid, rather than reporting zeros that look like a dead pipeline. On
  Alerts that means the messages accepted, failed and held back, the delivery chart and
  the last message line are replaced by a banner; the scope table and the detections
  that alerting covers stay visible.
- **Everything else** works with the stock `user` role: the detection tables, the feed
  counts, per-firewall arrival, the field-fill check, and the alert scope table.

## Security and data flows

What the app stores, where it connects, and what leaves the instance. All of it is
readable in `bin/` and `default/`; this is the summary.

**Timezones.** Every timestamp on the screens and the Slack card is rendered by Splunk at
search time, so a non-KST deployment shows its own local times. The card and the scheduled
searches run as the app (no owner, so no user timezone preference) and therefore use the
server's clock; the screens use each viewer's. Only the strings built with `%Z` carry a
timezone label: the card's `Seen:` line and the `first contact`/`last contact` columns of
the sweep lookup. The other columns are unlabelled, and four of them are strings frozen at
the clock of the search that wrote them rather than re-rendered for the viewer: `reported
(server time)`, `first contact` and `last contact` on the sweep table, and `last seen
(server time)` on the egress-address table. The feed's own clocks are fixed and parsed
with explicit offsets: sighting timestamps (`first_seen`/`last_seen`) are KST
(`cip_ti_feed_seen_tz`, +0900) and version stamps (`feed_version`, `generated_at`) are UTC
(`cip_ti_feed_version_tz`, +0000), both measured on 2026-08-26 (see the comments in
`default/macros.conf`). Either can be redefined in `local/macros.conf` if the vendor
pipeline changes; the quotes are part of the value, so a redefinition reads `definition =
"+0000"`. The retroactive sweep's schedule (04:20) is server local time.

**Secrets.** Set up stores the Criminal IP TI Feed License (API Key) and the Slack webhook in Splunk's
credential store (`storage/passwords`, entries `cip_key` and `slack_webhook`), encrypted
at rest. Both entries are readable by the `admin` role only: `metadata/default.meta`
sets that for new installs, and every Save re-applies it to the two entries through
their ACL. Roles with `admin_all_objects` bypass object ACLs and can still read them. If
the ACL write fails, Set up lists it under "Not written" as `read stays open`, and the
entry remains readable by any role holding `list_storage_passwords` until the next
successful Save. Saving the key does not run the download: the first download happens
at the next scheduled run of `ti_feed_sync.sh` (every 3 hours, `interval = 10800` in
`default/inputs.conf`) or as soon as the script input is saved in
**Settings > Data inputs > Scripts**. Two plaintext fallbacks exist for the license key, for
collection only: `local/cip_ti_feed.key` (one line) and the environment variable
`CRIMINALIP_TI_KEY_LIVE` on the splunkd process. The collector tries the credential
store first, then the file, then the variable, and logs which one it used
(`event=key_source`). A webhook typed into an alert's own **webhook_url** parameter takes
precedence over the encrypted one. The collector and the alert action each read their
own entry (`storage/passwords/:cip_key:` and `:slack_webhook:`), never the whole
credential list, in the app namespace over loopback (`127.0.0.1:8089`, certificate check
disabled for the self-signed endpoint) using the session token Splunk passes them.
Neither the key nor the webhook is written to any log; the collector logs the key length
only.

**Outbound connections.** Two, both TLS with certificate verification:

| Destination | When | What is sent |
|---|---|---|
| `dl.criminalip.io:443` | every 3 hours | The license key as a URL query parameter (`key=`), so it appears in any proxy or URL log on the path; profile, confidence and limit parameters; a browser User-Agent string, because the vendor's edge rejects the default Python one |
| `hooks.slack.com:443` | when an alert fires | The message below |

**What a Slack message contains.** One message per alert run, built from the run's result
rows. The blocks, in this order: a header; one section per match, where a match is one
(malicious IP, direction) key; a **Not shown** section when more rows came back than the
message can carry; and a final **Alert run** section. The message has no small grey
context blocks, so everything is body size on a phone.

The header reads `up to <severity>` followed by the number of matches, malicious IPs and
assets. `up to` means the highest severity among all rows of the run, not the severity of
every row. The retroactive sweep's header starts with a clock instead of a siren, counts
`past contacts` and ends with `(not new traffic)`.

Each match section carries these lines in this order. A line is left out when it has
nothing to say; the order never changes.

1. The key line: a coloured circle, the malicious IP, the direction and the severity word.
   Severity and its colour appear only here and in the Not shown list. Asset lines carry
   no colour.
2. **Firewall**: sessions completed (bold), with no reply and denied for that key, then
   the event count. Rows with no recorded outcome show `allowed`, because those two
   outcomes were not split when they were written. A key with none of the three reads `no sessions counted`.
3. **Note**: only when something changes the reading: the address is one of your own
   public addresses, the traffic was aimed at the firewall itself, or it came over a VPN
   link.
4. **Our asset** or **Our assets (K)**: a label line, then one line per asset. K counts
   distinct addresses; an inbound NAT key such as `a, b` counts two. Each asset line starts
   with a warning sign when that asset had a completed session and with a bullet
   otherwise. The warning sign means one thing everywhere on the card: a session
   completed. The line then gives the asset name and address (`name (address)` when the
   log carries the name), its own completed, no reply and denied counts, its first and
   last contact time, its bytes sent and received (only for assets with a completed
   session), and its destination ports when they differ from the match's. Up to 10 lines,
   then `and N more assets`. Rows without per asset data (the retroactive sweep, rows from
   older versions, corrupt data) show the address only on each line; the shape stays the
   same.
5. **Asset name(s)**: names that were not placed on an asset line (all of them for the
   sweep). A `|` or `;` inside a name is shown as a space on the asset line and that
   counts as placed. Names are never masked.
6. **Seen**: first and last contact of the key within the alert's window (the last hour
   for live alerts, 30 days for the sweep), so "first" is not the first contact ever, with
   `(N days ago)` from one day on.
7. **Seen by**: the firewall(s) that logged it.
8. **Data**, or **Data (all assets)** when K is 2 or more: bytes sent by us and sent to
   us, only when a session completed. Bytes of keys with only no reply or denied outcomes
   are SYN and RST sizes and are shown nowhere on the card.
9. **Dest ports**: up to 20, then `, and N more`.
10. **Threat feed**: the feed profile, the confidence and the feed last sighting, on one
    line.
11. **Reason**: the feed's reason string, first 120 characters.
12. **Open**: the **Investigate** and **IP lookup** links for that IP.

The **Not shown** section lists the circle, IP and direction of every row that did not
get a section: rows beyond **max_rows** (default 20, ceiling 50), and the message holds at
most 44 sections. The **Alert run** section is always the last block and is the only place
with the link to the run's search results, worded `Results in Splunk (kept 24 hours)`. The
24 hours is Splunk's default `alert.expires` for the results of a saved search; this app
does not change it. When no usable address exists it reads `no link, results kept 24 hours
in Splunk` and the Open lines are left out too; the card itself never tells the analyst
how to fix that. The links use the **Splunk web address** from Set up, or the origin of
Splunk's own results link when that is not loopback. Set up says it under that field:
"Host and port only, no path. Without it the Slack card has no links unless Splunk fills
in a reachable results link."

Asset addresses are shown in full by default; `mask_internal_ip=1` on the alert action
masks them (IPv4 `a.b.x.x`, IPv6 first two groups). The malicious IP, asset names,
firewall names and ports are never masked.

The per asset data travels in the alert search's `asset_lines` field, 13 fields per asset:
address, completed, no reply, denied, events, last epoch, first, last, ports, sev_tier,
sent, received, names. The renderer does not read `sev_tier`; the field stays so that
older lines keep parsing. A copy of the 0.5.17 or 0.5.18 stanza in
`local/savedsearches.conf` keeps sending 9 or 12 field lines: the card still renders, the
asset lines show addresses only and the names move to the **Asset name(s)** line. Delete
that stanza from `local/` and the shipped one takes over (checklist step 2 under
**Upgrading**).

The notification preview text, what a locked phone shows, is the header followed by the
search name. It no longer starts with `CIP TI Feed alert:`; a Slack keyword notification
set on that prefix should be moved to the search name, which is still present.

**System token.** The scripted input runs with `passAuth = splunk-system-user`. The
same token lets the collector repair the search macros when an upgrade reset them
(`event=macro_heal`), writing `local/macros.conf`. Set up writes conf files and
credentials as the saving administrator.

**Sharing.** The macros (`cip_ti_traffic`, `cip_ti_index`, `cip_ti_severity` and the
rest), the lookup definitions and the Slack alert action are shared system wide, so any
role that can run a search can read the macro definitions, which contain your firewall
index and sourcetype names. The lookup files themselves (feed, internal networks, egress
addresses) are app local and not exported.

**Logs.** The collector's stdout and the Set up handler's log go to `index=_internal`
(sourcetypes `cip:ti:feedsync` and `cip:ti:setup`). Detections go to `cip_ti_matches`
and include internal asset addresses and firewall names; treat that index's access like
the firewall logs themselves.

## Capacity

Numbers below were measured on one install: three FortiGates, about 136,000 traffic
events per hour, Splunk Enterprise 10.0.9. Scale them to your volume.

**Concurrent searches per screen.** Each dashboard dispatches its panels at once:

| Screen | Searches dispatched |
|---|---|
| Overview | 6 |
| Investigate | 10 |
| Health | 10 |
| Alerts | 8 |
| Trends, All detections, IP lookup | 3 each |

Counted as the `<search>` elements in each view that start a job; post-process searches
(`base=`) reuse a parent job and do not count. The numbers are for 0.5.16.

Splunk's historical search limit on a small instance is often 14 (`max_searches_per_cpu`
times cores plus `base_max_searches`). Two analysts with Health and Investigate open at
the same time exceed it; rejected panels show `…` instead of a value. Six scheduled
searches from this app also take slots at their run times.

**Scheduled load.** The 10-minute detection search took 1.6 s on average (8.9 s max); the
Slack, roster, egress and scope searches each under 2 s on average (6 s max). The daily **retroactive sweep**
is the cost item: it scans the last 30 days of traffic against the current feed, about
100 million events per run on the measured install (30 days at 136,000 per hour), 56 to 60
minutes per run, and one
run took 131 minutes when it found 1,483 new rows. It holds one search slot for that
long, every day at 04:20 server local time. To bound it, shorten `dispatch.earliest_time` of
`TI - retroactive sweep` in `local/savedsearches.conf` (cost is proportional to the
window), or disable the search if you do not need past-contact reports.

**Lookups.** The two feed files hold about 55,000 and 58,000 rows (6.5 and 7.4 MB) and
are replaced atomically every 3 hours. `cip_ti_retro_seen.csv` records every contact the
sweep has reported so it is not reported twice; the app never prunes it. It grew by
1,483 rows in a single sweep run. To prune, keep the recent rows and write the file back
(`reported_at` is a `YYYY-MM-DD HH:MM` string):

```
| inputlookup cip_ti_retro_seen
| where strptime(reported_at, "%Y-%m-%d %H:%M") >= relative_time(now(), "-90d@d")
| outputlookup cip_ti_retro_seen
```

Contacts older than the cut can then be reported once more by the next sweep.

**Summary index.** `cip_ti_matches` received about 150 rows per day (2 MB for 817
events), under 100 MB per year at that volume. `default/indexes.conf` sets paths only,
so retention follows your `[default]` index settings; set `frozenTimePeriodInSecs` or
`maxTotalDataSizeMB` for `[cip_ti_matches]` in `local/indexes.conf` if you want a bound.

## Upgrading

Reinstall the `.spl` over the top. Installing reloads conf files, views and the
scripts in `bin/` without a restart. `default/restmap.conf` is read at splunkd start
only (the Set up handler is `scripttype = persist`, and `conf-restmap/_reload` does not
pick it up), so a release that changes it needs `splunk restart`. The table says which
ones do.

| Version | Restart | After installing |
|---|---|---|
| 1.0.1 | No | Nothing to do. Text-only release: `check_for_updates` is no longer disabled, the Set up placeholder and the conf spec use a reserved example domain, and this README is corrected |
| 1.0.0 | **Yes, but not urgent** (`restmap.conf`: the Set up handler declares `python.required = 3.13` alongside `python.version`. The file is read at splunkd start only; until the next restart the handler keeps running exactly as before under Python 3, so nothing breaks by waiting) | First public release |

- **Survives:** everything in `local/` (license key, webhook, log sources, alert scope,
  generated macros), the downloaded feed, and the summary index.
- **Reverts:** the two editable lookups above, unless you kept copies in `local/`.
- **Rows with no recorded outcome** (no `established_count`, written by a version that
  did not split allowed sessions) stay in `cip_ti_matches`. Severity caps them at watch,
  and the screens leave them out of the completed-session tiles and the action counts,
  labelled `outcome not recorded`.
- **No longer reverts:** the alert scope lookup. It ships as
  `cip_ti_alert_scope.csv.default`, so an install leaves your saved scope untouched.
  On a **fresh** install Splunk materialises that seed under the runtime name while it
  installs the app, so the lookup is present from the start (measured on Splunk 10.0.9,
  single instance). Where that does not happen, the `TI - alert scope sync` search
  rebuilds the lookup from the shipped defaults within 5 minutes, and an alert run
  inside that window fails with a lookup error once before the 10-minute grid resumes.
- **Resets:** alert throttling. Installing rewrites the saved searches, and splunkd drops
  their throttle records with them. The first alert run after the install can repeat a
  Slack message that was sent within the previous 45 minutes; from the next run on the
  45-minute throttle applies again (measured on 2026-08-26: one repeat 10 minutes after
  the install, suppressed again from the run after).

**Post-upgrade checklist.** Each step is a screen or one search.

1. **Scripted input.** If the release changed `inputs.conf`, open
   **Settings > Data inputs > Scripts**, open `ti_feed_sync.sh` and press Save. Without
   this the input keeps the interval it had at the last splunkd start.
2. **Slack alert stanza.** Run
   `| rest /servicesNS/nobody/TA-cip-ti-feed/saved/searches | search title="TI - CIP Slack alert" | table alert.suppress.period alert.suppress.fields`
   and expect `45m` and `match_ip ti_direction`. Anything else means a copy in
   `local/savedsearches.conf` is shadowing the shipped search: delete that stanza from
   `local/` and the shipped one takes over.
3. **Detection search.** Within 10 minutes, the **Health** panel on the detection search
   should read the expected `schema_version`. A warning there means the same kind of
   shadow for the detection search.
4. **Overview.** If it says detection is stopped, open Set up and press Save. The app
   also repairs that by itself on the next collection run.
5. **Health > Log arriving, by firewall** fills within 10 minutes of the upgrade.
6. **Secrets (0.5.16 and later).** Run
   `| rest /servicesNS/nobody/TA-cip-ti-feed/storage/passwords | search username="cip_key" OR username="slack_webhook" | table username eai:acl.perms.read`
   and expect `admin` on both rows. Installing applies `metadata/default.meta` at once,
   so entries created by an earlier version already read `admin` right after the upgrade
   (measured on 2026-08-26, no restart). If a row shows anything else, open Set up, type
   the license key and the webhook again and press Save: saving rewrites both entries and
   posts the same ACL.

## What runs on a schedule

| Search | Every | Purpose |
|---|---|---|
| `TI - CIP feed match 10m` | 10 min | The detection search. A gap here cannot be recovered later. |
| `TI - CIP Slack alert` | 10 min | Evaluates detections against your alert scope and sends Slack. |
| `TI - alert scope sync` | 5 min | Applies alert scope changes made in Set up. |
| `TI - firewall roster sync` | 10 min | Keeps the per-device arrival list. |
| `TI - self egress discovery` | 10 min | Learns your own public egress addresses so the app does not report you as the attacker. |
| `TI - retroactive sweep` | daily 04:20 (server local time) | Re-checks the last 30 days of traffic against today's feed and reports contacts that were never alerted. See **Capacity** for its cost. |

Collection itself is a scripted input (`bin/ti_feed_sync.sh`) that runs every 3 hours.
Changing its interval in `local/inputs.conf` does not take effect until the input is
reloaded: **Settings > Data inputs > Scripts**, save the entry. Each run writes one
`event=sync_result` line to `_internal` (`sourcetype=cip:ti:feedsync`) with
`status=ok|failed|not_configured` and `exit=N`. The collector, `bin/ti_feed_pull.py`,
exits 0 (ok), 2 (a setting is invalid, nothing was downloaded), 3 (a feed failed or
shrank and the previous lookups were kept whole), 4 (only some feeds came back and were
written) or 5 (the feed's status endpoint did not answer). It never exits 1 by design;
1 is Python's uncaught-exception value. On failure the line carries
`reason=config_error|kept_stale|wrote_partial|status_unavailable`, and Health shows the
same word next to **Collection status**.

## Compatibility and AppInspect

- Tested on Splunk Enterprise 9.0, 9.1, 9.2, 9.3, 9.4, 10.0, 10.2 and 10.4, self-managed, on Linux (latest patch of each).
  Each was a clean install of this package: the app installs without a Splunk restart,
  Set up saves, the summary index and the lookups appear, and all seven dashboards plus
  Set up register. On 9.0 the Slack alert action was also fired end to end.
- Not Splunk Cloud: collection runs as a shell scripted input, and the app cannot create
  its index there.
- Python: the app declares both `python.version = python3` (required by the current
  AppInspect executable checks) and `python.required = 3.13` (the Splunk 10.2 convention
  that will replace it) on its alert action and REST handler. Splunk versions that do
  not know one of the keys ignore it; the scripts run under Python 3 either way.
  Measured: on Splunk 10.2 the bundled interpreter is Python 3.9 and the Set up REST
  handler still ran, so `python.required = 3.13` is not enforced as a floor there; on
  Splunk 9.0 the bundled interpreter is Python 3.7 and every script in `bin/` compiles
  and imports under it.
- Known AppInspect results for this package, so a reviewer can tell them from
  regressions:

| Check | Result | Why |
|---|---|---|
| AppInspect CLI, `cloud` tag | error 0, failure 0, future failure 0 | measured on 4.3.1 with this package |
| Hostname and IP literal checks | manual check | `127.0.0.1:8089` literal in `bin/` for the loopback management port |
| Binary/symlink checks | skipped on Windows CLI | no compiled binaries ship and the archive is built by `git archive`; the upload-time API run covers them |

## Support and license

Criminal IP TI Feed is proprietary software of AI Spera, Inc. Use requires a valid
Criminal IP TI Feed (CTIDB) license. See `LICENSE`.

Setting reference: `README/cip_ti_feed.conf.spec` and
`README/alert_actions.conf.spec`.
