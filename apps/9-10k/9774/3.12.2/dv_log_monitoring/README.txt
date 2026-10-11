Log Monitoring (dv_log_monitoring)
=================================

Zero-touch log outage monitoring for Splunk. Detects, per index/sourcetype/host,
when a source stops delivering - and says which team owns the failure.

Author: Datavira
Requires: Splunk 8.x or later, KV store enabled, a single search head (not an SHC).
Contains no Python, no scripted inputs, no custom commands, no alert actions.
Writes no limits.conf, no authorize.conf and no indexes.conf. It creates no
index of any kind: everything it knows lives in two KV store collections and
nine CSV lookups. Nothing here needs a capability beyond reading your indexes
and writing its own lookups.


WHAT IT DOES
------------
A scheduled search records, every 5 minutes, the most recent ARRIVAL time
(_indextime) for each index/sourcetype/host that delivered data in that window.
Anything that delivered nothing simply keeps its previous row, and its age grows.
There is no inventory to maintain: the expected set is the set of sources that
have already delivered at least once.

Status is computed at read time by a single macro, dvlm_status. Every dashboard
panel and every alert starts with it, so the dashboard and the alert can never
disagree.

Detection is on arrival time rather than event time on purpose. A device whose
clock is six hours behind is healthy; judged on event time it looks like an
outage. The two are also compared against each other, which surfaces clock skew
and timestamp parsing failures - a class of fault most outage monitors are blind
to.

The diagnosis distinguishes an agent that is down from an agent that is running
but not forwarding, from a source that has genuinely gone quiet, using two
independent liveness signals (_internal and _dsphonehome).


HA HOST PEERS (INTRODUCED IN 3.9.0)
--------------------
Actions > It's a passive device opens a host form, with or without a current alert.
Enter only Peer host. One relationship covers all recorded index/sourcetype streams
on both hosts, including future streams. The passive host need not have delivered
before. Choose an individual source; all monitored indexes now retain host/sourcetype detail.
Remove peer from any stream of the host removes its host relationship.

For EACH index/sourcetype, use the latest arrival from either host. A stream that
stops on both hosts raises Warning/Critical at its existing thresholds. Another
sourcetype, even on the same host, cannot hide the missing stream. Old silent
observations remain expected, including streams never delivered by the new active
host. No active/passive role is inferred; streams may arrive from either member.
Both hosts completely silent means an outage, not automatic passive status.

Two host decisions are saved in dvlm_entity, with h_ha_host, h_ha_peer and h_ha_id,
and included in Maintenance Backup Decisions. No new CSV or collection is needed.
Host keys use a separate ha-host: prefix with percent/colon escaping. Source keys,
physical observations, thresholds, reasons, suppressions and dismissals are untouched.
Thresholds and human decisions remain per source. Delete alert and Passive alert
still apply only to the selected source. Disabled/out-of-scope/rolled-up observations
cannot advance another stream's clock.

Last Data and Silent For use the pair's latest arrival for THAT index/sourcetype.
HA peer reporting means the same stream is arriving from the other member.
HA stream silent means neither member is delivering that stream within its threshold.
Main counts still count physical source records; no passive observations are invented.
The two outage alerts list missing streams in one finding per HA group. Only a newer
arrival of the same stream from either host expires that stream's dismissal.
Decisions shows the host link on affected sources and counts each host decision once.
An unseen peer's own decision can remain in the hidden-decisions count.

Both reciprocal host records must agree before HA takes effect. Incomplete or
conflicting links fall back to individual detection and show HA_LINK_INACTIVE.
A failed write may have reached one or both records: reopen the window to review,
retry or remove it. Writes are checked but not atomic; avoid concurrent edits.

Older 3.8 source links retain their original scope. A configured host link takes
precedence, including when incomplete. The form also offers Remove source link for
an older relationship. Removing a host link restores any older source links still
on record. Upgrading does not silently widen or erase older relationships.

