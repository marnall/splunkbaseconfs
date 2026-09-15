RansomLeak Add-on for Splunk — release notes

Unreleased
----------

* PACKAGE SIZE: the add-on is now 5.3 MB instead of 13.2 MB, and its bundled
  lib/ is 3.8 MB instead of 26 MB, because solnlib is pinned to 7.0.0. Every
  8.x release declares grpcio and the OpenTelemetry OTLP exporter as hard
  dependencies — about 22 MB of compiled, architecture-specific code that this
  add-on never calls. Nothing the add-on uses changed between solnlib 7 and 8:
  the KV-store checkpointer, the configuration manager, the credential reader
  and the logging helpers are identical apart from type annotations.

  There are now no compiled binaries in the package at all, so it installs and
  runs the same on x86-64 and AArch64 (Graviton) Splunk hosts.

* PACKAGE METADATA: app.manifest now names the publisher (RansomLeak,
  RansomLeak OÜ, support@ransomleak.com), carries a release date and a link
  to https://ransomleak.com/privacy-policy/, and describes what the add-on
  actually collects instead of just repeating the product name. The
  description is what Splunk shows beside the add-on in Apps -> Manage Apps,
  and the publisher name now appears there as the author. No behaviour change.

* FIXED: _time was WRONG on every sourcetype, in two different ways, and this
  release settles both. Every event now carries a field named rlEventTime as
  its first key, holding exactly the instant that sourcetype's _time is
  defined to be, and props.conf extracts _time from it with a prefix anchored
  to the start of the event.

  The two defects, both measured on Splunk Enterprise 10.4.2:

    - Aggregate TABLE rows (overdue users, assignments by category) inherited
      the timestamp of whichever time-series event preceded them, putting 102
      overdue-user rows nearly twelve days in the past. An extraction rule
      that fails to match an event does NOT defer to the timestamp the input
      supplied — it reuses the previous event's.

    - The first attempt at fixing that turned extraction off with
      DATETIME_CONFIG = CURRENT, on the belief that the input's explicit
      timestamp would then be authoritative. IT IS NOT. CURRENT keeps only the
      sub-second fraction of the supplied value and takes the whole second
      from arrival. ransomleak:audit drifted by up to 162 days and
      ransomleak:phishing by up to 196; 901 daily metric buckets collapsed
      onto 2 instants, so every trend chart became a single vertical line at
      ingest time. Identity panels on their default 7-day window counted 1,181
      events where 59 belonged, Phishing counted 1,591 where none did, and the
      Feed status table's STALE state could never fire.

  Both are gone: audit and phishing _time now match the event's own timestamp
  to 0.000 s, and 901 metric buckets occupy 901 distinct _time values spread
  across the queried history.

  ROWS ALREADY INDEXED KEEP THEIR WRONG _time. Re-index, or accept the gap.
  If your deployment installs this add-on separately on forwarders and
  indexers, upgrade BOTH: an old forwarder's events carry no rlEventTime for
  a new indexer's props.conf to read. That case is loud, not silent — splunkd
  logs one DateParserVerbose WARNING per event, and the Health dashboard's
  "Recent errors, warnings and timestamp-parse failures" panel shows it with
  log_level=TIMESTAMP.

  rlEventTime is an added field. A payload field of the same name is kept,
  renamed to rlEventTime_payload; nothing is dropped.

* FIXED: CIM fields on ransomleak:audit could be the literal string "null".
  Splunk's JSON field extraction renders a JSON null as the four-character
  string rather than omitting the field, so Authentication.user, object and
  object_id showed "null", the administrator was reported in src_user on
  events that have no separate subject, and a real target id was occasionally
  discarded in favour of the string. Affects searches and Access Center
  panels reading these fields; no re-index required, the fix is search-time.

* FIXED: seventeen dashboard panels — including Enrollments by team,
  Enrollments by framework and Users with overdue training — rendered blank
  even with data present, and the genuinely empty ones showed nothing instead
  of their explanation. Their emptiness guard used field names beginning with
  a double underscore, and `eventstats ... as __rows` returns zero rows on
  10.4.2. Also, the Feed status table's "events (all time)" column now really
  is all time, so the STALE status can fire.

* DEPLOYMENT SCOPE NARROWED: app.manifest now declares targetWorkloads
  ["_search_heads"] and supportedDeployments ["_standalone", "_distributed"].
  Nothing in this add-on runs on an indexer — the modular inputs need the
  management port, the KV store and outbound HTTPS, and the alert action only
  runs on a search head. Search head CLUSTERING is deliberately NOT declared:
  every member would run every input against one shared KV-store checkpoint
  document, and solnlib replaces that document rather than merging it, so
  concurrent members cause skipped events as well as duplicates. Install on a
  standalone or distributed search head.

