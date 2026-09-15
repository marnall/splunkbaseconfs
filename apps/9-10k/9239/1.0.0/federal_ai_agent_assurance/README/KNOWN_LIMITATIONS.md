# Known Limitations

- Not tested on a live Splunk instance, SHC, or browser in this build
  environment; AppInspect not executed (no tooling available offline).
  See BUILD_REPORT/TEST_REPORT for the exact gaps.
- SHA-256 seals are tamper evidence, not signer authentication.
- Audit chains are tamper-evident, not immutable, and are object-scoped
  (no single global order is claimed).
- KV Store has no CAS; stale-revision + lock + post-write claim checks
  narrow but cannot eliminate the write race (disclosed in SECURITY.md).
- Runtime conformity is limited by what observations establish; the app
  never infers unobserved configuration.
- Arbitrary SPL is not parsed; declared access boundaries are used.
- Policy DSL ships without regex (bounded glob only) in 1.0.
- Evidence import is reference-only by design; there is no "restore to
  authorized" path.
- Large lookup/knowledge content is referenced by hash, not stored.