Upgrade the existing dv_log_monitoring app after backing up both KV collections and
local settings. No data rewrite is needed. Follow Splunk's restart prompts and check
local macros.conf, transforms.conf, collections.conf and savedsearches.conf overrides
do not mask the new definitions. Test one pair first, including failover without one
of the expected streams. Local regression fixtures do not replace live Splunk testing.
Before rolling back, keep a separate 3.9.0 decisions backup: 3.8 ignores host links,
3.7 ignores all HA links, and older fields_list definitions may omit h_ha_host from
later backups.

INSTALLATION
------------
Three searches ship ENABLED. Everything else ships disabled.

  Collector, Collector Liveness, Collector DSPhoneHome -- outage detection.

All three only observe: they upsert what arrived into one collection and write
nowhere else.

The rule: a search that only upserts observations starts on its own, because an
app that watches nothing until someone reads a manual watches nothing. A search
that deletes, that alerts, or that is meant to be run once by hand does not -
each of those has a consequence a person should own.

Open the app and go to Setup Guide. It shows these steps with their live state -
which are done, which are half done, which have not been started - and it works
before anything has been installed, which is when you need it.

  0. Run "Log Monitoring - Create Missing Lookups" once, BEFORE ANYTHING ELSE.
     Settings > Searches, reports, and alerts > find it > Run.

     It creates the nine lookup files this app is configured through. Safe at
     any time: it writes only the files that are not already on disk and
     touches nothing you have edited. On a fresh install that is all nine; on
     a configured one it usually writes nothing and reports zeros.

     Run it again after EVERY upgrade, before opening a dashboard. A release
     can add a lookup the macro then reads, and a | lookup whose file is
     missing does not return null - it fails the search. dvlm_status is the
     first command of every panel and every alert, so the app stops until the
     file is there.

     The package deliberately ships no lookup files: Splunk untars over the app
     directory, so a shipped CSV would silently replace your thresholds,
     suppressions, index modes and team assignments on every upgrade. This
     search reads no data - it is makeresults plus outputlookup - and finishes
     in under a second.

     Then, before backfilling, size the estate:

       | tstats dc(host) AS hosts, dc(sourcetype) AS sourcetypes
           WHERE index=* earliest=-24h latest=now BY index
       | eval entities = hosts * sourcetypes
       | eventstats sum(entities) AS estimated_rows

     What a large number costs is runtime on every 5-minute cycle: the
     collector's tstats gets slower and its result spills to disk. It does not
     lose entities - tstats has no row ceiling, and | inputlookup as the first
     command of a search returns the whole collection. If the runtime trend
     bothers you, measure the collector runtime and review index scope.
     Large backfills can be run one index at a time with the full history window.

  1. Run "Log Monitoring - Backfill" once, by hand.

     Standard entity-mode installation has TWO manual runs in total: Create Missing
     Lookups and Backfill. Liveness populates automatically via Collector Liveness,
     every fifteen minutes when recent _internal data is available. Until that
     signal arrives, endpoint diagnosis may be incomplete. Syslog/HA outage
     detection and source Warning/Critical status do not depend on this signal.

  2. The three collectors are already running -- but Collector prefilters its
     tstats on dvlm_index_config, so until step 0 has run it is running every
     five minutes against a lookup that is not on disk. That is the whole
     reason step 0 says BEFORE ANYTHING ELSE. The two liveness collectors read
     no lookup and work from the moment the app is installed.

     Check Operations > Phone-Home Coverage - if the host names look wrong there,
     disable Collector DSPhoneHome and tell us.

  3. Enable "Maintenance Backup" AND "Maintenance Backup Decisions". Both are
     nightly, and together they are the only step that protects data rather
     than collecting it. Two searches, not one: | inputlookup is unbounded only
     as the FIRST command of a search, so a single stanza would have had to
     read the second collection inside a subsearch, where it can be truncated
     silently - and dvlm_entity is the one file nothing can rebuild.
     "Maintenance Purge" is NOT part of installing. Enable it only if you
     change an index's mode - see CONFIGURATION.

  4. Read Operations > Phone-Home Coverage and confirm the number is what you
     expect for your estate.

That is the whole install. Thresholds and alerting come after, and both are
decisions rather than steps - see ALERTS below.


