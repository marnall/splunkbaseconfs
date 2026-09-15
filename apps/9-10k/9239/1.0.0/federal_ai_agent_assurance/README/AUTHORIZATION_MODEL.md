# Authorization Model

An authorization decision binds: agent, release, canonical manifest hash,
diff hash, policy pack + result hash, test suites + result hash, review
record hash, risk-acceptance hash, open findings/accepted exceptions,
conditions, deployment boundary, effective/expiration times, reassessment
triggers, authorizing principal, and app/schema versions.

The record carries a SHA-256 **integrity seal** over its canonical
content. This is tamper evidence: any change to bound content invalidates
the seal and creates a reassessment requirement. It is NOT an
authenticated digital signature — it proves content integrity, not signer
identity. The app requires no key provisioning; a customer-controlled
detached signature over exported evidence is a possible future extension
and is deliberately not half-implemented in 1.0.

Expiration is automatic (sweep runs on Overview/health access — no
scheduled search). A new authorization for the same agent supersedes the
prior one. Revocation is permanent as history; reauthorization is a new
decision. To suspend or revoke: Release Workbench detail -> Suspend /
Revoke (requires `faaa_suspend`).
