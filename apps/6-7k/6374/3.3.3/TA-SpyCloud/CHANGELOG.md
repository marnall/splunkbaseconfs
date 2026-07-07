# SpyCloud Add-on for Splunk — Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [SemVer](https://semver.org/).

## [3.3.3] - 2026-05-29

### Changed
- **Watchlist now runs a second modification-date pass after the standard window**
  The standard `since` / `until` watchlist query remains unchanged. After it completes, the add-on now issues a second watchlist query with the same window mapped to `since_modification_date` and `until_modification_date`, using the same checkpoint and deduplication flow.

## [3.0.1] - 2025-12-05

### Added
- **Enhanced index validation for SpyCloud Index updates**
  Added index existence validation before updating SpyCloud inputs to prevent errors with invalid index names.

### Changed
- **Improved API key validation with comprehensive error handling**
  Enhanced API key validator with proper timeout handling, detailed proxy error messages, and better HTTP error handling for more informative user feedback during configuration.

- **Enhanced error messages for better user experience**
  Updated error messages for IP allowlist failures, API key issues, and rate limiting to provide clearer guidance and actionable troubleshooting steps.

- **Improved index update process with better error handling**
  Enhanced the SpyCloud index update functionality with improved error handling, better logging, and proper exception management.

### Fixed
- **Resolved index update reliability issues**
  Fixed potential issues in the index update process by adding proper error handling and validation checks.

---

## [2.0.5] - 2025-10-08

### Added
- **Set User-Agent on all API requests**  
  The add-on now sends `User-Agent: SplunkAddOn/2.0.0` on every outbound API call to improve traceability and vendor support. No configuration changes required.

- **Show clear API key failure messaging in setup and runtime**  
  Setup UI shows explicit reasons when key validation fails, and the add-on logs the same during execution. Covered cases: `429` quota exceeded, `403` wrong/disabled/deactivated key, and `403` allowlist failure with the offending source IP included. Runtime logs only; setup displays and logs.

- **Hourly breach ingestion option using last-run cursor**  
  Adds an “Ingest hourly” toggle. When enabled, the add-on runs hourly and uses the last successful run time as the `since` parameter to avoid duplicates and to deliver breach details soon after notifications. Default remains the existing daily schedule. Requested by Australian Unity.

### Changed
- **Proxy support for outbound API calls (already implemented, QA verified)**  
  Confirmed proxy support exists and functions for all API requests from the add-on. This item documents QA verification only. Reference: Zendesk ticket 11990.

- **Historical backfill on watchlist updates (already implemented, documented; QA on duplicates)**  
  Confirmed behavior that newly added identifiers pull all past records on the next run. Duplicate events are prevented via checkpointing. Documented that “Reload SpyCloud Database” clears the checkpoint and reloads everything, not selective items. Added QA guidance to validate duplicate suppression.

---

## [2.0.4] - 2025-10-07
Baseline for this changelog. No changes listed here.