CONFIGURATION
-------------
Every operational decision is a row in a CSV lookup. Nothing is hardcoded in SPL.

  dvlm_settings.csv            eight global parameters, one row: default threshold,
                               escalation multiplier, liveness window, purge age,
                               mass-outage percentage, drift tolerance, collector
                               staleness, syslog class default
  dvlm_threshold_entity.csv    index+sourcetype+host together - the most specific tier
  dvlm_host_allow.csv          one row here and only matching endpoints are watched;
                               EMPTY MEANS NO FILTER, never "watch nothing"
  dvlm_host_deny.csv           never watched, beats the allow list
  dvlm_threshold_host.csv      per-host thresholds
  dvlm_threshold_sourcetype.csv per-sourcetype thresholds
  dvlm_threshold_index.csv     per-index thresholds
  dvlm_index_config.csv        per-index collection mode, owning team, class
  dvlm_suppress.csv            suppressions, permanent or dated

Supported index modes: entity (one record per index/sourcetype/host) and off.
Legacy host/stream modes are treated as entity. Each source keeps its own arrival
time. Old class=stream values fall back to automatic host classification.
Host Monitoring and Stream Health group individual sources on screen; HA pairing
links hosts while checking each index/sourcetype separately.

Threshold precedence, most specific first:

  a value you type on the row  >  entity  >  host  >  sourcetype  >  index
  >  class default  >  default_threshold_sec

Nothing computes a threshold for you. If you want to know what a source's own
delivery history suggests, there is a search for it - see HOW OFTEN DOES THIS
SOURCE DELIVER below.

dvlm_threshold_entity.csv exists for the case the single-dimension files cannot
express: a host whose wineventlog and powershell arrive constantly but whose
ms:iis:default arrives a few days a month. A host rule would slacken every feed on
that host; a sourcetype rule would slacken every host. Leave a column as "*" to mean
any.

Within one file, row order is priority and the first match wins, so put specific
rows above generic ones. No file may contain a catch-all - not a literal "*", and
not a pattern built only from wildcards and separators such as "*.*.*.*" or "*:*".
In the entity file that test applies to all three columns at once: a row is only a
catch-all when every column is wildcard-only.
A catch-all in one dimension makes every dimension below it unreachable. To change
the value that applies everywhere, change default_threshold_sec.

Editing these CSVs requires the upload_lookup_files capability on your role. It
arrived in Splunk 9 and is not added to an existing admin role on upgrade; without
it the lookup editor fails with "You do not have permission to make a CSV Lookup"
even when the file's own permissions are correct.


DASHBOARDS
----------
  Setup Guide      the install order with live state - start here
  Log Outage       per index/sourcetype/host, with the diagnosis and its owner
  Deleted Alerts   every dismissal, and whether it is still holding
  Decisions        every source a person has decided something about
  Stream Health    the index / sourcetype axis
  Operations       collector health, threshold policy, suppressions, app self-checks
  Host Monitoring  one row per machine, marking each of its sourcetypes

Every row in Log Outage, Deleted Alerts and Decisions carries a "..." menu:
dismiss the alert, suppress until a date, set or clear a threshold, stop
monitoring. Those decisions are written straight to the KV store from the
browser - no Python, no custom endpoint - and Decisions is the register of all
of them.


HOW OFTEN DOES THIS SOURCE DELIVER
----------------------------------
Nothing in this app computes that for you and no dashboard column shows it. It
is a search you run when you want it. Set the time picker to 8 days or more -
tstats intersects the picker with the window written into the search, so a
narrower picker silently returns less history than the search claims:

  | tstats max(_indextime) AS lit WHERE index=*
      earliest=-8d@d latest=-1d@d
      _index_earliest=-8d@d _index_latest=-1d@d
      BY index, sourcetype, host, _time span=1h
  | `dvlm_norm_host`
  | where isnotnull(host) AND host != "" AND host != "."
  | stats max(lit) AS lit BY index, sourcetype, host, _time
  | sort 0 index, sourcetype, host, _time
  | streamstats current=f last(lit) AS prev BY index, sourcetype, host
  | where isnotnull(prev) AND lit > prev
  | eval gap = lit - prev
  | stats perc95(gap) AS p95, count AS gaps BY index, sourcetype, host
  | where gaps >= 50
  | eval delivers = tostring(round(p95, 0), "duration"),
         suggested = tostring(min(ceil(p95/3600)*3600 + 3600, 604800), "duration")
  | sort 0 - p95
  | table host index sourcetype delivers suggested gaps

