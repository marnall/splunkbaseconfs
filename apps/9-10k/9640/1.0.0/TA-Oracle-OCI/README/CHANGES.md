# Changelog

All notable changes to TA-Oracle-OCI are documented in this file.

## 1.0.0
Initial release.

- Field extractions, sourcetypes (`oci:audit`, `oci:flowlogs`,
  `oci:cloudguard:problem`, `oci:loadbalancer`, `oci:objectstorage`,
  `oci:log`), and CIM tagging for Oracle Cloud Infrastructure (OCI) logs.
- **Push method**: companion OCI Function (`oci-function/`) posts events
  to Splunk HTTP Event Collector.
- **Pull method**: native modular input (`bin/oci_stream.py`) polls an
  OCI Stream directly using API-key authentication — the same
  Tenancy/User OCID, Fingerprint, and private key `.pem` fields the
  archived Splunk Addon for OCI (Splunkbase app 5222) used, for
  drop-in credential compatibility.
- No compiled binaries and no Python-version dependency, unlike the
  archived Splunk Addon for OCI (app 5222) and Splunk Cloud Addon for
  OCI (app 7021), both of which are incompatible with Splunk 9.3+/10.
- Splunk Cloud compatible build: no `setup.xml`, no shipped HEC input
  stanza, `sc_admin` ACLs, `python.version`/`python.required` declared
  for the modular input.
