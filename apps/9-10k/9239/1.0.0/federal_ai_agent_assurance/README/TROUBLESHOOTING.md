# Troubleshooting

- "endpoint not found" after install: restart Splunk (restmap.conf).
- KV errors on Health: verify KV Store is enabled (`splunk show
  kvstore-status`); collections list shows per-collection status.
- 403 with code missing_capability: the response names the exact faaa_*
  capability to grant.
- 409 separation_of_duties: a different qualified person must act; the
  message names the conflicting role. This is by design.
- 409 stale_revision / object_locked: reload the record and retry.
- 422 unsupported_schema_version: the imported document's schema_version
  is newer/older than this app supports.
- AI errors: ai_disabled (enable in Settings), insecure_endpoint (https
  required), ai_tls_error (provide ai_ca_bundle_path; verification cannot
  be disabled), ai_schema_violation / ai_hallucinated_evidence (the model
  response was rejected — deterministic results are unaffected).
- Logs: $SPLUNK_HOME/var/log/splunk/faaa.log (request IDs + error codes
  only; no payloads or secrets).
