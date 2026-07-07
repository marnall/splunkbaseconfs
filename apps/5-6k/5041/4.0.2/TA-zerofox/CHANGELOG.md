# Changelog

All notable changes to the ZeroFox Data Collector for Splunk are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.0.2] — 2026-06-10

### Fixed

- **`app.manifest` — `platformRequirements`** corrected to `"Enterprise": "*"` (was `">=8.2"`, which failed Splunkbase SLIM validation).
- **Build pipeline — platform-specific native extensions** removed from the shipped package. The macOS mypyc-compiled `.so` files bundled by `charset_normalizer` are now stripped during `prune-output` so the add-on works correctly on Splunk Enterprise Linux deployments.

---

## [4.0.1] — 2026-06-09

### Changed

- **Version bump for Splunkbase resubmission.** Maintenance release — no functional changes from 4.0.0.
- **`app.manifest` — `releaseDate`** set to `2026-06-09` (was `null`).
- **Cloud Vetting** confirmed clean: 0 errors, 0 failures against Splunk AppInspect before submission.

---

## [4.0.0] — 2026-06-04

### ⚠ Breaking Changes

- **Input model replaced.** The 13 separate per-feed modular inputs
  (`zfox_cti_botnet://`, `zfox_cti_ransomware://`, etc.) are replaced by a
  single unified **ZeroFox Intel (CTI)** input type with a feed selector
  dropdown. Existing inputs will not carry over after upgrade — they must be
  recreated in **Settings → Data inputs → ZeroFox Intel (CTI)**.
  Checkpoints are migrated automatically; no data will be re-collected.

- **Framework changed from Add-on Builder (AoB) to UCC.** Internal
  file layout, REST handler names, and credential storage format have all
  changed. Do not mix files from 3.x and 4.x installations.

- **License changed** from Apache 2.0 to Proprietary. For licensing
  inquiries contact ask@zerofox.com.

### Added

- **Unified CTI input** — a single "ZeroFox Intel (CTI)" modular input
  replaces the 13 legacy per-feed inputs. Select the feed (Botnet,
  Ransomware, Phishing, etc.) from a dropdown when creating each input.
- **Workflow action** — a "View in ZeroFox" link appears in the event
  context menu on `zerofox:alerts` events and opens the alert directly in
  the ZeroFox cloud portal (`cloud.zerofox.com`).
- **`eventtypes.conf`** — defines `zerofox_alerts` (`sourcetype=zfox`)
  for scoping searches and workflow actions.
- **`props.conf` — `TIMESTAMP_FIELDS`** — each sourcetype now declares its
  timestamp field so events are indexed at the actual event time rather than
  ingest time.
- **ZeroFox app icons** — app icon now shown in the Splunk launcher.
- **Checkpoint migration** — on first run after upgrade the new input
  automatically reads the legacy AoB checkpoint and resumes from where 3.x
  left off.

### Changed

- **`props.conf` — `TRUNCATE`** raised from 10 000 bytes to unlimited (`0`)
  for all sourcetypes. Ransomware and other large records were previously
  silently truncated.
- **Logging** — INFO-level operational messages (collection start, event
  count summaries) demoted to DEBUG. Only error conditions are logged at the
  default log level. Enable DEBUG in **Configuration → Logging** for
  verbose output.
- **Alerts `source` field** — corrected from `zerofox_alerts://<name>` to
  `zfox://<name>`. Existing saved searches using `source=zfox://*` will now
  match correctly.
- **CTI lookback timestamps** — first-run date parameters now include an
  explicit UTC suffix (`Z`) to prevent API timezone ambiguity.
- **Checkpoint writes** — reduced from one file write per indicator to one
  write per API page, significantly reducing I/O on high-volume feeds.

### Removed

- **`email_addresses` and `national_ids` CTI feeds** — these feeds are not
  supported in the ZeroFox Splunk integration and have been removed.
- **Add-on Builder (`aob_py3`) dependency** — replaced by the UCC framework
  and standard Splunk SDK libraries.

### Fixed

- HTTP error responses from the ZeroFox API no longer produce multiple
  broken log lines when the response body contains newlines.
- `intel_sources.yaml` was previously missing from the deployed app package
  in some build paths, causing CTI inputs to fail on startup with
  `IntelSourcesValidationError`. The build pipeline now guarantees the file
  is always present.

---

## [3.7.3] — 2026-06-02

Initial import into the integrations-architecture monorepo. No functional
changes from the version published on Splunkbase.

---

## [3.7.2] and earlier

See the [Splunkbase listing](https://splunkbase.splunk.com/app/5041) for
release history prior to monorepo migration.
