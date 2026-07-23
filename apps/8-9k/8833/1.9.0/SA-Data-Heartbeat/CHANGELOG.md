# Changelog

All notable changes to SA-Data-Heartbeat are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows [Semantic Versioning](https://semver.org/).

## [v1.9.0] - 2026-07-21

### Added — build 88 (nightly Usage Refresh: "N uses" now stays current, with a searches-vs-dashboards breakdown)
- **New nightly "Usage Refresh" scheduled search (02:30).** `usage_count` (the "N uses" badge) was stamped only at add-time and never updated — a sourcetype added before anything referenced it (e.g. Curated picks on older builds) showed no usage forever, and counts never dropped when objects were deleted. The refresh recomputes the unified reference metric — **distinct saved searches/alerts + dashboards referencing `sourcetype=X`** — for *every* monitored row each night, preserving all operator-tuned fields and honoring the deletion-tombstone guard. REST-only (no index scan); enabled alongside detection via Settings / `enable_all`.
- **Breakdown stored and shown**: new `usage_searches` / `usage_dashboards` fields; the badge tooltip now reads e.g. "2 searches/alerts · 1 dashboards reference this sourcetype (recounted nightly)". Detection carries the new fields through its per-run upsert.
- Verified end-to-end: a curated row stuck at 0 uses recounts to the true total with the correct split; notes/importance/provenance untouched; fields survive detection runs.
- `heartbeat-v27.js` → `heartbeat-v28.js`, `settings-v61.js` → `settings-v62.js` (cache-bust).

## [v1.8.0] - 2026-07-21

### Fixed — build 87 (stale `_time`-equal freshness leaking through the carry; explicit provenance)
- **A backfilled sourcetype could report a freshness number that back-calculates exactly to `max(_time)` instead of `max(_indextime)`.** Root cause (verified with a dev divergence control — 100 events with `_time` 7–12 days old, `_indextime` = now): detection's event-time lookback window can't see recently-**indexed** data whose event **timestamps** predate the window, so `tstats` returns zero rows for the sourcetype and the `prev_last_seen` carry silently re-serves the last stored value — which, for a feed that was live before the gap, numerically equals `max(_time)` (live ingest ⇒ `_indextime ≈ _time`). The displayed number was a stale substitution presented as a live measurement.
- **`last_seen` is now monotonic** — `max(` fresh index-time`,` carried value `)` — so a partial in-window match can never regress it backwards.
- **New `freshness_basis` field makes provenance explicit** on every row: `index_time` (tstats saw the sourcetype this run — a live measurement), `carried` (no data with `_time` inside the lookback window — the value is the last *confirmed* receipt), `never` (no receipt on record). The Monitor table badges carried rows "**no data in window**" with guidance to widen Detection Lookback — a stale number is never silently presented as fresh.
- **Fixed: Detection Lookback values above 24 h silently failed to save** — the settings input allowed up to 10080 but the save handler still clamped at 1440. Both now allow up to 43200 (30 days), so operators with known backfill/skew patterns can widen the window to actually *measure* (not just carry) those sources.
- Regression-tested against the dev control: app output == `(now()-max(_indextime))/60` within ±2 min and ≠ `(now()-max(_time))/60`; empty sourcetype reports basis `never`; narrow-window runs report basis `carried` explicitly.
- `heartbeat-v26.js` → `heartbeat-v27.js`, `settings-v60.js` → `settings-v61.js` (cache-bust).

## [v1.7.2] - 2026-07-20

### Fixed — build 86 (detection search errored on some Splunk editions)
- **Removed the monitored-sourcetype subsearch from the detection `tstats`.** v1.7.0/1.7.1 constrained the scan with `[| inputlookup monitored_sourcetypes_lookup | fields sourcetype | format]` inside the `tstats where` clause. That construct — and the bare `NOT ( )` it emits when the monitored list is empty — **errored on some Splunk editions/versions** (it ran on Splunk 10.2 Enterprise, which is why it wasn't caught). Detection now uses `| tstats max(_indextime) ... where index=* OR index=_* by sourcetype` and keeps only the monitored rows via the existing `where _mon=1` step — the query shape every pre-1.7.0 release ran successfully.
- **Performance is preserved.** The subsearch was only a secondary optimization (it trimmed aggregation work *within* the scanned buckets). The dominant win — the 24 h lookback window that replaced the old ±2 y window (~730× fewer buckets opened per run) — is unchanged, along with the configurable **Detection Lookback** setting.
- `heartbeat-v25.js` → `heartbeat-v26.js` (cache-bust).

## [v1.7.1] - 2026-07-18

### Changed — build 85 (detection lookback default 60 min → 24 h)
- **The default Detection Lookback is now 24 hours (1440 min), up from 60 min.** The v1.7.0 default of 1 h was too tight for the common case: a source whose event timestamps trail ingest by more than the window (timezone misconfiguration, DST edges, batch/latent feeds) would be falsely flagged as stopped. 24 h tolerates those everyday skews while still being ~700× narrower than the old ±2 y window. The setting is unchanged — operators on very large, clean-timestamp deployments can still tighten it to 15–60 min for maximum performance (the "Detection Lookback" field on the Settings page; max raised to 10080 min / 7 days).
- Only the default value changed; the mechanism (constrain-to-monitored scan, single lookback window, `max(_indextime)` measurement) is unchanged from v1.7.0.
- `heartbeat-v24.js` → `heartbeat-v25.js`, `settings-v59.js` → `settings-v60.js` (cache-bust).

## [v1.7.0] - 2026-07-18

### Changed — build 84 (detection performance redesign for large-scale deployments)
The detection search was re-architected to run efficiently from 1 GB/day to 150+ TB/day, hundreds-of-PB tenants. Two changes, both runtime-verified on Splunk 10.2:

- **Detection now scans only the *monitored* sourcetypes.** Previously `| tstats max(_indextime) ... where index=* OR index=_* by sourcetype` computed a last-seen for **every** sourcetype in **every** index (including all of `_internal`/`_audit`/`_telemetry`) every run, and discarded the unmonitored ones at the end. It now constrains the scan with `[| inputlookup monitored_sourcetypes_lookup | fields sourcetype | format]`, so cost is proportional to the *monitored* count, not the total. Cold-start (empty lookup) safely returns nothing (`NOT ()`); the `append [inputlookup]` leg still injects monitored-but-never-seen sources. This is the single biggest recurring cost reduction — it runs every few minutes forever.
- **The ±2 year search window is gone.** It forced `tstats` to open up to **two years of buckets every run** — the real performance killer on long-retention tenants (Splunk prunes buckets by event `_time`, so a wide window = a wide scan; `_index_earliest` does not prune buckets on its own — confirmed against the tstats docs). Detection now uses a single **narrow lookback window** (dispatch `-1h → now` by default) while still **measuring `max(_indextime)`** (true receipt time). The `prev_last_seen` carry preserves the age of sources silent longer than the window, so the window stays small without losing long-silent aging.
- **New "Detection Lookback" setting** (Settings page; `detection_lookback`, default 60 min). Tune how far back each run scans — tighten it on a massive deployment, widen it if forwarders lag. It sets the search's `dispatch.earliest_time` via a plain property write (no fragile search-string edits).
- **Accepted tradeoff (solve for the majority):** a feed whose parsed `_time` is skewed further than the lookback window from its ingest time won't be tracked accurately. Catching that rare misconfigured-timestamp case would require a wide window, which is a non-starter at PB scale.
- `heartbeat-v23.js` → `heartbeat-v24.js`, `settings-v58.js` → `settings-v59.js` (cache-bust).

## [v1.6.1] - 2026-07-18

### Fixed — build 83 (detection tstats performance)
- **The detection `tstats` no longer includes `earliest=-2y@d latest=+2y@d` inside its `where` clause** — this was crushing performance on large tenants. Those tokens are not `tstats` index-time modifiers like `_index_earliest`; they force a per-row `_time` filter across a 2-year span and defeat the tsidx acceleration. The `where` clause now carries only `_index_earliest=-7d@h _index_latest=now` (efficient index-time bucket pruning). The ±2 y **event-time guard is retained at the job level** — `dispatch.earliest_time=-2y@d`/`dispatch.latest_time=+2y@d` for the scheduled search and the `{earliest:'-2y@d', latest:'+2y@d'}` search-manager range for Run Detection — so skewed timestamps (e.g. year-less syslog dates that roll a full year) are still covered. Runtime-verified: an event ingested now with a 4-day-old timestamp is still detected as fresh (`status=good`), and the query no longer scans the 2-year event range per row.
- **Tradeoff note:** with the guard back at the dispatch level, a pre-v1.4.1 `local/savedsearches.conf` override of the dispatch window could again shrink the event range on an un-remediated upgrade (see the v1.4.3 note on removing such stale overrides). This was the reason b76 embedded it in the `where` clause; the performance cost of that placement outweighed the benefit.
- `heartbeat-v22.js` → `heartbeat-v23.js` (cache-bust).

## [v1.6.0] - 2026-07-17

### Fixed — build 82 (delete-vs-detection resurrection race)
- **A deleted sourcetype can no longer be silently resurrected by a concurrent detection run.** Detection (both the in-browser Run Detection and the every-5-minute *Source Type Monitor* scheduled search) reads the whole monitored lookup, recomputes each row, and writes it back with `outputlookup append=true`. If a row was deleted (single Remove or Clear Never-Seen bulk delete) in the window *after* a detection run snapshotted the lookup but *before* it wrote back, the stale snapshot re-inserted the row — permanently, since the client write queue can't serialize with the server-side scheduled search. Reported as a known architectural gap in prior releases; now fixed.
- **How:** deletes write a lightweight tombstone `{sourcetype, deleted_time}` to a new `heartbeat_deleted` KV collection. Detection and the *Flagged Sources* alert now `| lookup heartbeat_deleted_lookup` and **drop any row whose `added_time` predates its tombstone's `deleted_time`** — so a stale resurrection is suppressed while a genuine re-add (which stamps `added_time = now()`) survives automatically, with no per-add bookkeeping. Restore bumps `added_time` so restored rows survive. A new nightly **Prune Deletion Tombstones** search reaps tombstones older than a day (they only need to outlive one in-flight detection run). Runtime-verified end-to-end: a deleted+tombstoned sourcetype is not re-inserted by a stale-snapshot write, a real re-add survives, and the prune keeps only recent tombstones.
- New: `heartbeat_deleted` KV collection (world-read, admin-write; holds only sourcetype + timestamp), `heartbeat_deleted_lookup` definition, and the Prune search (enabled/disabled alongside detection via Settings and the admin `enable_all`).
- `heartbeat-v21.js` → `heartbeat-v22.js`, `settings-v57.js` → `settings-v58.js` (cache-bust).

## [v1.5.2] - 2026-07-17

### Fixed — build 81 (second multi-agent bug-hunt: alert-secret leak-back + firing/validation hardening)
- **Restore no longer resurrects a deleted alert-target secret, and no longer re-arms an action with no target (security).** One-click Restore re-created the monitored rows but never cleared the admin-only `heartbeat_alert_targets` secret, so a webhook URL / recipient list the operator believed was deleted could silently re-attach on the next refresh; it also kept the row's `alert_action`, leaving it armed with no per-row target (which mis-routes to the global default). Restore now forces `alert_action` to `none`, blanks `alert_action_config`, **and** clears the per-sourcetype target secret for exactly the restored sourcetypes — mirroring the existing single-add guard. Runtime-verified: an orphaned `https://…` target is cleared and the action reset to `none`.
- **Quick-Start / Curated / Recommend-from-data re-adds get the same guard.** These bulk pick paths previously omitted the "blank the per-row alert target on (re)add" step, so re-adding a previously-deleted sourcetype could re-attach an orphaned secret. They now blank the target for every added sourcetype.
- **A literal `|` in a single-action webhook URL no longer truncates the target.** The dispatcher pipe-splits `alert_action_config` only when a row has multiple actions to pair; with one action the whole config string is used verbatim, so a raw pipe in a query string can't silently deliver to a truncated (wrong) endpoint. Verified.
- **Bulk paste-add de-duplicates within the paste.** `foo foo foo` is now one sourcetype, not three — previously it inflated the soft/hard-cap arithmetic and the "Added N" / audit totals.
- **Settings default-threshold now has an upper bound** (525600 min = 1 year), matching the Monitor add path — an absurd value can no longer be persisted.
- `heartbeat-v20.js` → `heartbeat-v21.js`, `settings-v56.js` → `settings-v57.js` (cache-bust).

### Known items intentionally deferred (documented, not fixed here)
- **Delete-vs-detection resurrection race** (architectural — needs a tombstone / update-only-detection design).
- **CSV→KV migration has no persistent "done" marker**, so a legitimately-emptied collection can be re-seeded from a surviving legacy CSV on an upgraded install (e.g. purged audit rows reappearing). Needs a migration-flag design.
- **Two email edge cases** — a duplicate send if the connection resets *after* a blocking `sendemail` job completes, and a success verdict when the job-state readback lacks a `content` block. These interact (naively failing the readback triggers a resend), so they need a sent-marker to fix safely.
- **Non-atomic detection-frequency save** (KV setting + saved-search cron can diverge if the second write fails; the display self-heals on reload and the failure is surfaced).
- Minor: recipient-order can split one digest into two emails; the read-only Settings guard is bound after the auto-save handlers (real protection still holds via `disabled` + server-side admin enforcement); the "every 1 min" cron skips `:00`.

## [v1.5.1] - 2026-07-17

### Fixed — build 80 (use-cases count over-counted shared objects)
- **The "N uses" count could be inflated for sourcetypes referenced by globally-shared saved searches/dashboards.** The reference-count query (added in 1.5.0) used `dedup _obj, _st | stats count`, but the `/servicesNS/-/-/…` REST namespace returns the same object once per ACL context it is visible in (app-scoped **and** global), and `dedup` did not always collapse those duplicate rows — verified live inflating a genuine 5-object count to 7. The query now uses `stats dc(_obj)` (distinct referencing objects), which is immune to the duplicate-context rows. Runtime-verified: the same fixture now reports 5. No other behavior change.
- `heartbeat-v19.js` → `heartbeat-v20.js` (filename cache-bust).

## [v1.5.0] - 2026-07-17

### Changed — build 79 ("use cases per sourcetype" is now one consistent metric everywhere)
The `usage_count` field — shown as the **"N uses" badge** (tooltip "use cases per sourcetype") — previously meant three different things depending on how a row was created, so the badge was not comparable across rows. It now means the same thing on every path: **how many saved searches + dashboards reference `sourcetype=X`** (a use-case / reference count, *not* event volume).

- **Manually-added sourcetypes** used to be hardcoded to `usage_count = 0` even when referenced by many searches/dashboards. The Add Sourcetype path now computes the real reference count and stores it. Verified live: a sourcetype referenced by 3 saved searches + 1 dashboard is written with `usage_count = 4`.
- **Run Discovery** and **Recommend from my data** previously stored event *volume* (`| metadata totalCount` / `| tstats count`) in `usage_count`, mislabeling raw volume as "uses". They now still *select* candidate sourcetypes by what you actually ingest (volume ranking) but *store* the reference count as `usage_count`, so the badge is consistent. "Recommend" also ranks its picks by the reference count instead of volume.
- **Curated picks** now get a real reference count too (was implicitly 0).
- Implementation: a single memoized helper (`getUsageCountMap`, one REST-only pass over `saved/searches` + `data/ui/views`, cached 5 min) feeds every path, so a bulk add computes the counts once. If the count can't be computed (e.g. the role lacks REST access) rows are still written with `usage_count = 0` — it never blocks adding or discovery.
- **Note:** the scheduled **Auto Discovery** saved search additionally factors correlation searches and audit-log query frequency into its count, so a row it creates can show a higher number than the interactive (searches + dashboards) count — both are use-case reference counts, not volume.
- `heartbeat-v18.js` → `heartbeat-v19.js` (filename cache-bust).

### Fixed — build 79 (hardening from a multi-agent bug-hunt)
- **Alert dispatcher could crash and silently disable ALL alerting on one malformed config row.** `load_global_defaults()` in `bin/heartbeat_dispatch.py` called `.strip()` on values read from the `enforceTypes=false` `heartbeat_alert_actions` KV collection; a non-string value (e.g. recipients hand-saved as a JSON array) raised `AttributeError` *outside* the REST try/except, aborting the whole alert action before any notification dispatched. The per-row body is now wrapped so one malformed record only skips itself, and list/non-string targets are coerced (a list of recipients is joined) rather than crashing.
- **"Use cases" count now captures single-quoted `sourcetype='x'` references** and counts each referencing object once. The reference-count query previously matched only bare/double-quoted refs (single-quoted refs were dropped, diverging from the scheduled Auto Discovery search) and inflated the count when one search mentioned a sourcetype several times; it now handles `'…'` and de-duplicates per object.
- **CSV export formula-injection guard now catches a formula char after leading whitespace** (`"\t=cmd()"`, `" +HYPERLINK(…)"`), which spreadsheets trim before evaluating — the previous anchored `^[=+\-@]` test missed them.

## [v1.4.4] - 2026-07-17

### Changed — build 77 (Monitor table: flagged rows take precedence over importance)
- **The Monitor table now sorts flagged sources to the top regardless of importance.** Previously importance was the primary sort key (VIP > critical > … > low), so a healthy VIP outranked a flagged low-importance source — pushing actual outages below rows that need no action. Now the primary key is status (flagged first), with importance ordering *within* each status group and an alphabetical tiebreak. So a flagged low-importance source appears above a healthy VIP, while among flagged rows the most important outage is still first (flagged VIP → flagged critical → …). No data or schema change; sort-only.
- `heartbeat-v17.js` → `heartbeat-v18.js` (filename cache-bust so browsers pick up the new sort without a hard refresh).

## [v1.4.3] - 2026-07-17

### Fixed — build 76 (stale detection rows on upgraded production search heads)
- **Existing rows could keep a stale `minutes_since_seen` forever after upgrading to v1.4.2.** Reported from production: a sourcetype actively ingesting showed `minutes_since_seen = 6000` in `monitored_sourcetypes` while a manual run of the detection SPL correctly computed 0. Root cause: any pre-v1.4.2 **`local/savedsearches.conf` override** of the Source Type Monitor search (created whenever the search was edited/saved in the UI on an older build) survives the app upgrade and keeps re-imposing the old `-24h` **dispatch** window. Because the dispatch window bounds *event* time, a feed whose timestamps parse >24 h in the past stayed invisible to the tstats leg even on v1.4.2 — the `prev_last_seen` carry then re-wrote the frozen value every 5 minutes (reproduced live: b75 SPL dispatched at `-24h@h` left a seeded row at 6000 while its sourcetype ingested continuously). Fix: the ±2 y event-time guard now lives **inside the tstats `where` clause** (`earliest=-2y@d latest=+2y@d`) in both the scheduled search and the dashboard's Run Detection — in-SPL time modifiers take precedence over the dispatch window, so a stale local override can no longer shrink the detection window (verified: the hardened SPL under a stale `-24h` dispatch window updates the row to ~0/good in one run). The ±2 y dispatch window is kept as belt-and-braces.
- **Production remediation note:** if the *entire search string* (not just the dispatch window) is overridden in `local/` on the search head, delete that `search` attribute from `SA-Data-Heartbeat/local/savedsearches.conf` (or re-save the search with the shipped SPL) so upgrades apply. Check which layer wins with `splunk btool savedsearches list "Data Heartbeat - Source Type Monitor" --debug`.

## [v1.4.2] - 2026-07-16

### Added — build 75 (Clear Never-Seen bulk delete + index-time detection window)
- **Clear Never-Seen bulk delete** (Monitor toolbar). Removes every sourcetype whose Last Seen is **Never** in one operation, with a triple-verify flow before anything is touched: the modal lists **every** in-scope row for review (verify 1: reviewed checkbox), the user must type the exact row count to arm the delete button (verify 2), and the armed button still asks a final confirmation (verify 3).
- **One-click Restore / recycle bin.** Immediately before the deletes run, the full in-scope row set is snapshotted to a new `heartbeat_recycle_bin` KV collection (admin-only; replaced on each bulk delete; deliberately separate from the nightly DR backup so an interactive delete can never overwrite the recovery point). If the snapshot write fails, **nothing is deleted**. The same modal offers Restore — thresholds, importance, and notes come back exactly; per-row alert targets are not restorable (their secrets are deleted with the row) and the dialog says so up front. A **Download CSV copy** button provides an offline copy (with Excel formula-injection guarding); names can be re-added anytime via Add Sourcetype → paste list.
- Each per-row delete reuses the existing per-key remove path, so alert-target secrets are cleaned up row-by-row (no orphaned webhooks), and the whole operation is written to the audit log.

### Changed — build 75
- **Detection freshness is now a pure ingest-time window.** The Source Type Monitor / Run Detection tstats leg adds `_index_earliest=-7d@h _index_latest=now`: a sourcetype counts as alive based on when Splunk *received* its events, regardless of the timestamps inside them. The lookback is 7 days (was effectively 24 h) so gaps up to a week report their true age instead of surviving only via the previous-value carry, and a source whose last data predates its monitoring row shows a real age instead of "Never" — still a cheap tsidx scan. Previously the `-24h` dispatch window bounded event time, so a feed whose timestamps parsed >24 h wrong (device clock skew, timezone mis-parse, backfill) was invisible to detection while actively ingesting — verified live: an event ingested seconds ago with a 3-day-old timestamp was flagged "never seen". Because index-time modifiers do not bypass the event-time range, the dispatch window widens to ±2 y as the event-time guard — ±2 y (not ±30 d) because the classic failure is a year-less syslog date crossing `MAX_DAYS_HENCE` and rolling back a **full year** (also verified live; a ±30 d guard missed it), while still letting bucket pruning skip ancient buckets on long-retention tenants. `runSearch`/`runWriteSearch` accept an optional per-call time range so only detection pays the wider scan.
- `heartbeat-v16.js` → `heartbeat-v17.js` (cache-bust for the new modal + detection SPL).

## [v1.4.1] - 2026-06-21

Hardening pass (builds 68–74). A deep multi-agent audit + a full live re-install on Splunk 10.2.3 (single instance and a real 3-member SHC) surfaced 23 issues; all fixed and re-verified on a freshly installed/deployed package. **Build 69** adds two fixes from a follow-up 16-agent deep-inspection pass:

### Fixed — build 74 (20-persona QA + developer regression soak)
A 20-persona QA/developer soak (193 checks; every persona re-verified the full bug registry as still-fixed, then hunted new defects) caught a regression in the build-73 onboarding fix plus a DR gap and three minor items:
- **Non-admin onboarding banner regression** (major). The build-73 fix hid the empty-state onboarding banner for non-admins in `init()`, but `renderMonitorTable` re-shows it on an empty collection — so a read-only user on a fresh install still saw the actionless "Pick one" dead-end. Now a higher-specificity CSS rule (`.hb-readonly .hb-onboarding`) hides the whole shell so the JS toggle can't re-expose it.
- **Nightly KV Backup could destroy the recovery point** (major). The Restore search guards against an empty input (`override_if_empty=false` + row-count check), but the Nightly Backup that *feeds* it did not — so the night after an accidental wipe, the backup would overwrite the good snapshot with nothing. The backup now carries the same guard.
- **Read-only editor badges** (importance/notes/alert-action) are now truly inert for non-admins (`tabindex="-1"`, no `role="button"`) instead of only mouse-disabled — a keyboard user could previously tab into and open the editors.
- **Filter chips** now restore their active highlight from the persisted filter on reload (the table was silently filtered while the chips showed "All").
- On-demand/quick-start **discovery-source tags** (`metadata`/`curated`/`recommended`) now render with a friendly label + icon instead of raw text; `app.manifest` releaseDate updated.

### Fixed — build 73 (48-area parallel probe)
A 48-distinct-area parallel sweep (time/i18n/CSRF/lifecycle/concurrency/version-compat/dispatcher-internals/conf-spec/Cloud-banned/…; 304 checks, every failure re-verified) found three real items in areas earlier rounds hadn't deeply probed — fixed here:
- **Dispatcher survives a truncated results file** (major). A partially-written gzip `results_file` (disk-full / OOM-killed dispatch) raises `EOFError`, which is **not** an `OSError` subclass and so escaped `read_alert_results`'s handler and crashed the whole alert action. `EOFError` is now caught (degrades to "no rows" like every other read failure). A non-object JSON payload on stdin now also fails gracefully (`return 2`) instead of an `AttributeError`.
- **Uninstall steps reordered** (major, security-relevant). The steps told admins to remove the app *before* deleting the KV collections — but the deletion REST path is namespaced to the app, so it 404s once the app is gone and the **webhook/recipient secrets silently persist** (the exact thing that section exists to prevent). Deletion now comes first, while the app still exists.
- **Leak hygiene + UX**: the 60s search watchdog timer is cleared on settle (frees its SearchManager closure immediately); the non-admin empty-state no longer shows an actionless "Pick one" onboarding banner; README wording corrected (the app uses Splunk Web's jQuery/SplunkJS via `require()`, doesn't bundle them).

### Fixed — build 72 (third deep audit — re-architecture edge cases)
A third 12-lens adversarial audit (each finding re-verified, most reproduced live) targeted the build-70 per-row-secret re-architecture and surfaced real edge cases it introduced — fixed here:
- **Restore no longer re-leaks secrets** (high). Restoring a DR snapshot taken on a pre-v1.4.0 build copied the old `alert_action_config` straight into the world-readable `monitored_sourcetypes`, re-exposing webhook URLs/recipients (verified live). The Restore search now blanks `alert_action_config` before writing back, so it can never repopulate a secret into the world-readable collection.
- **Scheduled alert results are no longer world-readable** (high). The "Flagged Sources" alert re-joins the per-row secret into its results so the dispatcher can deliver — but a scheduled search's dispatch artifacts inherit its read ACL, and that search was `read:[*]`, so a non-admin could read the results and harvest the secret (verified live: viewer read the secret; after the fix viewer gets HTTP 403). The search's read is now restricted to `admin`/`sc_admin`; the scheduler still runs it, so delivery is unaffected.
- **Secret-migration is now self-healing** (high). The one-time CSV→KV secret relocation was guarded "run once"; if the copy succeeded but the source-blanking failed, the secret stayed in the world-readable collection forever. It's now keyed off the source still holding secrets (retried next admin load), and the source is blanked only after the copy is confirmed — so a failed copy can never destroy the targets either.
- **No orphaned-secret resurrection** (medium). `removeSourceType` now reliably clears the per-row secret (delete, or blank on failure) before reporting success, and a fresh (re)add blanks any stale target — so an orphaned webhook can't silently re-attach to a re-added sourcetype. `updateAlertAction` writes the target first, then arms the action, so a partial failure leaves the alert off (fail-safe) rather than armed-but-target-less.
- **SSRF guard closes the IPv4-mapped IPv6 bypass** (medium). The IPv4-mapped IPv6 form of a blocked address (carrier-grade-NAT / cloud metadata-proxy ranges) slipped past the IPv4-only checks; mapped addresses are now normalized to their embedded IPv4 before the block checks.
- **Docs/DR scope corrected**: the README "Backup & restore" note and the `monitored_sourcetypes_backup` comment now state that alert target secrets aren't part of the monitored-list DR snapshot (re-enter after a restore); the alert search preserves a legacy per-row config during the upgrade window; CHANGELOG collection count fixed ("seven").

### Fixed — build 71 (40-round Splunkbase submission-readiness testing)
A 40-round test sweep (live functional on a fresh Splunk 10.2 instance + RBAC/security probes + AppInspect cloud/future/manual + packaging/manifest/docs review; 220 checks, 0 confirmed failures) surfaced two doc/polish items, fixed here:
- **Uninstall instructions now list all seven KV collections** — the data-deletion list omitted `heartbeat_alert_targets` (the per-sourcetype webhook/recipient secret collection added in build 70), so following it literally would have left those secrets on the instance. Added it (the section's whole purpose is to scrub persisted secrets).
- **Alert notification "last event" text is now grammatical** — `_fmt_since` rendered "1 hours ago" / "1 days ago"; it now produces correct singular/plural ("1 minute/hour/day ago", "N minutes/hours/days ago") with consistent "ago" phrasing across all branches.

### Fixed — build 70 (20-persona audit, adversarially verified)
A 20-distinct-persona review (accessibility, KV-concurrency, RBAC, SPL, JS, packaging, i18n, alert-dispatch, perf, docs, regression-guard, …) surfaced 23 substantiated defects; **all 23 are fixed here**, each adversarially re-verified.
- **Accessibility — per-row controls were mouse-only.** The importance / notes / alert-action badges were bare `<span>`s (no role, tabindex, or keydown) and the importance popover options were non-focusable `<div>`s — unreachable by keyboard/screen-reader. All now expose `role="button"`/`role="menu(item)"`, `tabindex`, `aria-label`, and Enter/Space/Arrow/Escape handling. The per-row threshold input gained an `aria-label`, and for non-admins it now renders genuinely `readonly` (was only visually dimmed but still keyboard-editable). The three `✕` modal-close buttons got `aria-label`s.
- **Settings could silently fail to persist.** `updateSetting` was modify-only, so on a fresh install (or if Settings was opened before Monitor seeded `heartbeat_settings`) a change matched 0 rows, persisted nothing, yet still showed "Saved." It's now a true per-key upsert that creates the row when absent and preserves its description.
- **`$…$` in a note/config/sourcetype broke the write.** The KV-write SearchManagers ran with `{ tokens: true }`, so a value containing a `$…$` substring was parsed as an undefined dashboard token and the write silently timed out. Switched to `{ tokens: false }` (the app builds all SPL programmatically and never uses `$token$`).
- **Enabled-but-unconfigured alert action was mislabeled "Ready."** `loadConfiguredActions` seeded `isConfigured` to `isEnabled`; it now starts `false` so only an action with a real non-empty target shows "Ready" — matching the Settings page.
- **Auto-Discovery showed success before the write.** The "Discovered N" toast fired before the KV write, so a failed save showed green *and* red at once with nothing persisted. The toast now fires only inside the write's success branch. A read-only user opening Monitor on a fresh install no longer triggers a spurious "you need the admin role" toast (the CSV→KV migration now runs only for users who can write). Settings' per-action toggle now reverts on save failure instead of showing a stuck "enabled."
- **Health-metrics write no longer races the dispatcher.** The "Health Metrics" search did a full read-modify-write of `heartbeat_metrics` every 5 min, which could clobber a concurrently-inserted `heartbeat.dispatch_deferred` row. It now appends a single row with a ring-buffer `_key` (`append=true`, bounded ~10k rows) and never rewrites the collection. The two `heartbeat_alert_actions` writers (Monitor + Settings) likewise switched to per-key `append=true` upserts.
- **Security — per-row webhook/recipient secrets are no longer world-readable.** The per-row alert target (webhook URL / email recipients) was stored in `monitored_sourcetypes.alert_action_config`, which is `read:[*]` — any authenticated user could harvest every org's incoming-webhook URL via `| inputlookup` or the KV REST API. The secret now lives in a new **admin-only** `heartbeat_alert_targets` collection (keyed by sourcetype); `monitored_sourcetypes` keeps only the non-secret action name, so the **non-admin read-only Monitor view is preserved** while the secret is hidden. The admin-context "Flagged Sources" alert search looks the target up server-side (delivery unchanged); a one-time migration relocates existing per-row secrets and blanks them in the source. The nightly DR copy (`monitored_sourcetypes_backup`) read is also restricted to `admin`/`sc_admin`. The SSRF blocklist now additionally rejects RFC 6598 CGNAT space (`100.64.0.0/10`) and any non-globally-routable IPv4.
- **Add-Sourcetype dropdown is capped** at 1000 options (with a "use the Type/paste tab" hint) — an uncapped `| metadata` froze the UI on 10k+ sourcetype tenants.
- **Machine-readable webhook digest** now includes `last_seen`, so a consumer can distinguish "never seen" from "seen long ago" (parity with the email/Slack/Teams channels).
- **Audit log** now renders `alert_action_changed` → "Alert Action Changed" and `notes_updated` → "Notes Updated" (were raw codes), with matching filter choices and colors.
- **Docs/labels corrected.** Detection help text now describes `tstats`/`_indextime` (was the stale `| metadata`/"last-event time"); the README FAQ distinguishes on-demand Run Discovery (`| metadata`) from the scheduled daily Auto Discovery (`| rest` + `index=_audit`) and documents that Send Test Alert requires `admin_all_objects`; "Recommend from my data" failure toasts point to the real "Curated picks" button; the `heartbeat_metrics_seed.csv` header gained the declared `deferred_count` column.

### Fixed — build 69 (post-audit deep inspection)
- **Every alert digest said "Last event: never"** even for a source that had sent data and gone silent. The "Flagged Sources" alert search's `| table` dropped `last_seen`, so the dispatcher's `_fmt_since` (which keys off it) collapsed every source to "never (no events on record)". Added `last_seen` to the alert `| table` — digests now render the real elapsed time (e.g. "3 hours ago"), reserving "never" for genuinely unseen sources. Also set `last_seen` on the synthetic test-alert payload.
- **A curated sourcetype with a `/` in its name was un-removable.** `WinEventLog:Microsoft-Windows-Sysmon/Operational` (a one-click curated pick) has a `/` in its KV `_key`; the per-key REST `DELETE` percent-encoded it to `%2F` in the URL **path segment**, which the splunkweb `/__raw/` proxy can reject on Cloud — leaving the row stuck. `removeSourceType` now deletes by `?query={"_key":…}` (the key rides in the query, not a slashed path segment) — still a single-document delete, no full-collection rewrite.
- Hygiene: removed a dead `first(status) as old_status` aggregation from the detection SPL (parity with the JS); corrected a stale `.splunkignore` comment referencing the removed `monitored_sourcetypes_backup.csv` (now a KV collection).

### Fixed — runtime blockers

### Fixed — runtime blockers
- **Alerting/admin could not run on Splunk Cloud / 10.2 without Python 3.13.** `python.required` listed only `3.13`; Splunk runs "the highest version available from your list," and 3.9 is the 10.2 default (3.13 is opt-in), so a tenant without 3.13 had no satisfiable interpreter and the dispatcher + REST handler silently couldn't run. Now `python.required = 3.9, 3.13` (`restmap.conf`, `alert_actions.conf`) — runs on 3.9 everywhere, prefers 3.13 where enabled.
- **Notification flood.** `alert.digest_mode = 0` made splunkd invoke the alert action once *per flagged source*, so a fire with N flagged sources sent N separate emails/messages — defeating the consolidated-digest design. Now `alert.digest_mode = 1` (verified live: 3 flagged sources → 1 consolidated email).

### Fixed — data integrity & upgrades
- **Upgrade no longer wipes settings, alert-action config, audit history, or metrics.** The shipped seed CSVs were named like the runtime files, so an upgrade overwrote the user's data before the CSV→KV migration could read it (and alert-action config had no migration at all — alerts then delivered to nobody). Seeds are now `*_seed.csv`; the migration reads the user's *surviving* runtime CSV first and only falls back to the shipped defaults on a fresh install.
- **Lost-update writes.** Per-row edits (threshold/importance/notes/alert-action), add, bulk add, discovery, and remove no longer rewrite the whole KV collection (which could clobber a concurrent detection/discovery/other-tab write). Edits are single-key upserts (`where _key … | outputlookup append=true`); remove is a per-key REST `DELETE`.
- **Monitoring blind spot.** A row with an empty/non-numeric `threshold_minutes` is no longer silently `good` forever — detection coalesces the threshold to a 60-minute default so it still flags.
- **Detection no longer capped at 10,000 sourcetypes.** Switched the detection's `| metadata` (silently capped at 10k) to `| tstats max(_indextime) … by sourcetype` (no cap, tsidx-only).
- **Audit log is capped** at the most recent 5,000 entries (was unbounded).

### Fixed — security
- **Webhook/Slack/Teams URLs and email recipients are no longer world-readable.** The `heartbeat_alert_actions` KV collection was `read:[*]`; any authenticated user could read every configured webhook secret via the KV REST API. Read is now restricted to `admin`/`sc_admin` (delivery via the scheduled alert verified to still work).

### Fixed — non-admin experience & UX
- **Non-admins get a coherent read-only view** on both Monitor and Settings — the onboarding Quick-Start CTAs, toolbar buttons, per-row controls, and Settings toggles are hidden/inert, and a clear "admin required" message replaces the generic write-failure toast. A single client-side permission chokepoint backs the server-side ACL.
- **Long-silent sources read truthfully in alerts.** A source silent for years is shown with its real last-seen age (e.g. "740 days ago"), not mislabeled "never"; "never" is reserved for sources with no events on record (`last_seen=0`).
- **Clearer "Recommend from my data" failure** — points non-admins lacking index access to the curated picks instead of a raw error.
- **Dispatch no longer drops its tail silently** under a tight wall-clock budget — a deferred-count metric (`heartbeat.dispatch_deferred`) is recorded so the drop is visible.

### Changed — docs & packaging
- README corrected to describe the **seven KV-store collections** (not "one collection / CSV lookups"), the consolidated-digest model, `tstats`-based detection, the admin-only write/secret model, and a correct uninstall procedure that deletes the KV collections (where secrets persist). Removed the false claim that the manifest declares a "Cloud" `platformRequirements` key.
- `.slimignore` now excludes `__pycache__`/`*.pyc` (kept in sync with `.splunkignore`) so a SLIM build can't bundle Python bytecode.

## [v1.4.0] - 2026-06-18

Search Head Cluster bug-fix pass (six issues found running v1.3.0 on a live Splunk Cloud SHC).

### Fixed
- **Negative / wrong "Last Seen" from bad event timestamps.** Detection now keys off `recentTime` (when Splunk *received* the data, i.e. `_indextime`) instead of `lastTime` (the event's own timestamp). A future-dated or way-in-the-past event no longer makes a source read as a giant negative "minutes since" or get silently marked `good` / `flagged forever` — the monitor measures actual data flow, robust to clock skew and bad timestamping. Belt-and-suspenders future-clamp + display floored at 0; a `future-dated` badge surfaces any legacy/skewed rows. Applied to both the scheduled `Source Type Monitor` SPL and the JS "Run Detection" query.
- **"Run Discovery" returned nothing on a Search Head Cluster.** The button ranked `| metadata` on `totalCount`, which is null/0 on a distributed/SHC merge, emptying the result. Now coalesces `totalCount` and ranks by sourcetype so discovery surfaces sourcetypes on SHC and standalone. *(The richer saved-search-dispatch discovery is a planned follow-up.)*
- **Discovered sourcetypes showed the wrong provenance.** Run Discovery reads index metadata, but discovered rows were hard-coded with `discovery_source="audit_logs"`; they now correctly record `discovery_source="metadata"`.
- **Settings alert-action config never persisted across the SHC.** The enabled flag + recipients/webhook lived in a CSV lookup; a runtime `outputlookup` to a CSV on an SHC writes member-locally and does NOT replicate. Migrated the alert-action settings to a **KV-store collection** (`heartbeat_alert_actions`) which replicates cluster-wide; the dispatcher reads it via REST instead of the on-disk CSV.
- **Audit log + self-monitoring metrics didn't replicate across the SHC.** Both were CSV lookups written at runtime, so on a Search Head Cluster they diverged per member (the Audit page showed only the node you happened to hit). Migrated both to **KV-store collections** (`heartbeat_audit_log`, `heartbeat_metrics`) that replicate cluster-wide. On upgrade from a CSV-backed version, existing rows are seeded into KV on first dashboard load (the same one-time CSV→KV migration used for the monitored-sourcetypes list).
- **App settings + the nightly DR backup didn't replicate across the SHC** (and settings reset on every upgrade). `heartbeat_settings` (Detection Frequency / Default Threshold) and the `monitored_sourcetypes_backup` snapshot were runtime-written CSV lookups — member-local on an SHC, and the shipped settings CSV was overwritten on each app upgrade, resetting saved values. Both moved to **KV-store collections** (replicate cluster-wide and survive upgrades); the shipped defaults seed the settings KV on first load. *This completes the migration — every runtime-written lookup is now KV-backed.*
- **Settings showed actions disabled even when used per-row.** Choosing an alert action on a Monitor row now also enables it in the Settings KV (enable-only; never blanks a configured recipient), so Settings reflects what's actually in use and the dispatcher's global-default fallback applies.
- **New sourcetypes loaded with a default Note.** Discovered / added / curated sourcetypes now load with an **empty** Notes column (the catalog still sets importance/threshold).
- **Declared `python.required = 3.13`** (`restmap.conf`, `alert_actions.conf`) alongside `python.version = python3`. Splunk Enterprise 10.2+ **deprecates `python.version` in favor of `python.required`** — AppInspect's cloud checks `check_script_restmap_conf_python_required` / `check_alert_actions_conf_python_required` flag a missing `python.required` as a `future_failure` (Cloud-compatibility-in-the-future warning). `python.required` is ignored by pre-10.2 releases, which fall back to `python.version`, so shipping both is safe across versions.
- **Corrected stale/incorrect changelog notes** — earlier entries wrongly stated `check_for_updates` must be `0` (a public Splunkbase app requires `1`, which is what ships) and claimed the app ships `distsearch.conf` lookup replication (it does not; SHC-replicated state is KV-backed).

### Added / Changed
- **Alert Action column: "+" affordance.** After picking an action, a `+` button makes it clear you can add more than one action per source (storage already supported multiple).
- **Settings: Save button disables after a successful save** (re-enabled on the next edit/toggle) so it's clear the save took effect — consistent across Email / Slack / Teams / Webhook.

### Alert notifications — consolidated, cleaner delivery
- **Digest model: one notification per destination, not one per source.** When an alert fires with multiple flagged sources, each destination receives a **single consolidated message** instead of one-per-source — far less noise. Applies to all four actions; sources sharing a destination are grouped, distinct destinations stay separate.
- **Email is now a clean HTML table.** Replaced the single run-on plaintext line with Splunk's native HTML results table (`sendemail sendresults=true inline=true format=html`) listing every flagged source as a row — Source type · Status · Importance · Last event · Threshold — under a one-line summary. This is the Cloud-safe path, verified on a live 8-node SHC through a mailpit SMTP sink. *(A custom-branded HTML card was prototyped but dropped: Splunk's `sendemail` HTML-escapes a custom `message=` body, so a hand-built card arrives as raw source. The rich branded layout lives on Slack/Teams instead.)*
- **Slack → Block Kit; Teams → multi-section MessageCard.** Each renders a header + one section per flagged source + a "View in Splunk" button/action (Slack capped under its 50-block limit with an "…and N more" summary; a plain-text fallback covers notifications/screen readers).
- **Webhook is now a digest envelope** *(breaking change for webhook consumers)*: a single POST of `{app, alert_search, fired_at, splunk_url, count, sources:[…]}` — read `sources[]` (previously one object per source at the top level).
- Every cell value is SPL-sanitized before interpolation and HTML-escaped by sendemail on render, so neither SPL nor HTML injection is possible (verified against a hostile sourcetype).

## [v1.3.0] - 2026-06-17

Branding + Splunk Cloud Search Head Cluster (SHC) compatibility.

### Fixed
- **Splunk Cloud / SHC install failure — `app.manifest` never declared search-head-cluster support.** Splunk Cloud Platform runs the search tier as a Search Head Cluster (SHC), and the Packaging Toolkit (SLIM) schema **defaults `supportedDeployments` to `["_standalone", "_distributed"]` when the field is omitted — which excludes `_search_head_clustering`**. Because the manifest had no `supportedDeployments` field at all, Cloud rejected the install with *"does not support a SHC deployment"* (surfacing a misleading `platformRequirements` payload that was never the real cause). Added `"supportedDeployments": ["_standalone", "_distributed", "_search_head_clustering"]`. The core monitored-sourcetypes data is KV-backed and replicates cluster-wide; the manifest simply never advertised SHC support. Token values verified against the `splunk-packaging-toolkit` 1.2.8 schema.
- **`app.conf` release hygiene.** Set `is_configured = 0` (clean first-install experience) and synced `app.conf` version to the manifest (was lagging). *(`check_for_updates = 1` is correct for a public Splunkbase app — see the v1.4.0 correction note.)*

### Changed
- **Rebranded from DataDay Technology Solutions to O11y Innovators Network.** Updated author/company/contact across `app.manifest`, `default/app.conf`, `README.md`, `NOTICE`, `PRIVACY.md`, `LICENSE.txt`, and CSS headers. Contact is now `support@o11yinnovatorsnetwork.com` / `https://o11yinnovatorsnetwork.com`. The historical v1.2.x reference to the former proprietary license name is left intact as an accurate record.

## [v1.2.9] - 2026-06-10

Pre-Splunkbase deep audit: three parallel review passes (Python backend, frontend JS, conf/SPL/packaging) with every finding verified against a live Splunk 10.2 instance before fixing. Build 58; build 59 adds the two release-candidate review findings below.

### Fixed — release-candidate review (build 59)
Findings from a second adversarial pass with live verification on Splunk 10.2.3:
- **Audit dashboard FATALed on Splunk 10.x with its own default time range** — 10.x constant-folds `tonumber(<literal>)` at parse time and hard-fails on non-numeric literals, so the build-58 `tonumber("$time_filter.latest$")` bound (literal `"now"`) killed the table and all four charts on every load. Tokens are now hoisted into fields first (`tonumber(field)` is null-safe); verified live with relative, all-time, and absolute-epoch tokens.
- **Restore from Backup could wipe the live KV collection** — the row-count "bail-out" only filters rows; with the shipped header-only backup CSV, `outputlookup` still replaced the collection with empty (reproduced live against a 92-row collection). `override_if_empty=false` added — a 0-row restore is now a warn-level no-op (verified).
- **Email "Test Alert" no longer claims verified delivery** — Splunk's own `sendemail.py` swallows SMTP errors and exits 0, so job state can only confirm submission. The toast and code comments now say "submitted; confirm receipt — failures land in python.log".
- **Admin endpoint was dead on Splunk Free** — Free has no Auth feature, so `current-context` returns an empty capability list for everyone and the fail-closed gate 403'd the Enable Monitoring / Test Alert buttons. When the capability list is empty AND `server/info` reports `isFree`, the gate now allows (Free has no RBAC to protect); Enterprise behavior unchanged.
- **Detection no longer regresses `last_seen` to 0 ("never")** for sourcetypes silent longer than the 24h metadata window — the previous value is carried (`first(last_seen)` + coalesce) in both the scheduled search and the dashboard's Run Detection.
- Auto Discovery candidate hygiene: rex over search strings captures wildcards (`foo*`) and dashboard tokens (`$tok$`) that can never match `| metadata` and would sit permanently flagged — candidates are now filtered through the same sourcetype-name allowlist the UI bulk-add uses.
- Interactive test-alert email uses a 15s submit timeout (the 30s blocking submit + 10s verify could outlive splunkweb's ~30s proxy window, showing "failed" for an email that delivers).
- Completed the `.data()` → `.attr()` conversion for the remove button, threshold input, and importance badge (numeric-looking sourcetypes were coerced, targeting writes at the wrong key); the async default-threshold load no longer clobbers a value the user is typing in the Add modal.

### Fixed — critical
- **Email alerts never sent.** The dispatcher submitted the `| sendemail` job as `search | makeresults | sendemail ...` — a parse-time failure on every Splunk version. splunkd still returned 201 with a sid, so scheduled email alerts *and* Settings → "Send Test Alert" reported success while delivering nothing. The pipeline is now submitted as-is and delivery is confirmed by reading the job back and requiring `isFailed=false` (SMTP failures are now surfaced too).

### Fixed — high
- **Auto Discovery output went nowhere.** The scheduled nightly discovery search ended at `| table` — results were computed and discarded. It now inserts new sourcetypes into the monitored lookup as `pending` rows, insert-only (existing rows and their operator-tuned thresholds/notes are never touched).
- **Hardcoded `/en-US/` URLs** in every REST call (both dashboards + shared utils) broke all writes on non-English locales and `root_endpoint`-prefixed deployments. All URLs now derive the locale/root prefix from the page path.
- **First-run index-permissions modal on Settings was dead code** — it referenced the monitor page's ModalManager, which Settings never loads; even if shown it had no close handler. Implemented locally with proper dismiss + "don't show again".

### Fixed — reliability and correctness
- Audit dashboard time picker: "All time" and absolute date ranges blanked every panel (`relative_time(now(), "0")` is null); `latest` was ignored entirely. All 5 panels now compute robust epoch bounds.
- Persist REST handler: `splunk.rest` raises `AuthenticationFailed`/`AuthorizationFailed`/`SplunkdConnectionException` even with `raiseAllErrors=False`; these crashed the persist process mid-toggle. Capability lookups now fail closed, per-search toggle failures report per-search, and a top-level handler guard returns a clean 500.
- Saved-search names URL-encoded in the admin handler's REST paths (early-8.x bundled httplib2 doesn't encode spaces; `http.client` rejects them).
- Email test alert now reads the splunkd URI from the persist request's `server.rest_uri` (the previously-consulted keys don't exist), fixing non-default management ports.
- Dispatcher: per-item hard budget (210s) + retry-shedding near the soft budget so one pool of dead webhooks can't run into Splunk's 300s SIGKILL with no summary; a timed-out blocking email submit is no longer resubmitted (duplicate-email risk); Slack message no longer renders "threshold None min".
- Detection from the Monitor page used `join [| metadata ...]` — the subsearch's 50k row cap could silently truncate metadata and mis-flag sourcetypes on very large environments. Rewritten to the same metadata-outer/append form as the scheduled search.
- SearchManager instances are now disposed after every search (previously ~120 leaked managers/hour on an open dashboard via the 30s auto-poll); audit-log writes are serialized through the shared write queue (concurrent writes could drop entries); Settings writes serialized the same way (rapid edits could clobber each other).
- `disabled` flag normalization unified — splunkd returns boolean/number/string by version, and two sites treated `"0"` as disabled, showing wrong toggle/banner state.
- Settings "Default Threshold" was write-only — now loaded on Monitor init, applied to the Add modal and used as the add fallback. A user-entered threshold is no longer silently overridden by the catalog's auto-classification.
- Detection toggle in Settings now also schedules the three support searches (Health Metrics, Detection Stalled, Nightly KV Backup) so self-monitoring and backups actually run when monitoring is enabled via Settings (matches the Enable Monitoring button's enable_all).
- jQuery `.data()` reads replaced with `.attr()` for notes/config/sourcetype badges — `.data()` coerces numeric/JSON-looking values (a pasted JSON note rendered `[object Object]` and saved corrupted).
- CSRF token cookie now matched by page port (two Splunk instances on one host could grab the wrong instance's token → 401 on every POST).
- SPL escaping no longer mangles apostrophes (`it's` round-tripped as `it\'s`); `|` rejected in per-row action configs (it's the storage delimiter — a value containing it shifted every later action's config).
- Audit log "added" entries record the actual added names (previously a wrong subset when failures interleaved mid-batch); keyboard shortcuts (`a`/`d`) respect the read-only permission gate; VIP-flagged stat-card alert styling existed only in JS — CSS added; bulk-add modal threshold respects the configured default.

### Removed
- Dead `heartbeat_settings` KV collection + its two transforms stanzas + meta grant (settings live in `heartbeat_settings.csv`; nothing referenced the collection).
- Settings fields the dispatcher never read: email "Subject Prefix", Slack "Channel", webhook "HTTP Method" — same silent-no-op class as the v1.2.8 stub removal.
- Dead code: legacy Save/Discard action-bar functions, unused `enableSearch` alias, dead `#btn-onboarding-discover` handler, unused constants; duplicate 29-line `LICENSE` stub (canonical `LICENSE.txt` stays).

### Packaging / platform
- `python.required = 3.13` declared alongside `python.version` in `alert_actions.conf` and `restmap.conf` (Splunk 10.2+ deprecation; older releases ignore it).
- `[id]` stanza restored in app.conf (required for Splunkbase/SSAI; clears two AppInspect warnings). Note: the v1.2.7 entry below claimed removing `[id]` was a Cloud fix — that was wrong; the current AppInspect cloud tag passes with it present and warns without it.
- `.gitattributes` export-ignore restored — the release tarball is back to ~128 KB / 52 files (tests and dev artifacts were shipping again).
- Versioned asset filenames bumped (`heartbeat-v16.js`, `settings-v56.js`, `utils-v5.js`, `heartbeat-v3.css`) so Splunk's static cache can't serve stale code after upgrade.
- README corrected: support matrix (Enterprise 8.2+), one KV collection (not two), accurate uninstall/sensitive-data cleanup, Detection Stalled described as a tracked alert, issues link aligned with the manifest.
- Auto Discovery `_audit` subsearch capped at 50k (was 100k — above the append maxout, silently truncated).

## [v1.2.8] - 2026-06-07

Follow-up to the v1.2.7 audit, driven by live in-browser validation of the Settings and per-row alert-action flows.

### Fixed
- **Removed two dead alert-action stubs from the Settings page.** Settings → Alert Actions listed six action types, including **PagerDuty** and **ServiceNow**, but the dispatcher (`heartbeat_dispatch.py`) only implements **Email, Slack, Microsoft Teams, and Webhook** — any other action is explicitly rejected as "unknown" and skipped. A user could therefore enable and configure PagerDuty or ServiceNow in Settings and receive **silent no-ops** at alert time. Removed both accordion items from `settings.xml` and their entries from `settings-v55.js` (`actionNames`, `REQUIRED_FIELDS`). The Settings page now exposes exactly the four shipped channels, matching the per-row action picker (`SHIPPED_ACTIONS` in `heartbeat-v15.js`) and the dispatcher.

### Notes
- The per-row "Not Enabled / Needs Config / Ready" badge and the global "N configured" counter are **by design** (they reflect the channel's *global* Settings state and count *global* action templates respectively; per-row targets live in a separate store) and were left unchanged.
- The non-shipped action definitions retained internally in `heartbeat-v15.js` (`alertActionTypes`, `SAFE_ACTIONS`) are gated out of the UI and kept as v1.3 scaffolding; they are not user-reachable.

## [v1.2.7] - 2026-05-31

Remediation pass from a 60-round adversarial deep audit (Splunk Cloud Classic + Splunkbase readiness). Addresses the confirmed blockers and the highest-value Cloud/Splunkbase gates, security, and correctness findings. Audit reports retained outside the package.

### Fixed — blockers
- **Five scheduled searches shipped enabled.** `dispatch.latest_time = now` and `disabled = 1` were collapsed onto one line in five stanzas (`Nightly KV Backup`, `Health Metrics`, `Detection Stalled`, `Flagged Sources Alert`, `Auto Discovery`), so `disabled` never parsed and the searches — including the alerting one with `action.heartbeat_dispatch = 1` — ran on install. Split onto separate lines; all eight stanzas now ship disabled.
- **Dev scripts with a hardcoded password were packaged.** Removed `check-nav.js`, `open-dashboard.js`, `open-settings.js` (each contained `changeme123`) and added `.splunkignore` so test/dev artifacts can never ship.
- **SSRF via open redirect.** The webhook dispatcher validated only the initial URL, then followed up to 4 redirects without re-checking — reachable to internal/loopback/cloud-metadata hosts. Added a no-redirect, strict-TLS opener for all external webhook POSTs.

### Fixed — Cloud / Splunkbase gates
- Removed the deprecated `[id]` stanza from `app.conf`.
- Removed the alert-action `command` line entirely; `python.version = python3` now drives interpreter selection (a `command = python3 …` line resolves the interpreter via the subprocess PATH, which breaks on a restricted Cloud PATH).
- Populated `app.manifest privacyPolicy` + `releaseNotes`; added README **Prerequisites**, **Outbound Network Access**, and **Uninstall** sections.
- Capped the Flagged Sources alert at `| head 200`, **ranked by a numeric severity `case()` (vip→critical→high→…) so the cap never drops critical rows**, and added a ~90-second wall-clock budget (measured from invocation start) to the dispatcher so it logs a clean summary instead of being silently killed at the alert-action timeout.

### Fixed — security & correctness
- Email now dispatches `content_type=plain` (closes stored-HTML-injection via the email body); `_sanitize_spl_value` tightened to printable ASCII (drops DEL / C1 / NEL / LS / PS / RLO controls that truncated bodies or reversed subjects).
- REST handler returns a generic error to the browser (no fs-path/SSL/exception-text leak) and logs only parameter NAMES, not values (no webhook URL / recipient leakage).
- Confirmed REST RBAC is enforced in-handler (fails closed): `enable_all`/`disable_all` need `edit_search_scheduler` or `admin_all_objects`; `test_alert` needs `admin_all_objects`. (A single `restmap` `capability.post` can't express that per-action split without over-restricting one path, so it is intentionally not used.)
- Frontend: removed `console.log` of the full alert-action config (webhook URLs); whitelisted the `importance` value before it is rendered into markup; clamped the add-sourcetype threshold to a positive range.
- Dispatcher: never-seen sourcetypes now read "never (no events on record)" instead of a raw ~29.6M-minute number; `Retry-After` HTTP-date parsing pinned to UTC; `main()` exits non-zero when deliveries fail or are budget-deferred; broadened exception handling on results/stdin reads (`UnicodeDecodeError`/`OSError`).
- Audit dashboard summary panels' time scope corrected from `-24h@h` to `-30d@d` to match their "(30 Days)" titles.

### Deferred (tracked; need product decisions or live AppInspect/render testing)
- Percentile-based importance bucketing and operator-configurable per-tier thresholds (currently hardcoded 30/60/120/180).
- Per-lookup ACL tightening / `storage/passwords` migration for webhook secrets; `enforceTypes` change.
- Settings/audit write-queue concurrency hardening and KV migration of `heartbeat_settings`.
- Dashboard-token-in-SPL rework in `audit.xml` (pending live AppInspect confirmation) and the accessibility (WCAG/508) pass.

## [v1.2.6] - 2026-05-22

Cloud-readiness audit fix pass. A five-surface deep audit — validated against Splunk Cloud Classic Experience, Splunk Cloud Victoria Experience, and Splunk Enterprise on-prem 9.x/10.x — produced ~53 findings; this release fixes them. Each fix was verified against source.

### Licensing & documentation
- **Relicensed to Apache License 2.0.** `LICENSE.txt` previously contained a proprietary "DataDay Tech Software License" with Free/Premium tiers and a "communicates with DataDay servers for license validation" data-collection clause — for software that has no such code. `LICENSE.txt`, `NOTICE`, and `app.manifest` now declare Apache-2.0.
- **README rewritten to match the actual architecture.** The README claimed "zero `.py` files", "No Python", "No custom REST endpoints", "No web.conf" — all contradicted by the shipped package. It now accurately describes the Python alert dispatcher, the custom REST admin handler, and `web.conf`.
- Removed the unused `commonInformationModels` (Splunk_SA_CIM) declaration from `app.manifest` — the app uses no CIM data models.

### Security
- **Stored XSS** — `discovery_source` was interpolated raw into a CSS `class` attribute in the Monitor table render. Now whitelisted for the class and `esc()`-escaped for the label.
- **Custom REST endpoint hardened** — `web.conf` reduced to a single `[expose]` stanza, `methods = POST, OPTIONS` only (was GET-reachable, i.e. CSRF-able). The handler rejects any non-POST request and no longer reads parameters from the query string.
- **`test_alert` capability tightened** — now requires `admin_all_objects` (full admin), not the broadly-held `edit_search_scheduler`, since it can drive outbound HTTP.
- **Webhook URLs masked in logs** — `heartbeat_dispatch.py` logged full Slack/Teams webhook URLs (bearer secrets) on every non-2xx; logs now show `scheme://host/...` only.
- **TLS-bypass removed** — the `HEARTBEAT_DISPATCH_INSECURE` env var that disabled certificate verification for all external webhook traffic is gone; external webhooks always verify.
- **SPL escaping** — `action_type` is now SPL-escaped in the Settings alert-action save (it is read back from a lookup, so a crafted row could otherwise break out).
- Catalog regex compilation skips over-long patterns (ReDoS guard); toast action links are scheme-validated.

### Broken-on-install / packaging
- Shipped the missing seed lookups: `heartbeat_settings.csv` (was referenced as a transform but never shipped — the orphan `null_data_settings.csv` is removed), `heartbeat_alert_actions.csv`, and `monitored_sourcetypes_backup.csv` (header-only) so the Settings page, dispatcher fallback, and Restore search never hit a missing-file error on a fresh install.
- `metadata/default.meta` now has explicit `[collections/...]` and `[alert_actions/heartbeat_dispatch]` stanzas; `export = system` reduced to `export = none` (app-local) to stop global-namespace pollution.
- `monitored_sourcetypes.csv` file mode normalized in packaging.

### Reliability & correctness
- **Detection search rewritten** to put `| metadata` as the outer generating command with the monitored-sourcetypes lookup as a small `append` subsearch — the previous `join` form could silently truncate at the 50k subsearch row cap on large environments and mis-flag sourcetypes.
- **`enableSched = 0` removed** from all scheduled searches — shipping it alongside a `cron_schedule` meant enabling a search by only clearing `disabled` left it unscheduled.
- **"Enable Monitoring"** now enables all six scheduled searches (was three) — detection, alerting, discovery, Health Metrics, Detection Stalled, and Nightly Backup.
- Email alert body is now a single line — a multi-line body interpolated into an SPL `eval msg="..."` parses inconsistently across Splunk versions.
- `Retry-After` parsing accepts decimal seconds and the HTTP-date form (was integer-only).
- `_to_number` rejects `NaN`/`inf` (a stale `"NaN"` cell rendered as `nan` in messages).
- Test alerts use a single fast attempt so the REST handler returns within the proxy timeout.
- `enableSearchByName` normalizes splunkd's `disabled` field (boolean / number / string) before comparing — a successful toggle was being reported as a failure.
- `runDiscovery` calls its finalizer on every path — the Run Discovery button no longer reports "done" before the merge completes.
- Recurring dashboard timers are cleared on page teardown (was leaking on in-Splunk navigation).
- Pagination "Next" clamps to the last page (rapid double-click no longer overshoots into an empty state).
- `updateThreshold` coerces `minutes_since_seen` with `tonumber()` for a correct numeric status comparison.
- Detection Stalled guards against a zero `last_run_epoch` (no false page on a fresh install) and its description now matches what it checks.
- Audit dashboard charts now honor the time-range picker; the Sourcetype filter can select app-wide events.
- Fixed mis-nested `action-config-field` divs in the Settings accordion.

## [v1.2.5] - 2026-05-21

Deep-audit fix pass. A three-surface audit (Python / JavaScript / conf+XML) found 15 verified high-importance defects — including two regressions introduced by the v1.2.4 patch itself. All 15 are fixed here. Each fix was verified against the source; nothing speculative.

### Fixed — Security
- **Stored XSS in the notes popover.** `appserver/static/js/heartbeat-v15.js` — the popover read `notes` back via jQuery `.data()` (which HTML-decodes the value, undoing the render-time `esc()`) and spliced both `notes` and `sourcetype` raw into the popover title and `<textarea>`. A `notes`/`sourcetype` value containing `</textarea><script>…` executed on click. Both values now go through `esc()`.
- **SPL injection via Audit dashboard tokens.** `default/data/ui/views/audit.xml` — five panels used `| search action=$filter_action$ performed_by=$filter_user$ sourcetype=$filter_sourcetype$` with **unquoted** tokens. `$filter_user$`/`$filter_sourcetype$` are fed from `inputlookup` data, so a crafted `performed_by`/`sourcetype` value could break out of the search. All five occurrences are now quoted (`action="$filter_action$" …`).
- **SSRF hardening.** `bin/heartbeat_dispatch.py` — `_validate_webhook_url` now resolves the target host and rejects loopback / link-local / private / reserved / multicast addresses (and `localhost` / cloud-metadata names), failing closed on unresolvable hosts. Closes the SSRF path where a user holding only `edit_search_scheduler` could drive the `test_alert` endpoint to probe internal hosts or the cloud instance-metadata service.

### Fixed — Broken on install / data loss
- **Audit dashboard broken on fresh install.** The `[heartbeat_audit_log]` transform pointed at `heartbeat_audit_log.csv`, which **was never shipped** — every `inputlookup heartbeat_audit_log` errored until the first audit write lazily created the file. The file that *did* ship, `heartbeat_audit.csv`, was an orphan with an incompatible schema. Now ships `lookups/heartbeat_audit_log.csv` with the correct header; the orphan `heartbeat_audit.csv` is removed.
- **Email dispatch still failed on a self-signed cert.** `bin/heartbeat_dispatch.py` — the v1.2.3/v1.2.4 SSL fix picked the no-verify context only when `server_uri` was a literal loopback address; when Splunk supplied an FQDN it fell back to strict verification and failed against splunkd's self-signed cert. The email path now always targets the local splunkd via `127.0.0.1` (mgmt port taken from `server_uri`/env) with the no-verify context — the session key is the real authentication for that same-instance call.
- **Detection clobbered sourcetypes added/removed mid-run.** `default/savedsearches.conf` + `heartbeat-v15.js` — Detection's `outputlookup` had no `append=true`, so it replaced the entire KV collection from a stale snapshot; a sourcetype added through the UI during a Detection run was erased. Now uses `append=true` (per-`_key` upsert).
- **Per-row edits raced and lost data.** `heartbeat-v15.js` — `updateThreshold` / `updateImportance` / `updateNotes` / `updateAlertAction` / `removeSourceType` / `addSourceType` each did a non-atomic `inputlookup|eval|outputlookup` over the whole collection with no concurrency guard. Two quick edits, or an edit overlapping the auto-poll or discovery merge, silently lost a change. All lookup writes (per-row edits, detection, discovery merge, CSV→KV seed) now funnel through a serialized write queue (`runWriteSearch`).
- **`monitored_sourcetypes.csv` shipped with mode `600`.** The cold-start seed could be unreadable by the Splunk service account on a fresh install. Normalized to `644`; packaging now `chmod`s lookup files.

### Fixed — Reliability
- **Health Metrics wrote schema-incompatible rows into the audit log** *(regression introduced by v1.2.4)*. The v1.2.4 patch pointed Health Metrics at `outputlookup heartbeat_audit_log` — a different schema, so `outputlookup` dropped the metric columns and injected empty `health_metric` rows into the Audit dashboard. Health Metrics now writes to a dedicated `heartbeat_metrics` lookup (new `[heartbeat_metrics]` transform + `lookups/heartbeat_metrics.csv`), capped at 10,000 rows.
- **`distsearch.conf` removed** *(regression introduced by v1.2.4)*. The v1.2.4 patch added a `distsearch.conf` `[replicationWhitelist]` claiming it replicated CSV lookups across SHC nodes. That directive governs the **knowledge bundle sent to indexers**, not search-head-cluster member replication — it did not do what the v1.2.4 CHANGELOG/release notes claimed. The stanza is removed; the underlying SHC CSV-divergence concern is tracked for a future KV-store migration of the audit log.
- **Webhook/Slack/Teams alerts dropped on transient 5xx.** `bin/heartbeat_dispatch.py` `_post_json` retried only HTTP 429; a momentary 502/503 returned failure with no retry, while the email path retried. `_post_json` now retries 5xx with exponential backoff.
- **Multi-action config misalignment.** `bin/heartbeat_dispatch.py` — the comma-separated `alert_action` list was filtered for empty tokens but the pipe-separated `alert_action_config` list was not, so a leading/embedded empty action shifted every config out of alignment and misrouted targets. Both lists are now parsed strictly positionally; empty action tokens are skipped in place.
- **"Run Discovery" button stuck spinning.** `heartbeat-v15.js` — `runDiscovery` returned early on a discovery search error without calling its `onDone()` finalizer, leaving the button in its loading state until a page reload. Fixed.
- **"Restore from Backup" could not produce a clean collection.** `default/savedsearches.conf` — used `outputlookup … append=true`, an upsert that left corrupt/stale rows behind. Now a full replace (no `append`), keeping the empty-backup guard.
- **`visibilitychange` re-render destroyed in-progress edits.** `heartbeat-v15.js` — returning to the tab triggered an unconditional full table re-render. Now honors the same skip rules as the 30-second auto-poll.

### Removed
- Dead `[discovery_sources]` KV-store collection from `default/collections.conf` — defined but referenced nowhere.

## [v1.2.4] - 2026-05-19

Splunk Cloud compatibility pass. The v1.2.3 audit caught 29 functional bugs but missed Cloud-submission blockers because it didn't run AppInspect's `cloud_compatible` tag. This release fixes the remaining issues so the app runs unchanged on Splunk Cloud (Victoria + Classic) and Splunk Enterprise on-prem. AppInspect `cloud + cloud_compatible + packaging_standards + splunk_appinspect + migration_victoria + future` (precert): **0 errors / 0 failures / 2 future_failures (advisory) / 3 informational warnings / 127 success / 117 N/A**.

### Fixed
- **Cloud-blocker: `subprocess.run` in REST admin handler.** The "Send Test Alert" path in `bin/heartbeat_admin.py` shelled out to `splunk cmd python3 heartbeat_dispatch.py` via `subprocess.run`. Splunk Cloud forbids subprocess from custom apps. Replaced with in-process import of the dispatcher's per-action functions (`dispatch_slack/teams/webhook/email`) — same code path, no fork/exec.
- **Cloud-blocker: `passSystemAuth = true` in `default/restmap.conf`.** Elevated-privilege handlers are forbidden on Splunk Cloud. Removed. The handler now runs as the authenticated user, which is what the capability gate (`edit_search_scheduler` / `admin_all_objects`) wants anyway.
- **Cloud-blocker: Health Metrics search wrote to `_internal`.** `| collect index=_internal` is forbidden for the default `nobody` saved-search owner on Splunk Cloud — the metrics search would have silently failed there. Now writes to the `heartbeat_audit_log` lookup with `| outputlookup heartbeat_audit_log append=true`.
- **`app.manifest` platform declaration — *later found to be a no-op; see correction*.** Added `"Cloud": "*"` alongside `"Enterprise": "*"` in `platformRequirements.splunk`, believing Splunkbase/Cloud submission required an explicit Cloud platform entry. **Correction (v1.2.9):** this was wrong — `Cloud` is not a valid SKU key (only `Enterprise`/`Free`/`Light`), and `platformRequirements` is *not enforced by Splunk* and isn't even part of `schemaVersion 2.0.0`. The key did nothing for Cloud compatibility and was **removed in v1.2.9** after it began blocking SLIM/Splunkbase upload validation. Real Cloud-install gating is AppInspect cloud-vetting + the Splunkbase listing's compatibility record, not the manifest.
- **SHC replication: CSV-backed lookups didn't replicate.** KV-store auto-replicates across search head clusters (which Splunk Cloud uses under the hood), but our three CSV lookups (`heartbeat_audit_log.csv`, `heartbeat_alert_actions.csv`, `monitored_sourcetypes_backup.csv`) stayed local to whichever node wrote them. Added `default/distsearch.conf` with a `replicationWhitelist` covering `apps/SA-Data-Heartbeat/lookups/*.csv`.
- **Removed `python.required = 3.13` from `default/restmap.conf` and `default/alert_actions.conf`.** Pinning Python 3.13 broke compatibility with Splunk versions shipping older Python (Cloud Victoria currently ships 3.9, on-prem Enterprise 9.x ships 3.9). Falling back to `python.version = python3` only — this raises 2 informational `future_failure` items from AppInspect about Splunk 10.2's deprecation of `python.version`, but those are advisory and don't block submission today.
- **Removed empty `docs/screenshots/` placeholder.** Was only a README.md inside the otherwise-empty directory.

### Changed
- `app.manifest` `releaseNotes` updated to describe Cloud-compat scope.

## [v1.2.3] - 2026-05-18

This release is a hardening pass driven by a multi-pass bug audit. Every fix in this changelog corresponds to a verified, reproducible defect — no speculative changes.

### Fixed — Alert dispatcher (server-side, `bin/heartbeat_dispatch.py`)
- **Email alert path was broken out of the box.** Dispatcher called splunkd at `https://localhost:8089` with strict cert verification — splunkd's default self-signed cert caused `SSL: CERTIFICATE_VERIFY_FAILED` on every email dispatch. Now uses a dedicated, scoped no-verify SSL context **only** for the localhost splunkd loopback (the session key already authenticates us); all external webhook traffic still uses strict verification.
- **Non-URL alert targets crashed the dispatcher.** Typing a Slack channel name like `#security` into the per-row config would hit `urllib.request.urlopen('#security')` and throw `unknown url type` mid-loop. Dispatcher now validates http(s) scheme up front and logs `invalid webhook url` instead of crashing.
- **Exception logs lost row context.** `dispatcher exception: <error>` didn't identify which row failed. Each future is now mapped back to its work item so logs read `dispatcher exception for splunkd/slack: ...`.
- **SPL injection risk in email path.** Email recipients are now validated against a strict email regex (rejects quotes, pipes, backslashes, parens, dollar signs, backticks, control chars); sourcetype/importance/threshold values interpolated into the `| sendemail` SPL string are also sanitized as defense-in-depth.
- **Throttle held the lock during sleep**, serializing entire worker pools instead of just spacing dispatches. Throttle now computes the wake time inside the lock and releases it before sleeping.
- **Email path had no retries** while `_post_json` retried 3× — a transient REST blip would lose the alert. Email path now retries 5xx responses and network errors with exponential backoff.
- **User-Agent header was hardcoded to `SA-Data-Heartbeat/1.2.2`** even after version bumps. Dispatcher now reads the version from `default/app.conf` at startup.
- **Empty tokens in comma-split actions** (`email,,slack`) produced an empty action that logged as `unknown action ''`. Now filtered out cleanly.

### Fixed — REST admin handler (`bin/heartbeat_admin.py`)
- **Privilege escalation / SSRF via admin endpoint.** `/services/data_heartbeat/admin` had `requireAuthentication=true` but no capability gate — any authenticated user (incl. the default `user` role) could toggle scheduled-search state via `enable_all`/`disable_all`, or trigger arbitrary outbound HTTP POSTs through the dispatcher via `test_alert` (SSRF probe of internal hosts, bandwidth funnel). Handler now requires at least one of `edit_search_scheduler` or `admin_all_objects` for all three actions, matching Splunk's own RBAC for these operations.
- **Tempdir leak on test_alert.** Every "Send Test Alert" button click leaked a `/tmp/hb_test_*` directory. Now wrapped in `try/finally + shutil.rmtree`.

### Fixed — Saved searches (`default/savedsearches.conf`)
- **Detection Stalled (monitor-the-monitor) never fired.** SPL parsed `last_actual_run_time` only as ISO-8601 (`%Y-%m-%dT%H:%M:%S%z`), but `| rest` returns this field in different formats across Splunk versions: ISO-8601 on 9.x, space-delimited `2026-05-18 12:34:56 UTC` on 10.x, epoch on some Cloud builds. `strptime` returned null and the `where last_run_age_min > 15` filter dropped every row, so the meta-monitor was silently dead. SPL now coalesces all known formats — verified all three parse to the same epoch.
- **Alert search flooded notifications.** No suppression/throttle was configured, so a persistently-flagged sourcetype re-fired every 10 minutes forever (Slack/Teams/email storm until the upstream feed was fixed). Added `alert.suppress = 1`, `alert.suppress.period = 1h`, `alert.suppress.fields = sourcetype` so each flagged sourcetype only pages once an hour.
- **CSV→KV Migration could clobber live data.** Stanza shipped `disabled=0`, meaning a Splunk Manager admin could click "Run" and overwrite live KV rows (including user-edited importance/notes/alert_action) with the bundled CSV seed. Now ships `disabled=1`; the JS dashboard still seeds via direct SPL when (and only when) the KV collection is empty, so the user-facing path is unchanged.
- **"Restore from Backup" had no validation and could clobber live data.** Stanza shipped `disabled=0` with `inputlookup monitored_sourcetypes_backup.csv | outputlookup ...` — if the backup file was empty, partially written, or corrupted, the restore would upsert garbage into KV. Now ships `disabled=1`, requires `sourcetype` to be non-null/non-empty per row, and adds a `_backup_row_count > 0` guard to bail out on an empty backup.
- **Detection threshold comparison was defensively coerced to numeric.** Splunk's `eval` auto-coerces numeric-looking strings in modern releases, but `tonumber(threshold_minutes)` is now explicit so misconfigured rows can't trigger a lexical comparison silently.

### Fixed — Dashboard JS (`appserver/static/js/heartbeat-v15.js`)
- **"Run Detection Now" wrote to the wrong lookup after KV migration.** Function hardcoded `monitored_sourcetypes_csv` for both read and write — but the live source-of-truth is the KV-store collection `monitored_sourcetypes_lookup` after first-install migration. Detection results landed in the dead CSV; dashboard read from KV; status never updated. Now uses `LOOKUP_FILE` (KV) on both sides.
- **"Run Detection Now" required accelerated data models.** Used `tstats summariesonly=t` which silently returns empty on non-accelerated environments — every sourcetype would get flagged with `last_seen=0`. Now uses `| metadata type=sourcetypes index=* OR index=_*`, matching the scheduled Detection search (no event scans, no DM dependency, includes internal indexes).
- **"Run Detection Now" had no in-flight guard.** Two concurrent calls (button-click + bulk-add success + curated-pick success) raced on `outputlookup`. Now serialized via a module-level flag; duplicate callers skip cleanly and pick up the in-flight run's refresh.
- **Stored XSS in alert-action badges.** Per-row `alert_action` value was interpolated raw into `data-current="..."` and only `"` was escaped in the `title` attribute. An admin with KV write access (or the auto-discovery saved search on a hostile sourcetype-name extraction) could inject `onmouseover=` via a `<`, `>`, `&`, or `'` character. All attribute values now go through `esc()` (5-char HTML escape) and the action class is whitelisted against known action types so an unknown value can't smuggle CSS selectors.

### Changed
- **Slack target placeholder/hint no longer suggests channel names.** The per-row picker previously offered `#security-alerts` with hint "Channel name or webhook URL" — but channel names don't work; only incoming-webhook URLs do. Placeholder is now `https://hooks.slack.com/services/T0/B0/...` with a hint that explicitly rules out channel names.

### Fixed — second audit pass
- **Sourcetype picker dropdown silently hid internal sourcetypes.** `SourceTypeDiscovery.getAvailableSourceTypes` used `| metadata index=*`, which excludes `_*` indexes — so `splunkd`, `_audit`, `_internal`, etc. never appeared in the "Add Sourcetype → From environment" picker even though they're legitimate things to monitor. Same bug in `runDiscovery` (the toolbar's Run Discovery button). Both now use `index=* OR index=_*`, matching Detection.
- **Threshold field accepted `NaN` and persisted it.** A non-numeric paste into a row's threshold input wrote the literal string "NaN" into the KV-store collection. Every subsequent Detection run's `tonumber("NaN")` returned null and the row's status got stuck forever. Now range-checked client-side (`isNaN || < 1 → reject`; clamp at one year) before SPL composition.
- **Stored XSS via the settings lookup.** `displayCurrentSettings` rendered raw `setting_value` (and `setting_name` key) values into the settings summary table — an admin-controlled lookup is still XSS, and the table includes anything that ends up in `heartbeat_settings.csv` via direct edit or future code. All three columns (`key`, value, description) now go through `escapeHtml()`.
- **Stored XSS via the alert-actions lookup display.** The "enabled / configured alert actions" summary rows also rendered action-type names raw. Now escaped, matching the rest of the table.
- **Toggle handler silently reported success when it couldn't verify state.** `enableSearchByName`'s verify-state GET error handler was `function () { callback(null); }` — splunkd returning 500 / timing out / refusing the verify GET was treated as success. The user saw a green toast even though the real state was unknown. Now surfaces the verification error so the toast/error UI can drive a retry.
- **Settings page accepted invalid Slack/Teams/webhook target URLs.** `validateActionItem` only checked "non-empty" — a user could save `#general` as the global Slack target, see "Configured" in the UI, and only discover at first alert that the dispatcher rejects it. Now an http(s) URL regex check fires alongside the empty-check, with the missing-field error string explaining the expected format.
- **`Shortcuts` keydown handler didn't ignore key auto-repeat.** Holding `r` (refresh) spammed `refreshData()` many times per second and flooded splunkd. Now skips events with `e.repeat = true`.
- **Audit-log search had no watchdog timeout.** A slow / hung splunkd would leave the `AuditLogger.log` SearchManager open forever, leaking memory and search slots. Added a 30s watchdog (mirrors the Settings page pattern) plus `search:fail` handling.
- **Duplicate element IDs in `monitor.xml`.** Both the close-X button and the footer Cancel button in the VIP-confirm modal carried `id="btn-cancel-vip"` (same in the action-config modal). Invalid HTML5 + accessibility tools confused. Close-X is now a class-based handler; only the Cancel button keeps the ID.
- **`updateActionBar()` was wired to DOM elements that no longer exist.** `#btn-save-settings`, `#btn-discard-settings`, `#settings-status-text` were removed from `settings.xml` when the page moved to per-control auto-save in v1.2.0, but the JS still targeted them — all `prop()` / `text()` calls silently no-op'd. Reduced to an explicit no-op shim with a comment so the call sites don't break and the misleading code is gone.

## [v1.2.0] - 2026-05-05

### Added
- **Quick start onboarding** — single button on the welcome banner adds 10 critical security/identity/cloud/network sourcetypes from the catalog, so the dashboard isn't empty after install.
- **Keyboard shortcuts** — `r` refresh, `d` discover, `a` add, `?` help. Shown on the help toast. Suppressed inside form fields.
- **Focus trap in modals** — Escape closes; Tab/Shift+Tab cycle without escaping the dialog. Modals now have proper `role="dialog"` + `aria-modal` + `aria-hidden`.
- **Permission-aware UI** — `/services/authentication/current-context` is queried on load; write controls are hidden for users not in `admin`/`sc_admin`.
- **Skip-to-content link** for keyboard users.
- **Tooltips** on all action buttons describe what they do and the keyboard shortcut.
- **README**: Splunk Cloud (Victoria + Classic) section, Troubleshooting, FAQ, Keyboard shortcuts, Permissions, Screenshots layout.
- `docs/screenshots/` directory with capture spec.
- `app.manifest` declares `commonInformationModels: { Splunk_SA_CIM: "5.x" }` and adds Security/Fraud category for Splunkbase listing.
- HeartbeatUtils module expanded: `debounce`, `FocusTrap`, `Permissions`, `Shortcuts`.

### Changed
- **Performance**: detection saved search and discovery flow now use `| metadata type=sourcetypes` instead of `tstats count where index=*`. Drops bucket-only metadata reads instead of event scans, so it's safe on multi-TB tenants.
- **Code consolidation**: `settings.js` and `heartbeat.js` no longer have their own Toast implementations; both delegate to `HeartbeatUtils.Toast` (with safe fallback shims if utils.js fails to load).
- Table headers got `scope="col"` for screen reader column-association.
- Inline error state shown in monitor when sourcetype lookup fails (instead of just a toast).

### Removed
- `appserver/static/js/audit.js` (dead code — never referenced).
- `default/data/ui/views/audit_history.xml` (duplicate of `audit.xml`).
- ~600 lines of duplicated Toast/escape logic across the JS bundle.

### Fixed
- Audit query now caps at 1000 rows after sort (capped earlier in the pipeline so big histories don't choke).
- `escapeString` failures with backslashes inside notes/sourcetype names (audit log composition).

## [v1.1.1] - 2026-05-04

### Added
- `lookups/heartbeat_catalog.csv` — sourcetype catalog now lives in a CSV lookup instead of being hardcoded in JavaScript. New connectors can be added without an app release.
- `appserver/static/js/utils.js` — shared `Toast`, `escapeString`, and `Storage` helpers extracted from the three view scripts to remove duplication.
- Onboarding banner on the Monitor view when no sourcetypes are being monitored — points users at Discovery and Catalog.
- Pre-populated `monitored_sourcetypes.csv` with a small set of common defaults so the dashboard isn't blank on first install.
- Mobile responsive media queries in `heartbeat.css` (stacking columns under 768px).
- `prefers-reduced-motion` support — pulse and slide animations now respect user preference.
- `aria-label` attributes on key SVG icons for screen-reader accessibility.
- Filter state persistence — Monitor view filters survive page reloads via `localStorage`.
- Audit view pagination — capped at 1000 rows with a date-range picker so the table stays responsive on long histories.
- KV-store accelerated indexes on `sourcetype` for faster lookups as the collection grows.

### Changed
- Hardened `escapeString()` to handle backslashes, newlines, and other edge cases that previously could break audit log composition.
- Audit view now defaults to a 7-day window with an inline date-range picker.

### Fixed
- Several CSS duplications collapsed (`.settings-section`).
- Pulse animation no longer runs for users with `prefers-reduced-motion: reduce`.

## [v1.1.0] - 2026-05-04

### Removed
- Freemium licensing system (license validator, tier manager, REST handler, tier_gate.js, dataday.conf, restmap.conf).
- Splunk-Cloud blockers: `default/web.conf`, `metadata/local.meta`, `static/appIcon.svg`.

### Added
- `LICENSE.txt`, `NOTICE`, `README.md`, `app.manifest` for Splunkbase compliance.
- `[id]` stanza in `app.conf` for modern semver compliance.
- DiscoveryCatalog feature: visual catalog of known critical sourcetypes (security, identity, network, cloud).

### Changed
- `version` 1.0.0 → 1.1.0, `build` 32 → 34.
- AppInspect now passes with 0 failures, 0 errors against `cloud` + `splunk_appinspect` + `private_app` + `private_victoria` + `private_classic` + `packaging_standards` + `future` + `migration_victoria` tags.

## [v1.0.0] - prior

Initial development releases (built up to build 32 on `splunk-apps-dev`). See git history before commit `1d794ff` for details.