* CIM: ransomleak:audit now populates the Authentication and Change data
  models. Requires the Splunk Common Information Model add-on
  (Splunk_SA_CIM 6.0 or later); the add-on ingests normally without it, only
  the data models stay empty.

  Which events go where:

    - Authentication — login.success, login.failed, mfa.challenge_sent,
      mfa.verified, mfa.failed. `action` is success / failure / pending.
    - Change — the user, SCIM, password, licence, API-token, role and tenant
      settings events. `action` is created / updated / deleted / lockout, and
      `status` distinguishes the two SCIM provisioning failures. Eighteen of
      them also carry the `account` tag and so appear in Account_Management.

  Four event types are in NEITHER model on purpose — logout,
  password.reset_requested, ip.blocked and scorm.origin_blocked. CIM has no
  honest home for them, and a wrong mapping produces wrong answers silently.
  They are grouped under the tagless eventtype ransomleak_audit_unmapped so
  they remain easy to search.

  ransomleak:training, ransomleak:phishing, ransomleak:risk and
  ransomleak:metrics are NOT mapped, for the same reason.

  Two things worth knowing when you search:

    - `src` is the client IP, and is ABSENT rather than "unknown" when the
      product could not resolve one.
    - On account changes, `user` is the account that changed and `src_user`
      is the administrator who changed it. Some of those events record only
      an internal id, so `user` can be a UUID; `user_id` always holds the id
      if you need to group consistently.

  Any audit row whose event type is not one the product currently defines —
  older tenants hold a few from retired code paths — matches the eventtype
  ransomleak_audit_unclassified. It is indexed and searchable; it is simply
  not claimed to belong to a data model.

* NEW INPUTS: Risk Posture (ransomleak:risk) and Programme Metrics
  (ransomleak:metrics).

  Both read the aggregate metric endpoint behind the RansomLeak Grafana
  data source: human risk score, training completion rate, overdue
  assignments and users, phishing click/report rates, assignments by
  category, and Grafana-triggered auto-assignments. Each input takes a
  multi-select over the whole metric catalogue, an optional team and
  phishing-channel facet, and a lookback window; they differ only in which
  metrics and interval they default to.

  ACTION REQUIRED: the account's API token must additionally carry the
  'integration' scope. It is NOT one of the scopes the Phishing Events,
  Audit Events or Training State inputs use, so a token minted for those
  returns 403 on these two inputs — and the response does not say which
  scope is missing. Add the scope to the existing token, or point these
  inputs at a new account.

  _time depends on the shape of the metric:

    - time series -> the UTC day the value describes, also carried in the
      event's bucketTime field. A day whose value is later corrected is
      re-indexed at the same _time, so chart it with
      `timechart span=1d latest(value)`.
    - table (overdue users, assignments by category) -> the moment the
      add-on observed the row. Table rows carry no day of their own; they
      describe the present.

  A day with no denominator (no simulations sent, no assignments yet) is
  indexed as NO EVENT rather than as 0, so it renders as a gap instead of
  dragging averages and alert thresholds down. The count of such days is
  logged each run. A genuine zero is still indexed.

  Only buckets and rows whose value changed since the last poll are
  emitted, so a wide lookback window costs one request per metric rather
  than repeated events.

* ransomleak:training — _time is now OBSERVATION time.

  These events are emitted when a training row's content changes, so their
  _time is the moment this add-on observed the change. It was previously
  assignedAt, which indexed a completion observed today at the instant the
  training was assigned, possibly months earlier. That made the events
  invisible to recent-time searches (completion alerting could not work),
  gave every change event for one enrollment the same _time, and let a short
  frozenTimePeriodInSecs freeze them out on arrival.

  assignedAt, completedAt and dueAt still ship verbatim in the event body, so
  a search that wants assignment time reads the field:

    index=... sourcetype=ransomleak:training
    | eval assigned=strptime(assignedAt, "%Y-%m-%dT%H:%M:%S.%3NZ")

  ransomleak:audit and ransomleak:phishing are unaffected: their timestamp /
  occurredAt genuinely are the event's own occurrence time.

* ransomleak:audit — the input pulls the audit feed through the RansomLeak
  keyset-cursor API (GET /api/external/security-events), and that is now its
  ONLY path. The previous day-by-day export walk, kept for one iteration as a
  fallback for servers that did not yet serve the cursor route, has been
  removed.

  What this changes for you:

    - The first run backfills the entire retained audit history, with no
      horizon to configure.
    - Events whose type is no longer in the product's event-type list (older
      tenants hold some) are indexed instead of only being warned about.
    - The 10,000-row-per-request cap, and the truncation warnings that went
      with it, cannot occur.
    - Events reach the indexer a page at a time as the feed is read, so a
      long first-run backfill does not scale its memory with the size of the
      history. The checkpoint is still written once, after every event; a run
      interrupted part-way re-emits, it never skips.

  TWO INPUT SETTINGS WERE REMOVED with the export walk: Window (days) and
  First-run backfill (days). They configured that walk and nothing else. If
  you templated inputs.conf by hand, drop window_days and backfill_days from
  your audit_events stanzas.

  Your RansomLeak server must serve GET /api/external/security-events. Every
  RansomLeak deployment does; if the input logs a 404 against that path, check
  the account's base URL first.

  Lookback (hours) is unchanged and should stay non-zero: an event's timestamp
  is set when it is logged, not when its transaction commits, so a row can
  become visible behind a point the feed has already read. Setting it to 0
  makes the input resume from the exact cursor and accept that risk.
