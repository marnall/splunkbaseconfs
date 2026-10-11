#   Version 1.0
#
############################################################################
# OVERVIEW
############################################################################
# capabilities.conf declares source-independent Network Intelligence health
# capabilities. A capability defines the graph subject, canonical metric
# vocabulary, and supported health states that source-specific bindings emit.
#
# Full contract:
# docs/health/reference/capability-bindings-contract.md
#
############################################################################
# STANZA
############################################################################

[<capability_id>]
* One stanza per capability.
* The stanza name is the stable capability identifier, for example
  [device.availability] or [interface.throughput].

############################################################################
# IDENTITY AND DESCRIPTION
############################################################################

capability_id = <string>
* Optional. Defaults to the stanza name.
* Stable, unique identifier starting with a lower-case letter, followed by
  lower-case letters, numbers, dots, underscores, or hyphens.

title = <string>
* Optional. Human-readable capability title. Defaults to capability_id.

description = <string>
* Optional. Human-readable purpose and interpretation.

subject = <subject_class>:<subject_type>
* Required.
* Graph subject selector. V1 supports vertex subjects such as vertex:device,
  vertex:interface, and vertex:tunnel.

############################################################################
# METRIC AND STATE CONTRACT
############################################################################

required_metrics = <JSON array or comma-separated list>
* Optional. Canonical metric names that describe the capability's primary
  vocabulary. Every name must exist in metric_definitions.

optional_metrics = <JSON array or comma-separated list>
* Optional. Additional canonical metric names. Every name must exist in
  metric_definitions and must not also appear in required_metrics.

metric_definitions = <JSON object>
* Required when disabled = 0.
* Reference catalog keyed by canonical metric name.
* Each metric must define unit, value_type, and polarity. See the full
  contract for the supported metadata fields and vocabularies.

state_values = <JSON array or comma-separated list>
* Required when disabled = 0.
* Must include ok, degraded, critical, and unknown.

############################################################################
# LIFECYCLE AND SYSTEM METADATA
############################################################################

disabled = 0 | 1
* Optional. Standard Splunk conf toggle. Defaults to 0.
* 0 enables the capability; 1 disables it.

version = <string>
* Optional. Capability definition version. Defaults to 1.

registered_at = <epoch seconds>
* Optional system-managed registration timestamp.
* Do not set in shipped default capability definitions.
