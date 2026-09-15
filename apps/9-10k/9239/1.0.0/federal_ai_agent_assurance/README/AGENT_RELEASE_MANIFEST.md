# Agent Release Manifest

The immutable canonical description of one agent release. Sections:
identity, governance, model, instructions, knowledge, lookup_dependencies,
mcp_tools, splunk_access, execution, memory, tevv, authorization_request,
plus one bounded `extensions` object for unknown vendor data.

Required minimum: identity.agent_id/agent_name/release_version/owner/
mission, governance.impact_level/impact_rationale/
reassessment_interval_days, model.provider/model_id,
execution.permitted_side_effects. See samples/sample_manifest_v1.json for
a complete valid example and MANIFEST_SCHEMA.md for the canonical JSON
profile and machine-readable schema.

Never place credentials, tokens, or private keys anywhere in a manifest —
validation rejects credential-shaped fields and values. Raw sensitive
prompts are not required: store a prompt hash + controlled reference.
MCP snapshots are explicitly versioned (mcp_protocol_version,
snapshot_version); unknown tool fields belong in `extensions`. Complex SPL
is not parsed: declare normalized access, and mark
splunk_access.spl_extraction_status = "unknown" to route to review.