p95 rather than the average, which one bad night drags around, and rather than
the maximum, which IS that bad night. "suggested" rounds it up to the next whole
hour, adds an hour of margin and caps at seven days: what you would type into
Set threshold, not something anything applies on its own.

Two knobs. "gaps >= 50" refuses to answer for a source with too little history;
lower it on a young environment, but below about 20 a percentile stops meaning
much. "latest=-1d@d" keeps today out, so a source that broke this morning cannot
teach you that being broken is normal - leave that one alone.

Swap perc95 for median to get the typical interval instead of the near-worst
case.


RESTORING FROM A BACKUP
-----------------------
"Maintenance Backup" and "Maintenance Backup Decisions" write one collection
each to CSV every night. They are two searches because | inputlookup is only
unbounded as the FIRST command of a search: one stanza would have had to read
the second collection inside a subsearch, where it can be truncated without a
word. Until now this
file never said how to use them, which made the backup a safety net nobody had
been shown how to deploy.

Both restores REPLACE the collection, so read the row count first and be sure
the backup is the one you want:

  | inputlookup dvlm_log_tracking_backup.csv | stats count
  | inputlookup dvlm_entity_backup.csv       | stats count

Observations - rebuildable anyway, the collectors refill this in half an hour:

  | inputlookup dvlm_log_tracking_backup.csv | outputlookup dvlm_log_tracking key_field=_key append=false

Decisions - NOT rebuildable. Every row is something a person typed:

  | inputlookup dvlm_entity_backup.csv | outputlookup dvlm_entity key_field=_key append=false

key_field=_key is not optional in either. Without it the KV store generates new
keys, every entity gets a new identity, and the decisions in dvlm_entity - which
match on _key - stop pointing at anything. Every other search in this app that
writes a collection names key_field for the same reason.


UPGRADING FROM 3.1.5 OR EARLIER, WITH A DEPLOYMENT SERVER
---------------------------------------------------------
The phone-home collector took the hostname out of connectionId without undoing
the deployment server's escaping. connectionId uses "_" as its own separator, so
an underscore inside the hostname arrives as "%": an example machine named APP_NODE_01
was recorded as APP%NODE%01. That name exists nowhere else - the same
machine's data carries the real one - so liveness never matched it, and every
such machine sat under "Liveness but no data" in Operations, looking like an
agent with no inputs configured.

The collector is fixed. The stale rows do not clear themselves, because nothing
writes to that key any more. Check what will go:

  | inputlookup dvlm_log_tracking
  | where index="_dsphonehome" AND match(host, "%") | stats count

Then delete them once, by hand. The collector repopulates within the hour:

  | inputlookup dvlm_log_tracking
  | eval dvlm_stale = if(index="_dsphonehome" AND match(host, "%"), 1, 0)
  | where dvlm_stale = 0
  | fields _key index sourcetype host last_time last_index_time ev cycle_time
  | outputlookup dvlm_log_tracking key_field=_key append=false override_if_empty=false

The shape is Maintenance Purge's, deliberately - it is the only other search
here that deletes, and it has been run on a live instance. Two details in it
are not decoration. The condition is an eval flag rather than "where NOT (...)"
because in SPL a comparison with null yields NULL, not false: with "where NOT",
a row whose host was somehow null would evaluate to null, the where would drop
it, and the row would be DELETED. if() returns its else branch on a null
condition, so such a row is kept. And "| fields" pins exactly the eight columns
the collection holds, so nothing the pipeline picked up can be written back
into it.

Nothing else was affected: a "%" host matches no data row, so it formed its own
liveness group and changed no real entity's diagnosis. What it did cost is the
second liveness axis on those machines - Agent Stopped and Agent Not Forwarding
could not be told apart there.


