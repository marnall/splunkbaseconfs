# EAT — Environment Assessment Tool

**Version:** 1.0.0  
**Author:** Splunk Architect  
**Compatibility:** Splunk 8.x, 9.x | Standalone offline use

---

## Overview

A comprehensive Splunk environment assessment tool for architects and senior administrators performing environment audits, health checks, and security reviews. Designed for use on both standard and air-gapped classified networks (SIPR/JWICS).

This tool works in **two modes**:
- **Standalone** — open `assessment.html` directly in any browser, no Splunk required
- **Splunkbase app** — install to Splunk and access at `/en-US/static/app/splunk_architect_assessment/assessment.html`

---

## Features

### Assessment Coverage (55+ checks)
- **Infrastructure** — Cluster health, bucket replication, SHC stability, KV Store
- **Forwarder fleet** — Heartbeat coverage, version drift, DS management
- **Index & storage** — Retention, disk headroom, hot bucket sizing
- **Config files** — outputs.conf, props.conf, server.conf, authorize.conf
- **Ingestion pipeline** — Queue fill levels, throughput balance, parsing errors
- **Data quality** — CIM compliance, volume trends, line-breaking health
- **Search workload** — Slot saturation, slow searches, data model acceleration
- **Authentication** — Role audit, local accounts, audit log completeness
- **TLS & certs** — Certificate expiry, port exposure, web hardening
- **Operations** — Error rates, app version consistency, version currency
- **Splunk ES / SIEM** — Correlation search health, RBA, threat intel, asset/identity
- **CIM compliance** — Authentication, Network Traffic, Endpoint data model coverage
- **MITRE ATT&CK** — Initial Access, Persistence, Credential Access, Exfiltration, Lateral Movement
- **SIPR specifics** — Telemetry disabled, FIPS 140-2, offline license, CAC/PKI auth

### Functionality
- **Health scoring** — Weighted A–F grade with per-section breakdowns
- **Evidence capture** — Paste SPL output directly into each check
- **Remediation guidance** — Step-by-step fix instructions for every check
- **Baseline comparison** — Load a previous assessment JSON to track improvements/regressions
- **MITRE ATT&CK view** — Coverage dashboard mapped to ATT&CK tactics
- **Export** — Plain text report, print-to-PDF, JSON save/load
- **Fully offline** — Zero external dependencies, no CDN calls, works air-gapped

---

## Installation

### As a Splunkbase App
1. Download the `.spl` (tar.gz) package
2. In Splunk Web: Apps → Manage Apps → Install app from file
3. Navigate to: `https://<your-splunk>:8000/en-US/static/app/splunk_architect_assessment/assessment.html`

### Standalone (no Splunk required)
1. Extract the package
2. Open `appserver/static/assessment.html` in Chrome or Edge
3. No installation required

### SIPR / Air-gapped Transfer
See the transfer guide in `README/TRANSFER_GUIDE.txt` for instructions on moving this tool through cross-domain solutions (DOTS, Trusted Guard, etc.)

---

## Usage

1. Work through each check section by section
2. Set status: **Pass / FAIL / Warning / N/A**
3. Click "details" to expand the SPL query, pass/fail criteria, and remediation steps
4. Paste your SPL output into the Evidence tab for documentation
5. Add analyst notes in the Notes field
6. Use **Save JSON** to checkpoint your work
7. Use **Export Report** for a findings document
8. Use **Compare** to load a previous assessment and track changes

---

## Splunk AppInspect Notes

- No REST API calls made by this app
- No credentials stored or transmitted
- No external network calls (fully static HTML/JS)
- Compatible with Splunk Cloud (static file serving only)
- No Python backend required

---

## Changelog

**v1.0.0** (Initial release)
- 55 checks across 14 domains
- A–F health scoring with weighted checks
- Evidence capture per check
- Remediation guidance for all checks
- MITRE ATT&CK coverage view
- Baseline comparison mode
- Export to text/PDF
- SIPR/air-gap compatible

---

## License

Apache License 2.0 — See LICENSE file

## Support

File issues at the Splunkbase app page or community.splunk.com
