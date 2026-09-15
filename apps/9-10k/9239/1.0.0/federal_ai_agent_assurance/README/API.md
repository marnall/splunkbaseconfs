# REST API

Base: /services/faaa (Splunk Web proxy: /splunkd/__raw/services/faaa).
Authentication: Splunk session; CSRF required on non-GET. All state
changes are POST with optional expected_revision and idempotency_key.
Responses always carry request_id; errors use stable codes
(bad_request, unauthorized, missing_capability, not_found, conflict,
illegal_transition, separation_of_duties, stale_revision,
idempotency_conflict, object_locked, payload_too_large, domain_violation,
unsupported_schema_version, blocking_findings, checksum_mismatch,
ai_disabled, internal_error, ...). HTTP: 200/201, 400, 401/403, 404, 409,
413, 422, 500.

GET  /health | /context | /agents | /releases | /releases/{id} |
     /releases/{id}/diff | /releases/{id}/waivers | /policies |
     /test-suites | /audit/verify[?chain_id=] | /settings | /ai/status
POST /agents | /agents/{id}/archive | /releases |
     /releases/{id}/(manifest|evaluate|tevv|submit|record-tests|review|
                     reopen|accept-risk|authorize|suspend|reinstate|
                     revoke|waiver|attest|export|ai-review) |
     /policies | /test-suites | /waivers/{id}/decide | /observations |
     /dependencies/import-lookupops | /dependencies/report-change |
     /evidence/verify | /evidence/import | /settings |
     /settings/credential | /maintenance/sweep-expirations |
     /admin/load-samples | /admin/self-test
