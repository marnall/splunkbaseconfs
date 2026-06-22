# Changelog

All notable changes to the Innovators Toolkit are documented here.

## [2.3.0] - 2026-06-10

### Fixed (critical — Splunk 10)
- **Design Studio saves failed on Splunk 10** with `Argument "output_mode" is not supported by this handler`. Splunk 10's `data/ui/views` write handler rejects the `output_mode` parameter that older versions ignored, breaking Create New, Update Existing, version restore (both paths), and Apply-to-Dashboard. All six write calls now POST without `output_mode` (their handlers never read the response body). Caught and verified by live Playwright E2E against Splunk 10.2.3 — the build→save→render round trip now passes end-to-end, including update-existing with version-history backup.

### Added
- **Instant Makeover** — in the Design Studio's "Import from Splunk" dialog, point at any existing Classic dashboard, pick a theme, click ⚡ Makeover: a themed COPY named `<dashboard>_studio` is created (with Spotlight Tour, panel zoom, dark/light toggle, and a curated animated background matched to the theme — CSS-only, Cloud-safe). The transform only adds `stylesheet`/`script` attributes to the root element — every panel and search is byte-identical, and the original dashboard is never modified. Duplicate names are reported cleanly.
- **Spotlight Tour (TV Mode)** — new interactive control (`toggles/spotlight-tour.js`, 79th component). One click turns any dashboard into an auto-cycling cinematic tour: each panel smoothly zooms into focus while the rest dim, with a per-step progress rail and a status HUD. Space pauses, ←/→ skip, Esc exits. `data-sit-tour-autostart` starts touring on load (unattended TV walls); `data-sit-tour-interval="10"` sets seconds per panel. Honors `prefers-reduced-motion` (no zoom, instant focus), namespaced teardown, idempotent header injection. Available in the Design Studio controls list and the Component Catalog.

## [2.2.0] - 2026-06-09

The first release verified end-to-end against a live Splunk 10.2 instance (fresh trial-license container, Playwright E2E: login, all 21 views, Design Studio build→save→render round trip, optimizer diff). Four parallel adversarial audits (Design Studio, Optimizer, widget layer, XML/packaging) drove the fixes below. Optimizer harness expanded 33 → 62 assertions, all green.

### Added
- **Design Studio: autosave drafts.** In-progress designs are saved to `localStorage` (`sit_ds_draft`, debounced 2s). Reopening the studio after a crash/refresh offers "Unsaved draft from N minutes ago — Restore / Discard". Cleared on successful save; corrupted drafts are silently discarded.
- **Design Studio: unsaved-changes guard.** Navigating away with unsaved panels now warns (standard browser prompt). Cleared on save.
- **Design Studio: keyboard shortcuts.** Ctrl/Cmd+S opens the Save dialog; Delete/Backspace removes the selected panel (undoable). Shortcuts ignore focused inputs.
- **Design Studio: dashboard-ID preview + validation.** The Save dialog live-previews the final dashboard ID ("Will be saved as: …") and refuses IDs that Splunk would reject (leading digit, all-underscores from a non-ASCII title) with a clear message instead of a raw server error.
- **Optimizer: SPL Health lint.** Every analysis now includes advisory per-search checks: `index=*` / missing index filter, leading wildcards, `join`, `transaction`, mid-pipeline `table`, real-time searches. Suggestions only — never applied automatically.

### Fixed (correctness — Design Studio)
- **Root-level base searches and `<init>` blocks survive the import→save round trip.** Previously a dashboard using the standard global base-search pattern saved with its panels pointing at a base that no longer existed (P0 data corruption). Both are now captured verbatim, re-emitted in schema order, restored by undo/redo, and reset on clear.
- **Undo is exact.** One Ctrl+Z now steps back exactly one operation and redo reaches the newest state (was off-by-one: one undo jumped two operations and the latest state was unreachable). Panel moves snapshot consistently with all other operations.
- **sanitizeHtml SVG/MATH ban actually works.** Foreign-namespace elements report lowercase tag names, so the ban never matched (`<svg>`-based XSS vectors survived). Tag check is now case-normalized and animation attributes (`values`/`from`/`to`) carrying `javascript:` are stripped.
- Save/import dialogs no longer dead-end on AJAX failures (app/dashboard lists show an error + retry hint instead of "Loading…" forever).
- Hide-by-value: no longer permanently hides search-less panels (`depends` token was emitted but never set); condition values are SPL-escaped (quotes, `%`, `_`) so `a"b` can't generate malformed SPL.
- Editing an imported base-search panel now warns at save time that those edits are kept verbatim (previously silently dropped).
- Config-popover edits (title/SPL/drilldown) are undoable; Update Existing guards double-clicks and empty selections; rapid preview toggling can no longer load widgets into a torn-down preview (timer tracked + cleared); malformed XML imports report "XML syntax error: …" instead of the misleading "No <dashboard> tag found"; custom `cssClass` from Advanced config is actually emitted; widget panel DOM ids are collision-free (two same-type widgets both initialize); version history is capped per dashboard (5) + globally (40) so updating one dashboard can't evict every other dashboard's backups; preview shows a toast when widgets fail to load.

