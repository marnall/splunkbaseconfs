# OPSWAT MetaDefender for Splunk (`opswat-mdcore`)

Ready-made dashboards that visualize OPSWAT MetaDefender Core scan activity from **CEF syslog**.
Installable on **Splunk Cloud** and **Splunk Enterprise**.

## Requirements
- Splunk Enterprise 9.x or Splunk Cloud.
- MD Core syslog reaching Splunk via a Universal Forwarder (Cloud) or Splunk Connect for Syslog
  (SC4S) (Enterprise), tagged `sourcetype = opswat:mdcore:cef`.

## Setup
1. Install the app (Splunkbase, or **Install app from file** for air-gapped).
2. On MD Core, add a syslog connection of type **Splunk** pointing at your collector (port 1514 / SC4S).
3. Open the app and choose your index in each dashboard's **Index** selector.

Details: see the bundled `docs/syslog-setup.md`.

## Dashboards
Executive Overview, SOC Triage, Blocked Files, Deep CDR, Metascan, Sandbox & Deep Analysis,
Workflows, Audit & Compliance, Security Enforcing Functions, Data Volume & License.

## What it ships
The `opswat:mdcore:cef` sourcetype with CEF header and `OMS*` field extractions
(`props.conf` / `transforms.conf`). No credentials, no data inputs — parsing + dashboards only.

## Release notes
- 0.3.2 — Deep CDR success-rate now displays 1 decimal and is guarded so any sanitization failure keeps it below 100% (was rounding 99.8% up to 100%).
- 0.3.1 — Bug-fix pass: Deep CDR success-rate KPI corrected (was showing the file total as a %); DLP moved onto the Deep CDR dashboard as a second tab; Sandbox split into Adaptive Sandbox (embedded) and filescan.io (remote) tabs; Workflows now shows a per-rule activity/block/timing table (all rules, not just File process) and dual-format config-change audit; Security Enforcing Functions and Data Volume & License gained in-dashboard explanations.
- 0.3.0 — DLP & Deep CDR depth + dual-format resilience: dashboards now read fields via dual-format extraction (CEF `OMSx=` and native `x='..'`) and dedup by data_id, so they populate whichever syslog format MD Core emits; Deep CDR shows sanitize success/failure/rate/throughput; new Data Loss Prevention tab on Security Enforcing Functions.
- 0.2.1 — Fixed a FATAL regex error in Metascan (single-backslash `replace()` in the CEF-space-unescape eval).
- 0.2.0 — Dashboard schema fidelity: rebuilt Metascan on the real multiscan fields MD Core 5.20.0
  emits (`OMSthreatDetectedBy` / `OMSthreatFoundCount`); removed the phantom "Scan result received"
  per-engine event from Metascan and Data Volume; constrained the scan dashboards to the CEF
  `core.workflow | Processing finished` event so plain-text MSCL duplicates no longer inflate counts.
- 0.1.0 — Initial MVP: 10 dashboards + CEF parsing.

© OPSWAT, Inc. See LICENSE.
