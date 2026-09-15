# Cyber Defense Command Center

**Author:** Eric Cobbs

**Required dependency:** Splunk Enterprise Security 8.x

> Cyber Defense Command Center requires Splunk Enterprise Security. It is not a standalone security application.

Cyber Defense Command Center is a non-duplicative assurance and engineering extension for Splunk Enterprise Security. Native ES remains authoritative for Security Posture, Mission Control, findings, investigations, Risk Analysis, Finding Geography, threat-intelligence management, analyst queue audit, source health, indexing audit, and data-model acceleration.

## Extension-only capabilities

- Detection reliability, failures, skips, runtime percentiles and zero-yield candidates
- Detection metadata debt and content-coverage hygiene
- Risk-event entity, score, message and type-quality assurance
- Raw-threat telemetry to detection and finding conversion analysis
- Field-level detection readiness and ingest-lag exceptions
- Finding SLA breach, p90 aging and queue-equity analytics
- Raw-event to risk-event to finding pipeline conversion
- Approved external read-only enrichment launch points

## Requirements

- Splunk Enterprise 9.2 or later, or a compatible Splunk Cloud Platform deployment
- Splunk Enterprise Security 8.x
- CIM-aligned data sources

## Macros

Index scopes and the finding SLA are centralized in default/macros.conf. Update cdcc_security_indexes for production telemetry and cdcc_finding_sla_hours for the organization's SLA. Dashboard searches contain no hard-coded index scopes.

## Install

Upload the packaged TGZ from Apps > Manage Apps > Install app from file. Restart only if Splunk requests it. Open Cyber Defense Command Center and validate searches against local ES field conventions.

## Initial configuration

All scheduled detections, assurance assessments, notifiers, inventory refreshes, and lab searches ship disabled. Before enabling content, an administrator must configure the index macros, confirm ES permissions and field contracts, review summary-index retention, validate schedules and suppression, and run bounded tests in a non-production environment.

## Detection pipeline

Version 1.0.0 includes five enabled event-based detections that write intermediate findings to the ES risk index and two enabled finding-based detections that create ES findings. The development default is scoped to `index=cdcc_demo`. Review schedules, thresholds, and risk scores before changing the security-index macro for production. Windows JSON normalization is search-time and does not override the shared `WinEventLog:Security` sourcetype.

## Status

Version 1.0.0 is the initial public release candidate. Complete the documented release gates before production deployment.