### Fixed (correctness — Optimizer)
- **Dashboards already using base searches are left intact.** Previously `<search base=…>` post-process tails were treated as full searches: the rewrite overwrote their `base` attribute (severing the original chain) and injected a broken leading-pipe base (P0 corruption). Pre-chained and leading-pipe (`| tstats`) searches are now excluded from grouping and rewriting.
- **Studio inputs can no longer dangle.** Dedup repoints `inputs[*].dataSources` (e.g. dynamic dropdowns) alongside visualizations before deleting duplicate sources (P0).
- **SPL comment blocks tokenize correctly.** A pipe inside a ``` comment no longer splits the stage (which shipped an unterminated comment in the base and resurrected commented-out SPL in the residual); unterminated comments mark the query unparseable (skipped).
- `<init><set token>` declarations are recognized as dashboard-global (an invalid CSS selector previously aborted the whole token scan, so init-token dashboards got zero opportunities).
- Identical duplicate panels emit `<search base=…/>` with no `<query>` element (an empty `<query/>` errors on several Splunk versions).
- Studio dedup keys on the full option set: sources differing in `refresh`/`refreshType`/other options are no longer merged (merging silently dropped the survivor's auto-refresh).
- Re-aggregation residuals (`stats`, `timechart`, `head`, `dedup`, `rex`, …) are now scannable by GUARD 1 instead of auto-skipping the group — common 2-stage dashboards optimize again.
- The diff compares against the text that was analyzed (editing the input between Analyze and Generate no longer diffs unrelated text); the copy button says "Copy JSON" for Studio output; the expectations note documents the Studio-dedup asymmetry and out-of-scope cases (pre-existing bases, saved-search panels).

### Fixed (correctness — widgets/components)
- **`sit-toolkit.js` no longer clobbers `window.SIT`** — it previously replaced the whole namespace, wiping the preview-teardown registry and `parseDisplayNumber` depending on load order (silently re-enabling the preview leaks the teardown system fixed).
- `SIT.parseDisplayNumber`: scientific notation ("1.2e5") and bare leading decimals (".5", "-.75") parse correctly; all documented locale cases re-verified (17/17).
- Splunk 10.2 compatibility: alert-toast and confetti single-value readers got the SVG fallback (`.result-number` no longer exists on 10.2 — triggers silently never fired).
- Component registry URL matching works against real (cache-busted) Splunk static URLs; was matching nothing.
- Teardown integrity: unnamespaced document handlers in drag-resize and panel-collapse no longer stack per preview cycle; header-injected buttons (dark/light, reset-sizes, collapse-all) are removed on teardown and never duplicated; dark-light-mode's init timer can't re-apply a theme class after teardown; countdown timers detect panel re-renders and rebuild instead of updating detached DOM forever.
- Panel-collapse: expanded panels no longer clip content that loads after init (max-height released after transition); init retries on slow dashboards; full keyboard/ARIA support (tabindex, role=button, aria-expanded, Enter/Space).
- Toast hover-pause resumes with the actual remaining time (was a hardcoded 30% guess); gauge label can't duplicate the value; KPI counter keeps trailing-zero precision during animation; modal focus trap includes links and skips disabled/hidden elements.
- Reduced-motion: core spinners/progress stripes, KPI glass shimmer, and the sparkline SMIL pulse now honor `prefers-reduced-motion`.

### Changed
- README/app.conf/manifest accuracy: data-* configuration documented correctly (attributes go inside an `<html>` panel, not on the `<dashboard>` root); Cloud Mode text reflects direct saving with Download-XML fallback; component counts phrased consistently ("78 including…"); `_internal` role requirement noted for demos; the optional `toolkit-loader.js` master loader is documented.
- Dev: Playwright live-E2E suite (`tests/`) and showcase recording added; `tools/package.sh` excludes them from the Splunkbase tarball.

## [2.1.16] - 2026-05-31

### Removed
- Deleted the dead `saveCloudFlow`/`showCloudSavedSuccess`/`cloudFallbackFlow` cluster (~125 lines) from `sit-design-studio.js`. It was superseded in v2.1.4 (the Cloud Save button opens the app+name Save modal) and had been inert/unreferenced since; removing it eliminates a confusing dead code path and the last reference to the dead `/dashboards/_new` route.

## [2.1.15] - 2026-05-31

Closes the findings from the section re-run (completing the 60-round coverage). AppInspect cloud-tags 0/0/0; optimizer harness 33/33.

### Fixed (correctness)
- **Imported HTML panels keep their markup.** Import captured panel content via `textContent` (tag-stripped), so editing an imported HTML panel silently destroyed its markup on save — now captures `innerHTML`.
- **Advanced panel-config controls work again.** The config popover was appended to `<body>` while its handlers are delegated on the app container, so the drilldown / hide-by-value / depends-rejects / cssClass fields were non-functional. The popover is now appended inside the container.
- **Optimizer — `IN` operator.** GUARD 1's field-reference extractor missed `field IN (...)`, so a residual filtering on a field the transforming base drops could over-promote into a broken base search. `IN` is now detected.
- **Optimizer — Dashboard Studio reference integrity.** Dedup now keys on data-source type + chain `extend` (not just query+time) and repoints every visualization dataSource slot (not just `primary`) plus chain `extend` before deleting, so it can no longer dangle a chain/secondary reference. (Also corrected the optimizer's in-UI note to list the real transforming-command set.)
- **Undo integrity / preview leak.** Moving a panel left/right is now undoable (`pushHistory`); and a preview-teardown race (an async-loaded effect module registering its cleanup after teardown already ran) now runs that cleanup immediately instead of orphaning a timer/canvas.

### Accessibility
- `prefers-reduced-motion` guards added to the remaining widget stylesheets (news-ticker, status-traffic-lights, kpi-neon-glow, loading-skeleton) and the confetti widget no longer animates for reduced-motion users.
- `real-time-clock` now clears its staggered init timeouts on teardown.

## [2.1.14] - 2026-05-31

Fixes from section-focused evaluation rounds. AppInspect cloud-tags 0/0/0; optimizer harness 33/33.

### Fixed (memory / leaks)
- **`topology-renderer`** window resize handler is now namespaced + removed on teardown (was stacking each preview cycle), and its bootstrap `setTimeout`s are tracked/cleared.
- **`particle-network`** resize handler is now namespaced + removed on teardown (was leaking per cycle).

### Fixed (correctness)
- **Gauges/ring update on refresh.** liquid-fill, speedometer, and circular-progress rendered once and went stale when the panel's single-value updated on auto-refresh — they now re-render on value change (debounced, change-guarded). Liquid-fill no longer stamps a spurious "%" on non-percentage KPIs.
- **`org-chart`** node selection no longer clears every org-chart on the page (scoped to the instance).
- **Demo correctness**: removed inert filter dropdowns from the Security Ops (Severity, Data Source) and DevOps Pipeline (Environment) demos (they were never referenced by any query); fixed the Threat Hunter "Anomaly Score" KPI (a `streamstats`-over-one-row expression that always blew past its thresholds) to a meaningful bounded value.

### Accessibility
- The four JS canvas/video backgrounds (particle-network, matrix-data-rain, starfield-parallax, video-ambient-loop) now honor `prefers-reduced-motion` (render a single static frame / don't autoplay) — the earlier reduced-motion work was CSS-only.
- Fixed sub-AA contrast on muted text: corporate-modern under-label (2.54→4.83:1) and dark-mode-pro under-label/table-header (3.45→6.5:1).
- Cert-prep exercises: the gentlest hint (step 1) is now reachable (was skipped on the first hint click).

### Removed
- A non-functional "Print Dashboard" `::after` pseudo-button in the print stylesheet (a CSS pseudo-element can't trigger `window.print()`, and it collided with the panel-polish control bar).

## [2.1.13] - 2026-05-31

Closes the remaining backlog surfaced by the deep-dive rounds. AppInspect cloud-tags 0/0/0; optimizer harness 33/33.

### Fixed (Design Studio import/round-trip)
- **Base / post-process searches preserved.** Imported panels that use a base search (`<search base="…">` + a root `<search id="…">`) are now detected on import and kept verbatim when edited, and a valid `<search base="…">` is emitted on the regeneration path — previously the base reference was dropped and the post-process fragment could be emitted as an invalid top-level query.
- **Correct element scoping in the parser.** Time bounds now read from the panel's own viz `<search>` (not the first descendant), dashboard `<label>`/`<description>` from direct children only, and panel title from the panel's direct `<title>` (not a nested viz/drilldown title).
- **Preview-view cleanup.** Orphaned `_sit_preview_*` views are now removed on tab close (synchronous DELETE on `pagehide`/`beforeunload` with the CSRF header), a real stale-view reaper runs at load (the old one could never fire), and both cleanup DELETEs now log failures.

### Fixed (Optimizer safety)
- **Residual-field-subset guard.** The Optimizer no longer promotes a base search when a panel's residual tail references a field the transforming base would drop (which would break that panel) — it skips the group instead. Default-to-skip on any uncertainty.
- **Token-position guard.** Prefixes are only shared into a base search when their `$token$`s are dashboard-global (fieldset/init), not panel-local — preventing incorrect base-sharing of searches that use the same token name in different roles.

### Fixed (widgets / touch)
- Countdown timer renders 1000+ day counts (was truncated at 3 digits); heatmap handles negative values and quoted-number inline data; `background-helper` recolors generic Splunk 10.2/10.3 SVG single-values.
- Larger touch hit-areas for the resize handle (coarse pointers) and an explicit zoom button on touch (instead of whole-panel tap that collided with scroll/drilldown).

## [2.1.12] - 2026-05-31

Fixes from deep-dive evaluation rounds 31–40 (light-theme/SVG, i18n, touch, exercises, parser, version matrix, widgets, optimizer, operability). AppInspect cloud-tags remain 0/0/0; optimizer harness 33/33.

### Fixed (correctness)
- **Optimizer base-search safety regression.** The v2.1.8 transforming-command guard wrongly listed `eventstats`, `streamstats`, `table`, `dedup`, `transaction`, and `makeresults` as transforming — they are not, so a base search ending in them is event-bound and would silently truncate dependent `stats`/`chart`. The list is now restricted to genuinely transforming commands (`stats`/`tstats`/`chart`/`timechart`/`top`/`rare`/`contingency` + `si*` variants).
- **Editing an imported `<event>`/`<list>`/custom-viz panel no longer wipes it to "Empty Panel."** Unknown imported panel types now keep their original XML verbatim even when edited (a lost title-rename beats losing the whole panel).
- **Splunk 10.2/10.3 single-value coloring.** Themes set `color` on the legacy single-value element but not `fill` on the new inline-SVG `<text>`, so KPI numbers rendered in Splunk's default fill — invisible on dark themes. Added `fill` rules across all 12 themes, the panel-polish base CSS, and light mode.
- **Light themes are readable on first paint.** newspaper-editorial / executive-boardroom / corporate-modern now define their own readable title/value colors in CSS instead of relying solely on a 500 ms JS class (which caused white-on-light flashes and stale-localStorage white-on-white).
- **Locale-aware number parsing.** Eight widgets parsed displayed single-values assuming en-US decimals (so `1.234,56` in de-DE collapsed ~1000×). Added a shared `SIT.parseDisplayNumber` (`lib/sit-parse-number.js`) that detects the decimal separator, and applied it to the gauges, KPI counters, sparkline, confetti, and number-morph. Output reformatting now uses the user locale.
- **Speedometer gauge**: no longer renders a NaN needle when min==max, and now honors an explicit `data-max="0"`.
- **Cert-prep exercises**: Exercise 3's starter taught the wrong `SITModal.confirm()` signature (fixed to the 4-arg form); Exercise 1's grader and starter are now consistent.

### Changed
- **Touch support** added to the drag-resize, right-click context-menu, and panel-zoom toggles (Pointer Events + `setPointerCapture`, long-press for the context menu, larger touch targets) — they were mouse-only.
- **Operability**: the runtime version banner now reports the real version/build (was hardcoded to 2.0.0), and `SIT.debug`/`SIT.log` are defined app-wide in the loader so debug logging works on any dashboard, not only in Design Studio.

## [2.1.11] - 2026-05-31

Fixes from verification/deep-correctness evaluation rounds 21–30 (regression re-audit 9/10, upgrade-safety 9/10, release sign-off GO). AppInspect cloud-tags remain 0/0/0.

### Fixed
- **Honesty — the experimental JSON export no longer claims to be Dashboard Studio.** The Design Studio export tab previously labeled "Dashboard Studio JSON" produced output that does not import into real Dashboard Studio, contradicting the app's Classic-only positioning. It is now labeled "JSON (experimental — not a Dashboard Studio import)" with a caption stating it's a best-effort starting point, not guaranteed to import. The Classic Simple XML export (the supported path) is unchanged.
- **Component Reference code examples now work.** The documented `require()` module IDs were wrong (`components/sit-button` etc.); corrected to the real `app/splunk-innovators-toolkit/components/…` paths so copy-pasted examples load.
- **Privacy control now clears the real collapse keys.** The preferences "clear" list referenced the retired non-namespaced `sit-collapsed-panels`; it now enumerates and removes every per-dashboard `sit-collapsed-panels-<path>` key.

### Performance
- **Background animations are now well-behaved.** particle-network, matrix-data-rain, starfield-parallax, and background-helper previously ran two full-document `querySelectorAll` scans on *every* DOM mutation via an unthrottled `document.body` subtree observer; the callbacks now early-return unless element nodes were added and debounce their work. Canvas/animation loops now pause drawing while the tab is hidden (`visibilitychange`), so hidden dashboards stop consuming CPU.

### Docs
- Corrected stale in-app counts in Getting Started (13 backgrounds, 12 controls); reworded the README Security Operations demo to the honest `index=_internal` framing; replaced the over-broad "Not compatible with Dashboard Studio" line with an accurate statement (themes/controls/Design Studio target Classic; the Optimizer can also analyze Studio JSON); manifest release date updated.

## [2.1.10] - 2026-05-31

Fixes from 10 adversarial/specialist evaluation rounds (red-team import, Cloud platform security, pentester, privacy/GDPR, i18n, mobile, Victoria migration, core-API, maintainer, QA). AppInspect cloud-tags remain 0/0/0.

### Security
- **Hardened the HTML sanitizer.** Replaced the regex-based `sanitizeHtml()` (defeatable via slash-delimited attributes / mutation-XSS) with a **DOMParser-based** sanitizer that parses without executing, removes dangerous elements (`script`/`iframe`/`object`/`embed`/`style`/`link`/`meta`/`base`/`form`/`svg`/`math`), strips all `on*` handlers, and neutralizes `javascript:`/`data:`/`vbscript:` URLs (incl. `style` `expression()`/`url()`).
- **Sanitize on the save path, not just preview.** Imported HTML-panel content is now sanitized when generating the saved dashboard XML (the regex version only ran in the editor preview). (Verbatim unedited-panel round-trips remain byte-faithful and rely on Splunk's server-side HTML-panel sanitizer.)

### Fixed
- **Multi-page tab navigation was never loaded.** `tab-navigation.js` was appended to the script list *after* the `script="…"` attribute had already been assembled, so multi-page dashboards shipped without their tab-nav script. Moved the include before assembly.
- **Non-ASCII dashboard titles** no longer produce an empty export filename or a colliding dashboard id — the slug now falls back to a default when a title has no `[a-z0-9]` characters (e.g. all-CJK titles).

### Changed
- **Removed ~90 KB of dead code from the package**: two byte-identical unused copies of SortableJS (`lib/Sortable.min.js`, `lib/sortablejs-1.15.6.js`) — only `vendor/sortablejs.js` is loaded. Also removed a stray dev file from the repo.
- **PRIVACY.txt corrected** to list the real localStorage keys (`sit_ds_*`, `sit-*` toggle keys, per-dashboard suffixing), added an indefinite-retention note for version-history/custom-templates, and documented exactly what the in-app "clear" controls do and don't remove.

## [2.1.9] - 2026-05-30

Completes the persona-round backlog (accessibility, cross-version, motion, leak hygiene). AppInspect cloud-tags remain 0/0/0.

### Accessibility
- **Design Studio's six dialogs are now accessible.** showEffectInfo, clear-canvas confirm, Save-template, Version-history, Import, Save/Export modals now route through a shared `a11yDialog()` helper: `role="dialog"`/`aria-modal`, focus moved into the dialog on open, **Escape to close**, Tab focus-trap (guarded so it never traps when there are no focusables), and focus restored to the trigger on close.
- **`prefers-reduced-motion` honored.** 17 theme/background stylesheets now disable their infinite animations (CRT flicker, scanlines, gradient shifts, sweeps, rain, pulses) for users who request reduced motion (WCAG 2.3.3).

### Fixed (cross-version)
- **Splunk 10.2 single-value widgets work again.** kpi-animated-counter, kpi-circular-progress, kpi-3d-flip, and sparkline-inline read only the legacy `.result-number`; they now also read the Splunk 10.2 SVG `<text>` single-value (dual-path, same as the gauges) so they no longer silently no-op on 10.2. Splunk 9 path preserved.

### Fixed (data integrity)
- **Editing an imported recognized panel no longer drops its styling/drilldowns.** When a dirty imported panel is regenerated, its original non-model `<option>`, `<fields>`, and drilldown nodes are now preserved (merged back from the stored raw XML). Imported `<fieldset>` form inputs are emitted verbatim when the user hasn't changed the input set. (Verified with a jsdom round-trip test; flagged for live re-verification.)

### Fixed (memory)
- **`beforeunload` handlers no longer stack** across preview cycles — every module's registration is now namespaced (`beforeunload.sit<Module>`) so the preview re-loader swaps the handler instead of accumulating one per cycle.

### Changed
- **QR widget is honest now.** It no longer claims "Scan to Open Dashboard / point your phone camera" (the rendered code isn't a spec-compliant scannable QR). The modal now presents the dashboard URL as the primary element with a working **Copy URL** button; the code remains as decoration.

## [2.1.8] - 2026-05-30

Fixes from 10 brutally-honest Splunk-expert-persona evaluation rounds (Cloud admin, on-prem admin, SOC analyst, Splunkbase reviewer, Splunk Trust SME, dashboard dev, SRE, AppSec, accessibility, first-time user). AppInspect cloud-tags: **0 failures / 0 errors / 0 manual checks**.

### Security
- **Second DOM-XSS fixed.** An imported dashboard's HTML-panel content was rendered raw into the Design Studio canvas. It now passes through a `sanitizeHtml()` strip (removes `<script>`/`<iframe>`/`<style>`/etc., inline `on*` handlers, and `javascript:`/`data:` URLs) before preview.

### Fixed (honesty / correctness)
- **SOC demo titles now match the data.** After the `_audit`→`_internal` rewrite the panel titles still said "Auth Failures"/"Total Alerts"/"Authentication Activity" — misleading in a real SOC. Retitled to what the queries actually show (e.g. "UI Access Errors (HTTP 4xx)", "Scheduled Searches (success)", "UI Access Activity (200 vs 4xx)") and the dashboard description now states it's a demo on `_internal`, not Enterprise Security/auth data.
- **Removed an endorsement over-claim** — the signature theme no longer calls itself the "official Splunk Innovators Network branded theme".
- **Dashboard Optimizer base-search safety.** It no longer promotes a *non-transforming* shared prefix into a base search (which in Splunk caps post-process tails at the base event limit and silently truncates dependent `stats`/`chart`). Base searches are now only created when the shared prefix ends in a transforming command.

### Fixed (performance / memory)
- **`topology-renderer`**: its per-preview SplunkJS `SearchManager` is now cancelled/destroyed/revoked on teardown (was leaking search jobs + indexer concurrency every preview cycle), and creation is de-duplicated.
- **`confetti-celebration`**: per-panel poll intervals, timeouts, rAF, and the resize listener are now all tracked and cleared on teardown.
- **Namespaced `beforeunload`** in these modules so the preview re-loader swaps the handler in place instead of stacking duplicates each cycle.

### Changed
- **Auto-refresh is now opt-in.** It no longer auto-starts a full-dashboard re-run loop on load; it starts only on explicit user action or a `data-sit-refresh-interval` attribute, defaults to ≥15 min, and pauses while the tab is hidden.

### Accessibility
- Design Studio toasts and the alert-toast widget now expose `role`/`aria-live` so save/import/error feedback is announced to screen readers.

## [2.1.7] - 2026-05-30

Fixes from brutally-honest evaluation rounds 6–10 (security, performance, Victoria, cross-version, production-readiness).

### Security
- **Fixed DOM-XSS in Design Studio.** Importing or remixing a dashboard parsed its root `stylesheet`/`script` attributes into the theme/background fields unsanitized, then rendered them unescaped in the Settings summary and the saved-template palette. Theme/background names are now sanitized to safe characters on parse and escaped at every display sink.

### Fixed (Splunk Cloud)
- **`demo_newspaper_audit.xml` is now fully `index=_audit`-free.** The remaining 6 gated `_audit` searches (the hybrid "requires _audit access" panels) were converted to `index=_internal` (`splunkd_ui_access` / scheduler) equivalents so every panel returns data under standard Cloud roles, and the obsolete warning notes were removed. No executed `<query>` in any view uses `_audit` now.

### Fixed (memory/performance — teardown completion)
- **10 modules leaked `MutationObserver`s** (and some timers) that were never disconnected and never registered a preview teardown — so the v2.1.4 `require.undef` preview re-run actually spawned a fresh undisconnected observer each cycle. Now fixed in: `chart-annotations` (also fixed a self-feeding per-panel observer that leaked on **production** dashboards, not just preview), `org-chart-interactive`, `kanban-board`, `timeline-gantt`, `terminal-log-viewer`, `qr-code-generator`, `weather-widget`, `team-status-board`, `sparkline-inline`, `kpi-circular-progress`. Each now disconnects its observer(s), clears its timers, and registers a teardown via `window.SIT.preview` + `beforeunload`.

### Changed
- Corrected the animated-background count in the app.conf description and README (13, not 14).

## [2.1.6] - 2026-05-30

### Fixed
- **Timeline/Gantt widget** no longer produces `NaN` bar geometry for single-instant or empty data — a zero time-range now defaults to a 1-hour window.
- **Support email** corrected in README.md / README.txt (`datadaytech.com`, matching the manifest and PRIVACY notice).

### Known issues (tracked, not yet fixed)
- The QR-code widget renders a stylized code that is **not reliably scannable** (no spec-compliant encoder/error-correction). The URL is shown as text in the modal. A real QR encoder (or removing the "scan" affordance) is pending.
- Theme/background animations don't honor `prefers-reduced-motion`; a few muted-text colors fall under WCAG AA contrast — accessibility hardening pending.

## [2.1.5] - 2026-05-30

Critical fixes surfaced by a brutally-honest multi-agent review of the v2.1.4 changes — including a regression v2.1.4 itself introduced.

### Fixed
- **CRITICAL — Cloud "Save to Splunk" was a no-op (v2.1.4 regression).** v2.1.4 rerouted the cloud Save button to `showSaveModal()`, but that function had an early `if (cloudMode) return;` guard, so clicking Save in Cloud mode did nothing. Removed the guard — the modal's Create-New/Update flows already POST with the CSRF header, confirm the created entry, and fall back to Download-XML on a 403, so they work correctly in Cloud mode.
- **CRITICAL — Save/Export/Preview crashed on any hide-by-value panel.** `generateSimpleXML` referenced an undefined variable `ri` in the hide-by-value branch; under `'use strict'` this threw a `ReferenceError`, breaking the entire save/export/preview/version-backup pipeline whenever a panel used conditional visibility. Now uses the correct in-scope `pageIdx`/`rowIdx` (also makes the generated token unique across pages).
- **HIGH — Multi-page dashboards dropped widget JS on inactive pages.** Widget JS references were collected from the active page only, so a widget placed on another page was emitted without its `script=` include and never initialized. Now scans all pages.

### Added
- **Optimizer test harness committed to `tools/optimizer-harness/`** (dev-only, excluded from the package). Runs the real `window.SIT.optimizer` logic headlessly (jsdom) — 33 assertions across 13 dashboards (grouping, clone-reuse, time/token boundaries, real-time skip, malformed-SPL safety, Simple XML ordering, Studio dedup, valid re-parse). `cd tools/optimizer-harness && npm install && npm test`.

## [2.1.4] - 2026-05-30

Live-testing + adversarial-review pass. Fixes user-reported bugs found by exercising the app in a real Splunk container, plus regressions surfaced by reviewing the v2.1.3 fixes themselves.

### Fixed
- **Preview teardown lost after the first cycle (regression).** The Design Studio preview loaded each effect module via RequireJS by a fixed name, so the module body — which registers its `window.SIT.preview` cleanup — only ran on the *first* preview. On the 2nd+ preview, timers/observers/handlers leaked. `loadPreviewWidgets` now `require.undef`s each module before re-requiring, so every effect re-registers its teardown each cycle.
- **Cert-prep exercises produced broken output.** Exercise 1's `toast.show({...})` rendered an "undefined" toast (the API was positional only) and Exercise 2's task said `.open()` (no such method). `SITToast.show` now accepts an options object, `SITModal` gained an `open()` alias, and the Exercise 2 instructions say `.show()`.
- **Design Studio "Save" on Splunk Cloud opened a dead `/dashboards/_new` tab.** Cloud Save now opens the Save modal so you pick the target app + dashboard name and save via REST (CSRF-protected); a 403 offers a Download-XML fallback. The dead-route flow was removed.
- **Scroll-reveal could leave panels permanently invisible** (opacity:0) if the IntersectionObserver never fired — e.g. when another toggle re-parents a panel, in a non-scrolling container, or when a co-loaded script errors. Added a fail-safe that force-reveals any still-hidden panel after a short grace period (panels can never be left hidden).
- **Demo license-usage panels returned blank.** `demo_cyberpunk_noc` and `demo_internal_metrics` used `sourcetype=splunkd group=license_usage` (no such data → empty); `demo_glass_pipeline`/`demo_internal_metrics` referenced a non-existent `ev` field. Now use `source=*license_usage.log type=Usage | stats sum(b)`.
- **Stale demo count** in `getting_started` (said 9, now 13).

### Added
- **Dashboard Optimizer: line-numbered diff** of the optimized output with green (added) / red (removed) highlighting, replacing the plain before/after panes (with a side-by-side fallback for very large dashboards).
- **Optimizer: an expandable “What it optimizes & what to expect” note** documenting grouping rules, skipped cases (real-time, unparseable SPL), the client-side/no-size-limit behavior, and a review reminder.

### Changed
- **Optimizer: long SPL now wraps** in the Analysis panel (base search + per-panel residual code blocks) instead of overflowing the page.
- **Version History UX clarified.** Both the inline panel and the modal now explain that a version is an automatic backup of a dashboard’s *previous* content captured before an **Update Existing Dashboard** overwrite, that brand-new dashboards have no version until first overwrite, and that history is per-browser, shared across dashboards, last 20 kept.

### Verified
- Optimizer logic validated headlessly (jsdom) against 13 dashboards / 33 assertions — grouping, clone-reuse, time/token boundaries, real-time skip, malformed-SPL safety, Simple XML ordering, Studio dedup, and valid re-parse of every rewrite.
- App, demos, Design Studio (load → template → preview → teardown), and Optimizer exercised live in a Splunk 10.2.x container with zero console errors.

## [2.1.3] - 2026-05-30

Second deep-audit pass (multi-agent). Fixes Splunk Cloud Victoria/Classic correctness issues plus a wide set of memory/animation leaks found by an exhaustive bug hunt across every static module.

### Fixed (Splunk Cloud Victoria + Classic)
- **SPL — `index=_audit` removed from all demo dashboards.** `_audit` is restricted for standard Cloud roles (especially Victoria), so 8 demos rendered empty. Under a hybrid policy: panels with a clean `_internal` equivalent were rewritten (failed logins → `sourcetype=splunkd_ui_access status>=400`; search/scheduler activity → `sourcetype=scheduler`; `total_run_time` → `run_time`); the few audit-only panels in `demo_newspaper_audit` were kept but each now carries a visible "⚠ Requires _audit index access (admin / sc_admin on Splunk Cloud)" note. Removed the dead `notable`/`_audit` input choices from `demo_security_ops` (token was never referenced).
- **Cloud Save — `saveCloudFlow`** now POSTs with owner `nobody` (not the invalid `-`), includes `output_mode=json`, and confirms the created entry before reporting success (no more false-positive "Saved" on a soft error).
- **Create New Dashboard POST** now sends the `X-Splunk-Form-Key` CSRF header (Victoria 403'd without it).
- **Update Existing** now aborts the overwrite if the pre-overwrite version-history backup fails, instead of silently overwriting.

### Fixed (data integrity)
- **Lossless round-trip now covers ALL panel types.** Previously only *unknown* panels round-tripped verbatim; *recognized* panels (chart/table/single/map) were regenerated from a partial model that hardcoded `-24h@h`/`now` and dropped `<option>`, drilldowns, `<fields>`, and refresh settings — silently corrupting imported production dashboards on save. Import now stores each panel's raw XML and real `earliest`/`latest`, tracks a per-panel dirty flag, and emits unedited panels verbatim; only panels the user actually edits are regenerated.

### Fixed (Dashboard Optimizer)
- `rewriteClassic` no longer orphans panels when two share an identical query + time range (each base-search candidate is now consumed one-to-one), no longer injects the base `<search>` before `<label>` (Simple XML ordering), HTML-escapes parser-error text, and skips (rather than corrupts) SPL it cannot safely tokenize (`\|`, unbalanced brackets/quotes).

### Fixed (memory & animation leaks — preview teardown)
- **`requestAnimationFrame` / interval / observer leaks** fixed across widgets, visualizations, backgrounds, and animations. Each now registers a teardown via `window.SIT.preview.register` + `beforeunload`: gauge-liquid-fill (perpetual rAF), countdown-timer, kpi-3d-flip (self-triggering observer → reflow churn), gauge-speedometer, kpi-animated-counter, number-morph, scroll-reveal, globe-3d-rotate, animated-svg-network-map, heatmap-calendar, particle-network, video-ambient-loop, matrix-data-rain, starfield-parallax, button-ripple-effect, typewriter-text, background-helper.
- **5 interactive-control toggles** (dark-light-mode, fullscreen-mode, auto-refresh-countdown, tab-navigation, filter-chips-tags) now actually unbind their `$(document)` handlers on teardown (namespaced) and remove persistent `<body>` classes (`sit-light-mode`, `sit-fullscreen-active`).
- **`alert-toast-notifications`** clears its poll interval and disconnects its observer on teardown.

### Fixed (components & loader)
- **`sit-modal`**: backdrop click now closes (was dead — delegated selector matched descendants only); reopened modals are interactive again (`close()` uses `detach()` + `show()` re-delegates instead of `.remove()` stripping handlers); added focus trap, focus restoration, and `role="dialog"`/`aria-modal`/`aria-labelledby`.
- **`toolkit-loader`**: `SIT.getToken`/`setToken` now `require('splunkjs/mvc')` (was a `ReferenceError`) with guards.
- **`sit-checkbox`** group no longer accumulates instances on re-render; **`sit-table`**/**`sit-toast`** escape empty-message text and clear auto-dismiss timers.

### Changed
- **app.manifest**: `privacyPolicy.uri` set to `null` (the GitHub raw URL 404'd during vetting); the bundled `PRIVACY.txt` text reference remains. Author/contact email normalized to `steve@datadaytech.com`.
- **Navigation**: added the four orphaned demos (Threat Hunter Tactical, FinOps Executive Brief, DevOps Pipeline Pulse, Internal Service Topology) to the nav.
- **Packaging**: removed the developer test harness `widget_test.xml`; `tools/` and `AUDIT/` are now excluded from the package build; `metadata/local.meta` untracked from git.

## [2.1.2] - 2026-05-26

### Fixed (Splunk Cloud Victoria + Classic)
- **Security** — replaced `new Function()` in `sit-exercises.js` with a sandboxed constrained evaluator. The cert-prep exercises run user-typed `toast.*` and `SITModal.*` calls through a pattern-matching parser, never through dynamic code execution. Required for stricter Splunk Cloud security policies.
- **SPL** — fixed two Cloud-restricted commands in demo dashboards:
  - `demo_security_ops.xml`: dropped `| tstats count where index=notable` (notable index isn't present without ES; tstats on `_audit` requires capability not granted to non-admin Cloud roles). Now uses plain `stats count`.
  - `demo_internal_metrics.xml`: replaced `| metadata type=sourcetypes` (blocked on Victoria) with equivalent `stats dc(sourcetype)`.
- **CSRF** — Cloud Save POST in Design Studio now sends `X-Splunk-Form-Key` header. Victoria 403s without it; previously the save silently fell through to the clipboard-fallback path.
- **Locale** — 30 hardcoded `/en-US/` URL paths replaced with a locale-aware `sitUrl()` helper. Non-EN locales and SSO setups that strip the locale segment no longer 404 on Cloud Save, Design Studio navigation, or Remix.
- **Preview teardown** — all 12 toggle modules (dark-light-mode, fullscreen-mode, auto-refresh-countdown, keyboard-shortcuts, panel-collapse-accordion, panel-zoom-focus, right-click-context-menu, sidebar-slide-panel, tab-navigation, drag-resize-panels, filter-chips-tags, user-preferences-persist) now register with `window.SIT.preview` and clean up their injected `<style>` tags, namespaced event listeners, and timers on preview close. Closes the v2.1.0 teardown work that originally landed only on backgrounds + widgets.
- **jQuery 3.5** — replaced deprecated `:first` pseudo-selector with `.first()` in 3 locations (terminal-log-viewer, filter-chips-tags, alert-toast-notifications).

### Changed
- **Packaging** — moved `bin/package.sh` to `tools/package.sh`. The empty `bin/` directory was triggering Splunk Cloud manual-review holds (Cloud reviewers gate on any `bin/` because of Python runtime concerns), even though our `package.sh` is a dev-only tarball builder that never runs inside Splunk.
- `console.log` calls in `sit-exercises.js` and `sit-toolkit.js` now gated behind `window.SIT.debug` (consistent with the rest of the codebase since v2.1.0).
- App manifest: declared `platformRequirements.splunk = ">=9.0"` and hosted privacy policy URI.
- App.conf: added `[supported_versions]` stanza pinning `splunk = 9.0+`.
- README: updated demo count from 9 to 13 (v2.1.0 added 4 demos that the README didn't reflect).

## [2.1.1] - 2026-05-08

### Fixed (Splunk Cloud compatibility)
- Replaced `| rest /services/data/indexes` in 4 demo dashboards (arctic_infra, glass_pipeline, internal_metrics, finops_executive) with Cloud-safe `index=_internal source=*license_usage.log type=Usage` aggregations — REST read commands against management endpoints are blocked on Splunk Cloud
- Replaced `| rest /services/server/info` in retro_terminal demo with a Cloud-safe uptime calculation derived from `_internal` Metrics events
- All 13 demo dashboards now run cleanly on both Splunk Enterprise and Splunk Cloud

## [2.1.0] - 2026-05-07

### Added
- **Dashboard Optimizer** — new nav entry. Loads Classic Simple XML or Dashboard Studio JSON, identifies panels with shared SPL prefixes, generates optimized version using `<search id="base_N">` + `<search base="base_N">` post-process pattern. Pure-JS conservative algorithm: respects time-range and token-signature boundaries; skips real-time searches.
- **Splunk Cloud one-click save** — Cloud Mode "Save to Splunk" button tries REST POST to user's namespace first; on failure auto-copies XML to clipboard and opens Source Editor in a new tab with paste-hint dialog
- 4 new demo dashboards: Internal Service Topology (ITSI Service Analyzer-style tree with animated data flow), Threat Hunter Tactical (cyberpunk SOC), DevOps Pipeline Pulse (DORA metrics), FinOps Executive Brief (license burn + cost attribution)
- Topology renderer widget (`appserver/static/widgets/topology-renderer.js`) — animated SVG bezier edges with data packets flowing child→parent, per-node mini sparklines, pulsing critical-node animations, scanning beam backdrop, live event stream ticker

### Fixed
- **Data-loss bug**: Design Studio import → save no longer drops `<event>`, `<list>`, `<viz>`, or other unrecognized panel types. Unknown panels are preserved as raw XML and emitted verbatim on save (lossless round-trip).
- Dark/light mode toggle: first click no longer a no-op for auto-detected light themes (executive, newspaper, glass, etc.) — fixed `currentMode` variable shadowing in `dark-light-mode.js`
- Catalog page: `sit-catalog.js` now retries bootstrap if the dashboard's `<html>` panel hasn't materialized when the script first runs
- Real-time clock widget: `setInterval` handle now tracked + cleared on teardown (memory leak fix)
- Preview-mode "screen cut off after close" bug — added `window.SIT.preview` teardown registry that strips injected `<style>` tags and prepended canvases on exit-preview; 5 background JS modules now register cleanup hooks

### Changed
- Removed 30-second auto-refresh option from effects panel — minimum interval now 1 minute (30s hammered the indexer for marginal UX value)
- `console.log` in design studio JS now routes through `window.SIT.log` (silent unless `window.SIT.debug = true`)

## [2.0.0] - 2026-04-16

### Renamed
- App renamed from "Splunk Innovators Toolkit" to **"Innovators Toolkit"** for Splunkbase naming compliance
- App ID remains `splunk-innovators-toolkit` (unchanged for backward compatibility)
- Community name unchanged: Splunk Innovators Network on LinkedIn



### Added
- Design Studio: visual dashboard builder with 4 tabs (Components, Effects, Colors, Settings)
- 4th tab "Colors" — theme, per-theme text color presets, background
- Splunk Cloud Mode toggle in top bar (enabled by default)
- Download XML primary action for Cloud users (no REST write required)
- Hide by Value — conditional panel visibility based on search results (equals, less than, greater than, contains, is empty)
- 9 production-ready demo dashboards (SOC, Cyberpunk NOC, Executive Report, Arctic Infra, Synthwave, Retro Terminal, Glass Pipeline, Newspaper Audit, Internal Metrics)
- 12 premium themes (Cyberpunk Neon, Dark Mode Pro, Executive Boardroom, Arctic Frost, Synthwave Sunset, Retro Terminal, Glass Dashboard, Gradient Luxury, Newspaper Editorial, Corporate Modern, SOC Command Center, Innovator Signature)
- 14 animated backgrounds (Matrix Data Rain, Particle Network, Aurora Borealis, Cyberpunk Grid Pulse, Radar Sweep, Starfield Parallax, Blueprint, Circuit Board, Dark Topography, Noise Grain, Mesh Gradient, Gradient Wave, Video Ambient Loop)
- 11 interactive controls (Dark/Light Toggle, Fullscreen, Panel Collapse, Panel Zoom, Auto-Refresh Countdown, Keyboard Shortcuts, Right-Click Menu, Drag Resize, Filter Chips, Sidebar Slide Panel, User Preferences)
- 17 HTML widgets (Live Clock, Countdown, Speedometer Gauge, Liquid Gauge, QR Code, Team Board, Weather, Traffic Lights, KPI Progress, Sparkline, Network Map, Globe 3D, Heatmap Calendar, Kanban, Org Chart, Terminal Log, Timeline Gantt)
- 29 animations and effects
- Remix button on dashboards — opens in Design Studio with widget types preserved
- Floating config popover (doesn't push panel off screen)
- Landing page rewrite — 3-path onboarding (Import / Template / Demos)
- Design Studio first-visit walkthrough

### Fixed
- CDATA HTML escaping bug — widgets now use inline XHTML with `&#160;`
- `data-target` attribute stripping — countdown uses `data-countdown-date`
- Gauge widgets now render as standalone SVG in HTML panels (no Splunk 10.2 single-value DOM dependency)
- Text color presets now apply via CSS custom properties (defeats `!important` rules)
- Config popover no longer pushes panels off screen (position:fixed)
- Effect checkbox scroll preservation (custom span replaces native checkbox, no focus auto-scroll)
- SPL comma errors across 4 demo dashboards (case/if/strftime/coalesce)
- Nav bar readability on all themes via CSS Modules wildcard selectors
- Panel entrance animations no longer conflict with opacity styles
- All widgets retry initialization (4 timeouts) to catch late-loading DOM

### Changed
- Cloud Mode moved from Settings tab to top bar pill switch
- Theme dropdown moved from Settings to Colors tab
- Panel config popover reorganized: Hide by Value at top, Advanced section collapsible
- is_configured = 0 (required for Splunkbase Cloud)
- Metadata permissions include sc_admin for Splunk Cloud

### Splunk Cloud Compatibility
- Passes AppInspect Cloud vetting (0 failures, 0 errors)
- No REST handlers, no scripted inputs, no Python/bin scripts
- No external network calls from JavaScript
- CSS-only mode works everywhere (Classic XML required for JS features)

## Requirements
- Splunk Enterprise 9.0+ or Splunk Cloud
- Classic Simple XML dashboards (version="1.1")
- Not compatible with Dashboard Studio