UPGRADING
---------
RUN "Log Monitoring - Create Missing Lookups" BY HAND, ONCE, AFTER EVERY UPGRADE.
Before opening a dashboard. Also follow any version-specific cleanup below.

Install over the existing app. Lookups are not in the package, so nothing you
configured is touched. But a release that ADDS a lookup leaves the macro reading
a file that does not exist, and a | lookup whose file is missing does not return
null - it fails the search. dvlm_status is the first command of every panel and
every alert, so the app stops until the file is there.

Create Missing Lookups creates ONLY the files that are absent and touches nothing
you have edited. It is idempotent: on a fully configured instance it writes
nothing and reports zeros. Run it as often as you like.

UPGRADING TO 3.12.0. Stream mode has been removed. The package no longer includes
"Log Monitoring - Collector Stream" or "Log Monitoring - Backfill Stream".
Every monitored index now keeps index/sourcetype/host observations. The three
remaining collectors retain their schedules. Host Monitoring, Stream Health,
HA relationships and both liveness collectors remain available.

Before installing, back up both KV collections, CSV lookups and app/user
configuration. Pause Maintenance Purge if enabled. Disable both retired searches,
including any app-local or user-owned copies. After installing, remove only their
retained definitions/stanzas, not whole configuration files. Check overrides of
Collector, Backfill, Maintenance Purge, Alert Self Health and dvlm_status so the
new definitions take effect. Follow the 3.11 notes too if upgrading from before 3.11.

Run Create Missing Lookups after installation. Existing CSV files are not rewritten.
Old mode=stream and mode=host values are read as entity; normal Collector and
Backfill now include those indexes. If you used an aggregate mode, run the normal
Backfill with its full history window, verify job completion and check restored
individual sources, then change only those mode cells to entity. Preserve all
other CSV values and row order. Old class=stream values use automatic host
classification; clear that legacy class value or set a supported class explicitly.

The Collector's eight-minute window cannot recover sources already silent at
upgrade. Backfill can only discover combinations present in its available index
history. An index::sourcetype::* summary cannot reconstruct individual host names
or timestamps. Index Mode Checks lists legacy settings only; an empty panel does
not prove that the source history is complete or that the collector has run.

Data summaries with host="*" or sourcetype="*" are ignored before status, liveness
association and collector-health calculations. They remain physically in KV until
cleanup. Liveness rows in _internal/_dsphonehome remain available and are exempt
from mode-related cleanup. Maintenance Purge also has a permanent-suppression age
condition; Stale Grain Rows previews only mode-related candidates, not this second
condition. Verify that full deletion scope before resuming Purge. If all rows
would be removed, override_if_empty=false prevents the collection rewrite.

No KV schema change occurs. Existing per-source decisions and host HA records
remain in dvlm_entity. Decisions on old aggregate keys remain recorded but are not
automatically copied to the new individual keys. Removing a summary does not
remove a human decision.

Rollback: reinstall 3.11.0 and restore saved configuration as needed. Re-enable the
old stream collector only if returning to mode=stream. If aggregate observations
were purged, restoring the previous package alone does not recover them: restore
the observation backup using the key-preserving procedure below. Do not uninstall
the app or clear either collection.

KNOWN LIMITATIONS CARRIED INTO 3.12.0. Collector health still uses the last data
observation write. If all collected data sources become silent, a successfully
running collector can be labelled stale and the outage-alert gate can close.
Alert Self Health should be enabled, but is not a replacement for source alerts.
Independent successful-run tracking is not part of this release.
Backfill writes existing keys without comparing their stored arrival timestamp.
An older historical subset can overwrite a newer observation; do not assume
arbitrary time slices are order-independent. Concurrent Collector/Backfill writes
also need care. Retiring stream mode does not resolve these two known issues.

UPGRADING TO 3.11.0. Host Grain has been removed. The package no longer includes
"Log Monitoring - Collector Host Grain" or "Log Monitoring - Backfill Host Grain".
In 3.11, Host Monitoring, host HA relationships, both liveness collectors and
stream mode remained available. Stream mode is retired by 3.12 as described above.
No KV schema change or automatic rewrite of your CSVs occurs.

