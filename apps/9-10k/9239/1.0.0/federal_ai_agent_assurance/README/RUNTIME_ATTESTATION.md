# Runtime Attestation

Import a versioned runtime/configuration observation (schema_version 1.0;
sources: manual_import, config_snapshot, transcript, telemetry_export,
bundle) and compare it with the authorized release boundary.

Per-field results: CONFORMANT, DRIFT, UNKNOWN, NOT_ATTESTABLE,
NOT_APPLICABLE. Fields the observation does not establish are UNKNOWN;
fields declared not_observable are NOT_ATTESTABLE; neither is ever
treated as conformant, and nothing unobserved is inferred.

Detected drift includes: unauthorized tools, changed tool schemas,
unauthorized endpoints, changed model/config/prompt hashes, data access
outside permitted indexes, side effects outside the permitted classes,
missing human-gate events on observed writes, changed lookup/knowledge
hashes, exceeded step limits, and expired authorizations. Drift marks the
release for reassessment; the optional `suspend_on_material_drift`
setting auto-suspends.

An optional normalized Splunk event schema (`federal_ai:agent_activity`)
is documented for customers who already index agent telemetry; any search
integration is administrator-configured, read-only, time- and index-
bounded, never `index=*`, and never required by the core workflow. This
release ships no searches at all.
