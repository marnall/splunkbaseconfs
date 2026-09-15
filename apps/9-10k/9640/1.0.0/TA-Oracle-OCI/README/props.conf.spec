#   Version 1.0.0
#
# This file documents the sourcetype stanzas TA-Oracle-OCI ships
# in default/props.conf. All attributes used are standard Splunk
# props.conf attributes (see Splunk's own props.conf.spec for the full
# attribute reference) -- this file exists to document which sourcetypes
# this app defines and why, not to introduce new attribute syntax.

[oci:audit]
* Oracle Cloud Infrastructure Audit Logs, delivered via HEC push
  (oci-logs-to-splunk-hec Function) or the oci_stream modular input.
KV_MODE = <string>
* Set to "json" -- audit records are single-line JSON objects; Splunk's
  JSON auto-kv extraction handles field extraction at search time.
TIME_PREFIX = <regex>
* Anchors timestamp extraction to the record's "eventTime" field.
TIME_FORMAT = <string>
* strptime-style format matching OCI's ISO-8601 timestamp,
  e.g. 2026-08-21T12:00:00.000Z.
MAX_TIMESTAMP_LOOKAHEAD = <integer>
* How many characters past TIME_PREFIX to scan for the timestamp.
SHOULD_LINEMERGE = <boolean>
* Set to false -- each HEC POST / stream record is already one event.
category = <string>
* UI grouping shown in Settings > Source types. "Cloud Infrastructure".
pulldown_type = <boolean>
* Set to true so this sourcetype appears in the sourcetype picker.
description = <string>
* Human-readable description shown in the Source types UI.
EVAL-vendor = <eval-expression>
* Search-time constant field, "Oracle" -- identifies the data vendor
  for CIM/Enterprise Security correlation searches that filter or join
  across multiple vendors' data.
EVAL-product = <eval-expression>
* Search-time constant field, "Oracle Cloud Infrastructure" (or "Oracle
  Cloud Guard" for [oci:cloudguard:problem]) -- identifies the specific
  product alongside vendor.

[oci:flowlogs]
* OCI VCN Flow Logs. Same attribute set as [oci:audit], timestamped from
  the record's "time" field instead of "eventTime".

[oci:cloudguard:problem]
* OCI Cloud Guard Problems (security findings). TIME_PREFIX matches
  "eventTime" -- confirmed present at the envelope's top level via a
  real example payload in Oracle's own Cloud Infrastructure blog
  (see README.md's "Known field-mapping fixes" section for the URL).
  That same sample showed no fractional seconds in the timestamp
  (unlike Audit's), so TIME_FORMAT omits subsecond precision -- adjust
  if a real sample with fractional seconds is observed.
* EVAL-product = "Oracle Cloud Guard" here, distinct from the other
  sourcetypes' "Oracle Cloud Infrastructure".

[oci:loadbalancer]
* OCI Load Balancer access/error logs.

[oci:objectstorage]
* OCI Object Storage access logs.

[oci:log]
* Fallback sourcetype for any OCI record that does not match a more
  specific type/source pattern during sourcetype auto-detection in
  bin/oci_stream.py or oci-function/func.py.
