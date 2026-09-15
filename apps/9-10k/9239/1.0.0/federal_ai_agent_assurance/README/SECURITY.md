# Security

## Threat model summary
Assets: authorized-release integrity, decision provenance, evidence
authenticity, optional LLM credential. Adversaries considered: a
low-privilege Splunk user, hostile imported content (manifests,
transcripts, observations, bundles), a hostile/compromised LLM endpoint,
and an insider attempting to bypass separation of duties.

## Controls
- Identity/capabilities re-derived from splunkd per request; client-
  supplied actor identity ignored everywhere (test-asserted).
- Server-enforced state machine; SoD conflict matrix (creator/submitter
  cannot review, accept risk, or authorize; reviewer cannot authorize
  under the strict baseline; waiver requester cannot approve). Splunk
  admin does NOT bypass SoD. No emergency bypass exists.
- Stale-revision protection + object-scoped locks + idempotency keys on
  state changes; KV Store has no CAS, so claims are re-read post-write and
  the residual window is disclosed here, not hidden.
- All imports are hostile: bounded strings/arrays/depth/bytes, allowlisted
  fields (bounded `extensions` only), credential-field and token-value
  rejection, schema-version pinning, transcript content-hash verification.
- Bundles: exact-name allowlist, traversal/symlink/duplicate/case-collision
  rejection, size + ratio caps, every SHA-256 verified before parsing,
  import never creates an authorized state.
- Policy engine: closed declarative DSL; no code, SPL, or regex execution
  (bounded glob only); node-count and depth caps; UNKNOWN never counts as
  conformant.
- Audit: per-object hash chains, append-only by application convention.
  Tamper-EVIDENT, not cryptographically immutable — an administrator with
  direct KV Store access could alter records; forward `faaa.log`/audit
  data to an indexer for stronger guarantees. No global total order is
  claimed across chains.
- Authorization seals are SHA-256 integrity seals: tamper evidence, NOT
  authenticated digital signatures. No key provisioning exists in 1.0; a
  customer-controlled detached-signature hook is a documented future item.
- Optional AI: disabled by default, server-side only, TLS verification
  cannot be disabled (customer CA bundle supported; plaintext only to
  loopback), credential only in Splunk secure storage, nonce-fenced
  untrusted data, schema-constrained JSON output, hallucinated evidence
  rejected, zero lifecycle authority.
- UI renders exclusively via textContent/createElement; no innerHTML; no
  external assets; CSRF via Splunk Web's standard token.
- Errors carry stable codes + request IDs; no stack traces, paths,
  session keys, or secrets in responses or logs.

## Reporting
Report suspected vulnerabilities to LC@federal.ai with app and Splunk
versions and reproduction steps. Do not include real mission data.