Before upgrading, back up both KV collections and the app/user configuration.
Pause Maintenance Purge if enabled. Disable both retired saved searches wherever
they remain, including app-local and user-owned copies. After installing, remove
only their retained definitions/stanzas; do not delete whole configuration files.
Check local overrides of Collector, Backfill, Maintenance Purge, Alert Self Health
and dvlm_status so the new definitions take effect.

Any existing mode=host setting is read as entity. The main Collector and Backfill
now include those indexes. If you previously used that mode, run the normal
"Log Monitoring - Backfill" after Create Missing Lookups, verify its completion,
then change those mode cells to entity, keeping all other CSV fields and row order.
The Collector's eight-minute window alone cannot discover sources already silent
at upgrade. Backfill can reconstruct only streams present in its thirty-day index
history; an old index::*::host summary cannot recover missing sourcetype names or
individual timestamps. Missing history is not proof that every feed is healthy.

Old host summaries are ignored by status and collector-health checks immediately,
so a fresh aggregate cannot hide a missing Security or threat feed. They remain in
KV until an explicit Maintenance Purge removes them. In Operations, review the
Stale Grain Rows (queued for removal) panel and verify the new source records
before resuming purge.
Both liveness indexes are exempt from mode cleanup; permanent-suppression age
cleanup is independent. Existing source decisions and HA
links stay in dvlm_entity; decisions on old aggregate keys are kept but are not
silently copied onto the new individual source keys.

For rollback, install the previous package and restore the saved configuration if
needed. Re-enable the old collector only if returning to mode=host. If old host
summaries were purged, the observation backup is needed to recover their old state;
use the recovery procedure below. Do not remove the app or clear either collection.

UPGRADING TO 3.10.0. Backfill Liveness has been removed from the package and setup
instructions. Collector Liveness remains enabled with its existing schedule.
There is no KV schema change or data migration, and existing HA links are retained.

After backing up local configuration, check for a saved search named
"Log Monitoring - Backfill Liveness" in this app, including user-owned copies.
If it remains after upgrade, disable it and remove only that saved-search definition
or its [Log Monitoring - Backfill Liveness] stanza from the applicable local or
user configuration. Do not delete the entire savedsearches.conf file or any KV rows.
Keep Collector Liveness. A default-only installation has no leftover to remove.
If rolling back to 3.9.0, the old default search returns with that package; restore
a customized copy only if it is needed. Existing observations and HA decisions
are unaffected in either direction.

Earlier versions shipped a second search, "Create Lookups", which replaced
all nine files unconditionally. On a fresh install it did exactly what Create
Missing Lookups does; the only thing it could do that this one cannot is
overwrite files somebody had already edited. It was removed. To go back to the
shipped defaults now, delete the CSVs you want reset and run Create Missing
Lookups again - deliberately, one file at a time, rather than by pressing the
wrong button once.

Earlier versions of this file told you to create a new lookup by hand with
| makeresults ... | outputlookup <name>.csv before installing. Do not do that.
outputlookup in replace mode overwrites the whole file, so on an instance that
already has it, that recipe discards the rows it was meant to protect.

The KV store collections are independent of the app directory, so collected
history survives; they are removed only if the app is uninstalled.

GOING BACK TO 2.x. If you reinstall 2.11.1 over this app, two stanzas exist
here and not there: "Maintenance Backup Decisions" and "Clear Learner Marker".
That is the same hazard as the six stanzas listed further down, under
"After upgrading, check local/savedsearches.conf", in the other direction. If you
have opened either one through the UI's Edit form, its whole stanza -- SPL
included -- is pinned in local/, and after the rollback it is an enabled saved
search whose default/ counterpart is gone. Delete those stanzas from
local/savedsearches.conf before or after rolling back; if you never opened them
with Edit, there is nothing in local/ and nothing to do.

Your decisions survive either way: dvlm_entity is written by the browser, not by
a search, and 2.11.1 reads the same fields. A threshold you typed by hand still
applies after a rollback even if you ran Clear Learner Marker first -- 2.11.1
reads that field as coalesce(h_thr_mode, ""), and "" is not "auto".

