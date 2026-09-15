# Optional Behind-the-Firewall AI Review

Disabled by default; the app is fully functional without it. No call
occurs at installation, page load, or discovery — only when an
administrator has configured a provider AND a user holding `faaa_use_ai`
explicitly requests a review.

Providers: openai_compatible, ollama, custom_json, disabled. Endpoint
must be https:// (plaintext permitted only to loopback for a local
runtime, mirroring the approved LookupOps pattern). TLS verification
cannot be disabled; a customer CA bundle path is supported. The service
credential lives only in the Splunk credential store. Requests/responses
are size- and time-bounded; server-side only; no redirects to unapproved
hosts (no redirect following at all).

Modules: risk_summary, contradiction_check, reviewer_questions,
release_narrative. Untrusted content is nonce-fenced; responses must be
schema-exact JSON; any citation of a non-existent evidence ID rejects the
whole response. Output is stored as advisory with provider, model, times,
hashes, requesting user, and human disposition. AI can never submit,
pass tests, review, accept risk, waive, authorize, suspend, revoke,
change policy or settings, alter audit history, or export secrets; an
AI-generated policy proposal is an untrusted draft until a human creates
and validates a policy version.
