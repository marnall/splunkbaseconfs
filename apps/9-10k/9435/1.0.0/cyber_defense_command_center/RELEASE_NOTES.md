# Release notes

**Author:** Eric Cobbs
**Required dependency:** Splunk Enterprise Security 8.x

## 1.0.0 — Initial public release candidate

- Establishes 1.0.0 as the first public release version.
- Identifies Eric Cobbs consistently as the application author and publisher.
- Makes Splunk Enterprise Security 8.x an explicit required dependency throughout application metadata and documentation.
- Adds Cloud-ready `[id]` metadata, reproducible release validation, normalized packaging, and a Splunkbase readiness checklist.
- Ships every scheduled detection, assessment, notifier, inventory refresh, and lab search disabled until an administrator completes configuration and testing.
- Preserves the validated detection-assurance, content-coverage, risk-quality, data-readiness, threat-conversion, analyst-workload, and evidence-pipeline capabilities from the development series.

## 0.8.5 — Splunk app-menu icon correction

- Adds the required case-sensitive `appIconAlt.png` and `appIconAlt_2x.png` assets used by Splunk bar and search-bar app menus.
- Retains the standard launcher icons and header logos introduced in 0.8.4.
- Adds an incremented install build number so Splunk Web refreshes versioned static assets after upgrade.

## 0.8.4 — ES-aligned application branding

- Replaces the high-neon application mark with a cleaner command-center shield aligned to the dashboard palette.
- Uses charcoal, slate, cyan, and blue as primary colors with restrained green, amber, and red status accents.
- Adds validated transparent Splunk launcher icons at 36×36 and 72×72 and header logos at 160×40 and 320×80.

## 0.8.3 — Detection Prompt Studio retirement

- Removes Detection Prompt Studio because it did not perform an actionable detection-engineering operation.
- Removes its navigation entry, dashboard definition, AI-specific requirements, and related security-design language.
- Preserves Detection Assurance Center and all validated ES extension dashboards and assessments.

## 0.8.2 — Detection Prompt Studio rendering correction

- Increases every Prompt Studio input control to a Splunk 10-compatible height.
- Reflows the form and expands the dashboard canvas so text and dropdown inputs render at normal browser zoom.
- Leaves the token-only, non-executing prompt composition and approval boundaries unchanged.

## 0.8.1 — Detection Assurance terminology correction

- Renames Detection Automation Center to Detection Assurance Center while retaining its validated scheduled assessments.
- Renames assessment searches, fields, macro, summary source, view, navigation, documentation, and optional finding notifier to use assurance terminology.
- Removes the legacy automation document and avoids representing the feature as autonomous remediation.
- Leaves Detection Prompt Studio and native ES approval boundaries unchanged.

## 0.8.0 — Detection requirements and guided assurance workflow

- Adds Detection Prompt Studio for composing structured event-based and finding-based detection requests without executing SPL, calling AI, storing prompts, or creating content.
- Adds optional same-tab handoffs to Splunk AI Assistant and ES Content Management.
- Adds an analyst-facing Assurance Center guide, assessment cadence, stale-assessment metric, operating-status inventory, seven-day default window, and correctly ranked review queue.
- Documents required and optional components for Splunk Enterprise, Splunk Cloud, ES testing, content versioning, and AI activation.
- Keeps AI generation optional while the native Splunk AI Assistant activation is pending.

## 0.7.2 — Same-tab navigation correction

- Replaces implicit view entries in Detection Assurance and Pipeline Assurance with explicit app-relative links.
- Sets `target="_self"` on all seven affected dashboard links so Splunk reuses the current browser tab.
- Leaves Operations Extensions and all validated assurance searches unchanged.

## 0.7.1 — Assurance summary timestamp correction

- Stamps every assessment state with `_time=now()` before summary collection.
- Prevents long dispatch windows from placing runtime, data-contract, and zero-yield states outside the dashboard's default 24-hour range.
- Validated all six assessment SPL pipelines against the live Splunk Enterprise Security lab.
- Preserves the disabled-by-default finding notifier and non-mutating assurance boundary.

## 0.7.0 — Detection Assurance Center and OWASP alignment

- Adds an ES-aligned Detection Assurance Center with current issue, severity, trend, and engineering review panels.
- Adds reliability, runtime-regression, schedule-collision, metadata-compliance, data-contract, and zero-yield assessments.
- Writes compact healthy/open states to the summary index; no assessment edits, enables, disables, reschedules, promotes, or deletes detections.
- Adds an optional, disabled-by-default ES finding notifier for recent high or critical engineering issues.
- Maps the design to OWASP Top 10:2025 and documents AppInspect and ASVS-based release requirements.
- Adds release-package SHA-256 integrity verification.

