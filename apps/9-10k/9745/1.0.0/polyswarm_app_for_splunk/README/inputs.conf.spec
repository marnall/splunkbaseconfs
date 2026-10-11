# Specification for the modular inputs this app defines.
#
# Splunk reads this file to validate a customer's local/inputs.conf and to
# render the input's settings, and the app inspector reads it to check that
# every modular input the package ships is declared. A setting the input reads
# and does not declare here is a setting no operator can discover.
#
# Credential values are never declared here. The API key lives in encrypted
# credential storage under the realm bin/ps_client.py names, never in a .conf
# file, so no stanza in this specification will ever carry a key, token or
# password setting.

[input_task_poller://<name>]

* The PolySwarm sandbox task poller. Follows detonations submitted by the
  polyswarmdetonate command or the PolySwarm Detonate alert action and updates
  each task in the ps_sandbox_tasks KV store collection until the platform
  settles it, then leaves it alone.
* The stanza name is the file name of bin/input_task_poller.py, because splunkd
  derives a modular input's kind from the script's own basename.
* Makes no request when nothing is in flight: with no task rows the run reads
  an empty collection and exits.
* Each in-flight task costs at most one status request per run. A status
  request is a GET against the PolySwarm API. It books no sandbox time and
  spends none of the detonation allowance a plan includes.
* Per-row backoff grows 30, 60, 120 then 300 seconds while a task is unsettled.
  A settled task is never polled again.
* A task that never settles is given up on rather than polled forever. See
  max_task_age_hours below.
* The shipped stanza is [input_task_poller://polyswarm_sandbox_tasks], enabled,
  at a 120 second interval.

max_polls = <integer>
* Most status requests one run of this input may spend.
* Rows above the ceiling are left for the next run rather than dropped.
* Must be at least 1. Disable the input rather than setting it to zero.
* Cannot exceed 200. That limit is in code, at MAX_POLLS_HARD_CAP in
  bin/input_task_poller.py, and saving a larger value is refused rather than
  silently reduced.
* Default: 50.

max_task_age_hours = <integer>
* How long one detonation may stay unsettled before the poller stops asking
  about it, in hours. This is the per-task ceiling; max_polls above is a
  per-run ceiling and bounds nothing about what a single row costs over time.
* A row that passes it is marked with poll_abandoned_at and is not polled
  again. The row is KEPT, carrying whatever the platform last said about it:
  it is the record of a metered detonation.
* The status field is left exactly as the platform reported it. This app never
  writes a status word of its own.
* Two things give up on a row sooner and need no configuration: the platform's
  own task expiration, which is about three hours after a task is created, and
  three consecutive polls the platform answers with nothing, which is what a
  404 for an unknown task id looks like.
* To have an abandoned task followed again, clear its poll_abandoned_at field
  in the ps_sandbox_tasks collection. Nothing in the app clears it.
* Must be at least 1. A shorter ceiling would stop following detonations that
  are still running.
* Cannot exceed 168, which is one week. Saving a value outside the range is
  refused rather than silently reduced.
* Default: 24.

[input_intel_pull://<name>]

* The PolySwarm threat intel pull. Design section 4.2. Pulls artifacts
  matching malware families, tags and a PolyScore floor into a Splunk index on
  a schedule, one event per artifact, sourcetype polyswarm:artifact.
* The stanza name is the file name of bin/input_intel_pull.py, because splunkd
  derives a modular input's kind from the script's own basename.
* SHIPS DISABLED. Every page of results is a metered API request against the
  account, so this input is opt-in: an operator enables it after choosing a
  window, a floor and a cap. That is defect class B8, and unlike the task
  poller above there is no version of this input that costs nothing when idle.
* Each run covers the window from the last successful run up to the current
  time minus lag_seconds. The first run covers lookback_minutes. Nothing is
  skipped by a long interval: the window starts where the last one ended.
* Checkpointed per stanza in the ps_intel_pull_checkpoint KV store collection,
  and safe to run twice: the window advances, and a digest the previous run
  emitted is refused. Constraint C7.
* The checkpoint advances after a run that completed, and as far as it got
  after a run that stopped at its cap. A run that FAILED part way advances
  nothing and re-covers its window on the next run rather than losing it.
* Each window closes at the current time minus lag_seconds, so an artifact the
  platform has taken but not yet made searchable is picked up by the next
  window instead of being skipped.
* Uses the standard index setting to choose its destination. The shipped stanza
  writes to `default`; point it at your own threat intel index.
* The shipped stanza is [input_intel_pull://polyswarm_intel_pull], disabled, at
  a 900 second interval.
* `| polyswarmsync stanza=<name>` runs one cycle of a stanza on demand and
  returns the run summary. It is a preview: it writes no events and does not
  advance the checkpoint.

families = <comma separated string>
* Malware family names to pull, for example emotet,ryuk.
* At most 3 are used. Values past the third are ignored, which is the ceiling
  the v1 add-on applied and this input reports on its finish line.
* Spaces are removed before the value is split, so "red line" becomes
  "redline". A family name is matched unquoted against five fields, and a space
  inside one would change what the query matches. Use tags for a value that
  needs a space.
* Blank, together with a blank tags, pulls the feed:premium tag.
* Default: blank.

tags = <comma separated string>
* Tag values to pull, for example sector:healthcare,ransomware.
* At most 3 are used, on the same rule families follows.
* Matched as an exact quoted tag, so a namespaced tag is given in full.
* Default: blank.

min_polyscore = <decimal>
* Only artifacts scoring at or above this are pulled.
* Must be above 0 and at most 1. A floor of 0 would pull every artifact the
  platform holds, and saving one is refused rather than silently corrected.
* 0.7 is the score polyswarmsearch bands malicious, so the default pulls what
  the rest of the app calls malicious and nothing below it. Lowering it widens
  the pull into the suspicious band, which is a supported choice; the cap is
  what keeps it affordable.
* Default: 0.7.

lookback_minutes = <integer>
* How far back the FIRST run reaches, in minutes.
* Applies only when the stanza has no checkpoint. Later runs start where the
  last one ended, so this is the size of the first window and not an overlap.
* Must be at least 1. Cannot exceed 43200, which is 30 days.
* Default: 1440.

max_artifacts_per_run = <integer>
* Most events one run of this input may write.
* Artifacts above the cap are left for the next run rather than dropped, which
  is constraint C11's refuse-rather-than-proceed shape applied to an input.
* Must be at least 1. Disable the input rather than setting it to zero.
* Cannot exceed 1000. That limit is in code, at MAX_ARTIFACTS_HARD_CAP in
  bin/input_intel_pull.py, and saving a larger value is refused rather than
  silently reduced.
* The next run continues where a capped run reached rather than repeating it.
  The endpoint answers newest first, so a capped run records the point it got
  to and the runs after it work backwards through the remainder of the window
  until the backlog is drained.
* Default: 200.

lag_seconds = <integer>
* How far behind the clock each window closes, in seconds.
* An artifact is stamped with the moment the platform took it and becomes
  findable by the metadata search a little later, once it has been scanned and
  indexed. A window that closed at the clock would ask about an instant whose
  artifacts were partly not yet findable, and because the next window starts
  where this one ended those artifacts would be skipped permanently and
  silently.
* Costs no artifacts at any value: what one window does not ask about, the next
  one does. What it costs is freshness, which is this value plus up to one
  interval.
* Must be zero or greater. Zero closes the window at the clock, which is
  supported and is what this input did before the setting existed; set it only
  if you have measured your platform's indexing latency.
* Cannot exceed 3600. Saving a larger value is refused rather than silently
  reduced.
* Default: 300.
* 300 is the longest delay this app already treats as normal for a
  platform-side operation that has not settled: it is the final step of the
  sandbox poller's per-row backoff, which runs 30, 60, 120 then 300 seconds.
  Using the same number keeps one claim in the app about how long the platform
  may take rather than two.

community = <string>
* The PolySwarm community to pull from.
* Blank means the app's own community rule answers: the community configured on
  the setup page, then the account's most private entitled community, then the
  platform default. This is the right value for almost every deployment.
* Set it only to pull two communities into two indexes from two stanzas, which
  the rule cannot express because it resolves one answer per account.
* Default: blank.
