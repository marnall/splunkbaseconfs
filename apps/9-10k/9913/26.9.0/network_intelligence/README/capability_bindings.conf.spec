#   Version 1.0
#
############################################################################
# OVERVIEW
############################################################################
# capability_bindings.conf declares source-specific Network Intelligence
# health bindings. A binding describes how source events become canonical
# capability observations and generates one health materializer saved search.
#
# Full contract:
# docs/health/reference/capability-bindings-contract.md
#
############################################################################
# STANZA
############################################################################

[<binding_id>]
* One stanza per binding.
* The stanza name is the stable binding identifier, conventionally
  <source_system>.<capability_name>, for example [meraki.device_availability].

############################################################################
# IDENTITY AND DESCRIPTION
############################################################################

binding_id = <string>
* Optional. Defaults to the stanza name.
* Stable, unique identifier starting with a lower-case letter, followed by
  lower-case letters, numbers, dots, underscores, or hyphens.

capability_id = <string>
* Required for an active binding.
* Must reference an enabled capability from capabilities.conf.

title = <string>
* Optional. Human-readable binding title. Defaults to binding_id.

description = <string>
* Optional. Human-readable description of the source mapping.

source_system = <string>
* Required for an active binding.
* Stable, lower-case source namespace such as meraki or thousandeyes.

############################################################################
# SOURCE PREPARATION
############################################################################

base_search = <SPL string>
* Required for an active binding.
* Bounded source search used by the generated materializer.
* Must not contain side-effecting commands such as collect, outputlookup,
  delete, sendemail, or map.

pre_transform_spl = <pipe-prefixed SPL fragment>
* Optional. Runs after base_search and before expansion_step.<n>.
* Must begin with a pipe and must not contain side-effecting commands.

expansion_step.<n> = <JSON object>
* Optional. Declarative array-expansion step, applied in numeric order.
* Each object requires path and output. Optional keys are input and fields.

let.<name> = <SPL eval expression>
* Optional. Reusable intermediate field evaluated in declaration order.
* Must be an eval expression, not an SPL pipeline fragment.

############################################################################
# SUBJECT RESOLUTION
############################################################################

subject = <subject_class>:<subject_type>
* Required for an active binding and must match the capability subject.
* V1 supports vertex subjects only.

subject_id_type = mac_address | serial_number | internal_identifier | ifindex | site_name
* Required for an active binding.
* Identifier type used to resolve the subject through ni_vertex_mappings.

subject_id_expr = <SPL eval expression>
* Required for an active binding. Produces the subject identifier value.

subject_id_template = <string>
* Optional documentation and debugging metadata describing the identifier
  shape. It is not used for materialization.

subject_id_namespace = <string>
* Conditionally required for an active binding.
* Set this for a globally resolvable subject identifier. Do not set it when
  the parent_id_type, parent_id_namespace, and parent_id_expr triad is used.

parent_id_type = mac_address | serial_number | internal_identifier | ifindex | site_name
* Conditionally required for a parent-scoped subject.
* Must be declared together with parent_id_namespace and parent_id_expr.

parent_id_namespace = <string>
* Conditionally required for a parent-scoped subject.
* Namespace used to resolve the parent vertex.

parent_id_expr = <SPL eval expression>
* Conditionally required for a parent-scoped subject.
* Produces the parent identifier value.

############################################################################
# METRICS, STATE, AND TIME
############################################################################

materializer_group = <string>
* Required for an active binding. Stable lower-snake-case materializer group.

metric.<name> = <SPL eval expression>
* At least one metric expression is required for an active binding.
* <name> must exist in the capability's metric_definitions.

state_expr = <SPL eval expression>
* Required for an active binding.
* Must return one of the capability's state_values.

score_expr = <SPL eval expression>
* Optional. Produces a score from 0 through 100, or null.

observed_time_expr = <SPL eval expression>
* Required for an active binding. Produces source observation epoch seconds.

############################################################################
# MATERIALIZATION POLICY AND EVIDENCE
############################################################################

pivot_policy = <JSON object>
* Optional. Bucket and pivot policy for event-per-metric sources.
* Supported keys are bucket_span, group_by, and aggregations.

aggregation_policy = <JSON object>
* Required for an active binding.
* current must be latest_observed, latest_worst_state, or
  latest_complete_bucket. Optional keys are dedupe_fields and within_bucket.

evidence_search_template = <JSON object>
* Required for an active binding.
* Must contain index, sourcetype, and a non-empty keys object describing how
  to find the raw events behind an observation.

############################################################################
# LIFECYCLE AND SYSTEM METADATA
############################################################################

binding_status = draft | validated | active | disabled | error | deprecated
* Optional. Binding lifecycle status. Defaults to active.
* Materializers run only for active bindings with disabled = 0.

disabled = 0 | 1
* Optional. Standard Splunk conf toggle. Defaults to 0.
* 0 enables the binding; 1 disables it.

version = <string>
* Optional. Binding definition version. Defaults to 1.

registered_at = <epoch seconds>
* Optional system-managed registration timestamp.
* Do not set in shipped default binding definitions.