## 0.6.1 — Data visibility correction

- Restores cross-app REST detection inventory searches after confirming the scheduled CSV cache did not persist its results.
- Disables the non-writing lookup refresh job and removes the empty lookup dependency from dashboard searches and macros.
- Adds a disabled, synthetic-only one-time Risk backfill detection for the existing 30-day lab dataset.
- Preserves the ES-aligned v0.6 visual system and accelerated aggregate searches.

## 0.6.0 — Enterprise Security visual alignment

- Adopts the installed ES 1200-pixel layout proportions, compact section headers, 35-pixel key metrics, flat native panels, bottom legends, and hidden chart-axis titles.
- Uses the native ES status and severity palette while preserving CDCC semantic green, amber, and red indicators.
- Removes high-saturation panel backgrounds and returns to native dark-theme surfaces.
- Aligns donut, table, chart, spacing, and navigation treatments with ES dashboard conventions.

## 0.5.1 — Lookup filter syntax correction

- Moves enabled and disabled filters into a separate `search` command after `inputlookup`, resolving the invalid-argument error.
- Refreshes the detection inventory across all app namespaces so native ES and CDCC detections are both cached.

## 0.5.0 — Search-layer performance optimization

- Caches detection metadata in a scheduled lookup, replacing repeated dashboard REST calls.
- Uses the accelerated ES Risk and Incident Management models for compatible count panels.
- Retains native risk and notable searches where detailed quality, SLA, or investigation fields are required.
- Ships an empty lookup schema so dashboards remain valid before the first refresh completes.

## 0.4.3 — Assurance panel parser correction

- Seeds the Assurance Debt by Layer search before its append subsearches, resolving the Splunk SearchParser error.
- Ensures the risk-quality layer returns zero rather than disappearing when no matching risk events exist.

## 0.4.2 — Semantic dashboard color system

- Adds bright green, yellow, and red semantic accents while retaining the dark cyber theme.
- Uses red for failures and exceptions, yellow for risk and warning conditions, and green for healthy or enabled signals.
- Expands chart and donut palettes for clearer visual separation.

## 0.4.1 — SLA macro correction

- Declares `cdcc_finding_sla_hours` as a literal SPL macro instead of an eval macro, eliminating the SearchParser error.

## 0.4.0 — Detection-to-finding pipeline

- Adds safe search-time normalization for synthetic Windows JSON.
- Adds five scheduled event-based detections with ES risk actions.
- Adds two ES finding-based detections over the Risk data model.
- Adds ATT&CK annotations, stable detection IDs, staggered schedules, and finding suppression.
- Updates data-readiness panels to parse JSON fields before measuring completeness.

## 0.3.0 — Non-duplicative ES extension review

- Removes Security Posture, Risk Analysis, Finding Geography, Mission Control timeline, generic entity investigation, TI inventory, index-volume, source-health and analyst-audit duplication.
- Retains only cross-capability assurance and engineering analytics not clearly provided by native ES.
- Adds configurable finding SLA analytics.
- Refocuses risk, threat, data and pipeline dashboards on quality and conversion gaps.
- Reduces the dashboard suite from eleven to nine extension-only views.

## 0.2.0 — Enterprise Security extension architecture

- Repositions the app as an assurance and engineering extension for Enterprise Security.
- Adds Detection Content Coverage as an eleventh dashboard.
- Expands detection health with skipped executions, runtime percentiles, failure details, and zero-yield candidates.
- Adds risk-event quality and CIM field-completeness analysis.
- Refactors navigation into ES Assurance and Investigation Extensions.
- Documents the capability boundary between native ES and CDCC.

## 0.1.2 — Macro-based index scoping

- Replaces hard-coded dashboard index scopes with centrally managed macros.
- Adds security, risk, internal, and audit index macros.
- Defaults customer security telemetry to `index=cdcc_demo` for the development lab.
- Preserves the native Enterprise Security `notable` macro for findings.

## 0.1.1 — View registration fix

- Wraps each Dashboard Studio JSON definition in the required version-2 Splunk dashboard XML knowledge object.
- Corrects the 404 response caused by unregistered raw `.json` view files.

## 0.1.0 — Development preview

- Introduces ten coordinated Dashboard Studio experiences.
- Adds executive, detection, RBA, threat-intelligence, analyst, CIM, timeline, investigation, geographic, and enrichment views.
- Uses native visualizations for baseline Splunk Enterprise and Splunk Cloud compatibility.
- Adds a high-tech cyber visual system and publication-sized app branding.
- Provides CIM- and Enterprise Security-aligned searches with global time controls.

This preview must be validated against customer field conventions and Splunk AppInspect before public Splunkbase submission.
