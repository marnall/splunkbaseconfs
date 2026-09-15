# Architecture

Browser -> Splunk Web (CSRF) -> persistent REST handler `faaa_rest.py`
(`/services/faaa/*`, requireAuthentication) -> `faaa_lib` engine ->
splunkd KV Store / storage-passwords (user's own session; ACL-enforced) ->
optional admin-configured local LLM endpoint (server-side only).

Modules (bin/faaa_lib): canonical (Federal.AI canonical JSON profile,
hashing, seals, evidence IDs), validate (boundary validation, secret
rejection, bounded glob), manifest (Agent Release Manifest), diffing
(semantic diff + authority expansion), policy + policy_baseline (closed
DSL + Federal Agent Release Baseline), statemachine (lifecycle + SoD),
tevv (suites, transcripts, deterministic evaluator), attest (runtime
conformity), audit (object-scoped hash chains), bundle (evidence packages
+ hardened archives), store (KV + locks + idempotency), rbac, settings,
samples, ai/ (providers, review, jsonschema_lite), api (orchestration).

Collections: faaa_agents, faaa_releases, faaa_manifests, faaa_policies,
faaa_findings, faaa_test_suites, faaa_test_runs, faaa_reviews,
faaa_risk_acceptances, faaa_authorizations, faaa_observations,
faaa_dependencies, faaa_waivers, faaa_audit, faaa_settings, faaa_locks —
all replicated (SHC-suitable). No runtime writes into the app directory.

Provenance: reuse of the Splunkbase-approved Federal AI LookupOps
patterns is recorded in the build's SOURCE_REUSE/LOOKUPOPS_REUSE_INVENTORY.
