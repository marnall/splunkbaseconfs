# Data Model

Common record envelope: `schema_version`, `_key`, stable domain id,
`created_at`/`created_by` (UTC ISO 8601 Z), integer `revision`, lifecycle
status, content hash, provenance fields, archival status.

Immutable-by-convention records (no update/delete API; corrections create
superseding records): manifests once frozen at submission, reviews, risk
acceptances, authorizations, waiver decisions, completed test runs,
imported evidence, audit events. Releases and agents mutate through
guarded transitions with revision bumps.

Large content (transcripts, evidence) is bounded by configurable limits
(Limits class, hard-capped) and stored in bounded records well below KV
document limits. All KV queries are constructed server-side from validated
filters; list endpoints paginate (default 50, hard max 1000).