UPGRADING FROM 2.x. Three things change. None of them needs action from you;
two of them leave something behind that you may want to clear up.

The app no longer ships indexes.conf, so the dv_logmetrics metric index it used
to declare is orphaned: still on disk with its data, read by nothing. Delete the
index and its directory to reclaim the space, or leave it to age out. Splunk
does not need the stanza in order to start without it.

The dvlm_learned KV collection is orphaned the same way, and it is the harder of
the two to notice: v2 declared it in collections.conf and gave it a lookup
definition, and v3 ships neither. The data is not in the app directory, so
installing over the app does not remove it -- but with the lookup definition
gone, SPL can no longer reach it at all. | inputlookup dvlm_learned now fails
with "lookup table does not exist", which reads like a broken app rather than
like a collection you no longer have a name for.

See whether it is still there -- NOT through the collections config endpoint.
That one lists what collections.conf DECLARES, and v3 declares no dvlm_learned,
which is the whole point of the paragraph above. Ask the KV store itself:

    | rest /services/server/introspection/kvstore/collectionstats count=0
        splunk_server=local

Each row is a collection the store actually holds. If dvlm_learned appears it
still carries one row per entity the learner had computed a threshold for.
Nothing reads it and nothing will.

Removing it is not the one-line step this file claimed in 3.5.5. With no stanza
splunkd does not know the collection, so a DELETE on the config endpoint answers
404. Getting rid of it means declaring it again in a local collections.conf,
restarting, deleting it, and removing the stanza. Leaving it costs KV store
space and nothing else, and leaving it is the recommendation.

Entities you had switched to the learned threshold follow the ordinary
precedence rules again, because there is no learner any more. That happens on
its own. A threshold you typed by hand is untouched, and so is every disable,
suppression and dismissal.

Those rows do still carry a dead marker field that nothing reads. To remove it,
run both "Maintenance Backup" searches and then
"Log Monitoring - Clear Learner Marker", once,
by hand. It reports how many rows it rewrote and is safe to run twice. It is
disabled and unscheduled on purpose: it rewrites dvlm_entity, which holds every
decision anyone has made here and is the one thing in this app that cannot be
reconstructed from your indexes. Leaving it unrun costs nothing but tidiness.

ALERTS
------
Three ship, all disabled, and none of them is an install step - who gets told, and
how, is a decision per team rather than something a setup guide can answer. That is
why they are not in the Setup Guide table.

  Alert Self Health    the app watching itself. It is the only legitimate reason
                       for the other two to be quiet, so if you enable one alert,
                       enable this one.
  Alert Critical Only  outages at Critical, grouped so a hundred hosts behind one
                       broken feed arrive as one message rather than a hundred.
  Daily Digest         one morning summary. Run it by hand first and read what it
                       says before scheduling it.

None of them emails until you set action.email = 1 and action.email.to. Until then
they land under Activity > Triggered Alerts, which is a fine place to leave them
while you decide whether what they say is worth someone's attention.


After upgrading, check local/savedsearches.conf. A saved search edited through
the UI pins its old SPL there and no update will ever reach it.

  For a stanza that STILL EXISTS in default/savedsearches.conf: delete the
  "search =" line and keep only the enablement keys.

  For a stanza that no longer exists in default/: delete the WHOLE stanza.
  Keeping only its enablement keys leaves an enabled saved search with no SPL,
  which fails on a schedule forever. Coming from 2.x, those are SIX:
  Create Lookups, History Metrics, History Population, Learn Thresholds,
  Maintenance Purge Learned, and Seed Learned Thresholds. Five went with the
  metric index and the threshold learner. Create Lookups went because Create
  Missing Lookups does the same job on a fresh install and on an upgrade, so
  there was no reason to keep two -- and it is the one that matters most here.
  It was the search a 2.x operator was most likely to have opened with Edit,
  and the copy that pins in local/ is the destructive one: it rewrites the
  lookups instead of filling in the ones that are missing. If you never edited
  any of them through the UI, there is nothing in local/ and nothing to do.
