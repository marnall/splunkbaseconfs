# Changelog

## v0.1.0 Beta

- Added the CryptView CBOM asset dashboard for Splunk-native inventory, certificate lifecycle, risk, and migration-priority review.
- Added layered PQC readiness fields that separate transport/key-exchange evidence, certificate identity, evidence level, confidence, and recommended action.
- Added rotation-friendly NDJSON ingestion guidance for asset, summary, event, audit, and optional standards artifacts.
- Added `cryptview:cbom:cyclonedx` sourcetype support for CycloneDX CBOM JSON as an optional standards/audit artifact.
- Documented the CSV-to-CryptView-to-Splunk onboarding path for pilot data: customer CSV inputs are processed by CryptView Collector/CLI first, then exported as Splunk-ready NDJSON.
- Kept beta limitations explicit: the TA visualizes CryptView-generated data only, does not run scans from Splunk, does not include the Collector/CLI, and provides evidence-based readiness visibility rather than certification.
