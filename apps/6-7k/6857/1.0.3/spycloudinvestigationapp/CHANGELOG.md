# SpyCloud Investigations App for Splunk — Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [SemVer](https://semver.org/).

## [1.0.2] - YYYY-MM-DD

### Changed
- **Cluster-wide INV API credential handling for SHC**  
  The app now checks Splunk credential storage instead of a local `is_configured` flag. In multi-search head clusters, one stored key serves all search heads, avoiding per-node entry. If no credentials exist, the app redirects to setup and displays an alert.

---

## [1.0.1] - 2025-10-07
Baseline for this changelog. No changes listed here.
