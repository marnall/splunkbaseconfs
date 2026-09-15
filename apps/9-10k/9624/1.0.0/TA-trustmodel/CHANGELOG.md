# Changelog

All notable changes to TA-trustmodel will be documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.0-alpha] — 2026-05-05

### Aligned with TRUS-785 v1.0 schema (TRUS-784)
- Collapsed sourcetypes from 5 (per-domain) to **2** (per-shape):
  - `trustmodel:eval` — evaluation lifecycle (all flavors)
  - `trustmodel:finding` — detected risk / issue
- Eval flavor (LLM, COTS, agentic_trace, DataScan) now carried in
  `eval_source` field on every event. Sub-flavors (fair_lending, hr_bias,
  healthcare, ...) carried in `eval_meta.eval_subtype`.
- Removed standalone sourcetypes for `guardrail`, `shadow_ai`, `redteam`
  (out of scope for v1).
- `props.conf` simplified — KV_MODE=json auto-extracts nested
  `eval_meta.*` and `evidence.*` directly.
- CIM compliance: strict on `Alerts` data model (`trustmodel:finding`),
  `trustmodel:eval` is not mapped to a CIM datamodel.
- Time field anchored on top-level epoch `time` for both sourcetypes.

### Added (carried over from package skeleton)
- Initial Technology Add-on package (TRUS-786)
- Eventtypes + tags for CIM datamodel inclusion
- Search macros (`trustmodel_index`, `trustmodel_eval`, `trustmodel_finding`,
  per-`eval_source` and per-`dimension` convenience macros)
- README with HEC setup
- Default permissions / metadata

### Pending
- AppInspect-clean validation
- Splunk Cloud Vetted certification
- Dashboard Studio JSON + Simple XML dashboards (TRUS-788)
- ES correlation searches in companion `DA-ESS-TrustModel` (TRUS-787)
