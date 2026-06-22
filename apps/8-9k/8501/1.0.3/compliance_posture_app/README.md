# Compliance Posture for Splunk

**CIS Benchmark compliance tracking and reporting for Splunk environments.**

Import CIS-CAT Pro Assessor ARF XML scan results and visualize compliance posture across your infrastructure with historical trend tracking.

## Overview

No Splunk app exists — free or paid — that provides a scan-result-import-to-dashboard workflow for CIS-CAT output. This app fills that gap:

1. CIS-CAT Pro Assessor runs a scan and produces an ARF XML file
2. Upload the ARF XML through the browser-based drag-and-drop interface
3. Dashboards instantly display compliance posture, trends, and remediation priorities

Designed for financial services organizations — banks, credit unions, insurance companies — where FFIEC examination requirements and PCI DSS Requirement 2.2 mandate CIS Benchmark assessments. If your organization runs CIS-CAT scans and uses Splunk, this app gives you a native way to ingest, track, and report on scan results.

Companion app to the [STIG Compliance App](https://splunkbase.splunk.com) for federal environments — together covering both commercial and federal compliance frameworks from a single architectural foundation.

## Features

- **Browser-based upload** — Drag-and-drop CIS-CAT ARF XML files directly into Splunk
- **CIS Benchmark Overview** — Host-level compliance scores, pass/fail counts, failed rule details with filters by host, benchmark, and profile
- **Executive Summary** — Leadership-ready compliance posture with overall scores and benchmark distribution
- **Remediation Report** — Failed rules grouped by benchmark section for prioritized remediation
- **Upload History** — Compliance score trends over time, progress tracking by host, full upload log
- **Alerting** — Compliance threshold and new failure detection alerts (disabled by default, configurable per environment)
- **Dedup logic** — Always shows latest scan per host/benchmark combination
- **No forwarder or TA required** — Single app install, zero external dependencies

## Supported Input

- **CIS-CAT Pro Assessor v4** ARF XML output (Asset Reporting Format)
- Default filename convention: `[hostname]-CIS_[Benchmark_Title]-ARF.xml`
- Windows, Linux, and network device benchmarks supported

## Requirements

- Splunk Enterprise 8.x or 9.x
- Splunk Cloud (compatible with Cloud Vetting requirements)
- No additional apps, add-ons, or technology add-ons required

## Installation

1. Install from Splunkbase or upload the `.tar.gz` package via **Manage Apps > Install app from file**
2. Navigate to **Compliance Posture for Splunk** in the app menu
3. Use the **Upload Scan** page to import your first CIS-CAT ARF XML file

## Index Configuration

The app uses the `main` index by default. To use a dedicated index:

1. Create the target index on your indexers (e.g., `ciscat`)
2. Go to **Settings > Advanced Search > Search Macros**
3. Set the App filter to **Compliance Posture for Splunk**
4. Update the `ciscat_base`, `ciscat_latest`, and `ciscat_upload_history` macros — change `index=main` to your target index
5. No code changes or CLI access required

## Architecture

The app uses a two-layer design for extensibility:

- **Layer 1 — `parse_arf.py`**: Standalone ARF XML parser with zero Splunk dependencies. Normalizes CIS-CAT output into structured JSON events.
- **Layer 2 — `framework_mapper.py`**: Framework enrichment engine driven by JSON config files. CIS Benchmarks ships as the default configuration.

Sourcetype: `ciscat:arf`

## Dashboards

| Dashboard | Purpose |
|-----------|---------|
| CIS Benchmark Overview | Primary operational view — scores, pass/fail, failed rule details |
| Executive Summary | Leadership reporting — overall posture, compliance rates by system |
| Remediation Report | Prioritized failed rules grouped by benchmark section |
| Upload Scan | Browser-based ARF XML file upload |
| Upload History | Trend charts, progress tracking, upload log |

## Support

This is a free community app provided by GIC Engineering Consultants.

- **Bug Reports & Questions**: Use the Questions & Answers section on the Splunkbase listing — no cost, community-supported
- **Custom Implementations**: For deployment assistance, environment-specific configuration, or remediation support, contact GIC Engineering Consultants at [gicengineeringconsultants.com](https://gicengineeringconsultants.com)

Contact: marcus@gicengineeringconsultants.com

## Release Notes

### v1.0.0

- Initial release
- CIS-CAT Pro v4 ARF XML parser
- Four compliance dashboards plus upload interface
- Upload history with assessment-date trend tracking
- Configurable alerting (disabled by default)
- Framework-extensible architecture

## Author

GIC Engineering Consultants
[gicengineeringconsultants.com](https://gicengineeringconsultants.com)
marcus@gicengineeringconsultants.com
