# Policy DSL

Declarative, closed, safe. Operators: exists, not_exists, equals,
not_equals, in, not_in, subset, contains, not_contains, starts_with,
ends_with, glob (bounded * and ? only — no regex in 1.0), greater_than,
greater_than_or_equal, less_than, less_than_or_equal, changed, added,
removed, expired_before, older_than_days; combinators any/all/not.
Conditions are capped at 200 nodes / depth 12.

Evaluation is three-valued: True/False/UNKNOWN. UNKNOWN (missing or
non-comparable data) is never treated as conformant; blocking policies
stay blocking on UNKNOWN. Policies whose scope object does not exist yet
(authorization/observation before one is recorded) report NOT_APPLICABLE.

Policy fields: policy_id, integer version, title, description, severity
(info..critical), scope (manifest|diff|tevv|authorization|observation),
source, condition, expected_result (absent|present), remediation,
blocking, framework_mappings, effective_date, supersession metadata.

The built-in **Federal Agent Release Baseline** (FAAA-BL-001..025) is
read-only and immutable; clone a policy to a new policy_id to customize.
A policy version used in a material decision remains immutable — create a
higher version instead.
