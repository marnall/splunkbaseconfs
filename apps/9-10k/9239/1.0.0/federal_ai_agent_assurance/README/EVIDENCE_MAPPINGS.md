# Federal Evidence Mappings (informational)

These mappings describe which evidence THIS APP PRODUCES that an
organization may present under each framework. They are informational
evidence mappings for a readiness package — not certifications, not
control implementations, and not statements of compliance. Primary-source
re-verification against current official publications could not be
performed at build time (no network access in the build environment);
each entry below records the identifier as known at the model knowledge
cutoff and is marked accordingly. Verify identifiers, versions, and
section numbers against official NIST/OMB sources before citing them.

| Framework (as known at build) | Evidence produced by this app | Limits |
|---|---|---|
| NIST AI Risk Management Framework 1.0 (AI 100-1) — GOVERN/MAP/MEASURE/MANAGE | Named owners, impact determinations, policy findings, TEVV records, authorization decisions, reassessment triggers, audit trails | Mapping at function level, not per-subcategory; org context required |
| NIST Generative AI Profile (AI 600-1) | Release-scoped risk documentation, TEVV evidence, drift monitoring records | Informational; profile actions require org processes beyond this app |
| NIST SP 800-53 rev5 evidence categories (e.g., CA-6 authorization, CM-3 configuration change control, AU-2/AU-9 audit, RA-3 risk assessment) | Authorization records with conditions/expiration; sealed manifests + semantic diffs; hash-chained audit; risk-acceptance records | Evidence inputs only; controls are implemented by the organization |
| OMB federal AI governance / acquisition memoranda (M-24-10 / M-24-18 lineage; verify current successors) | AI use-case inventory fields, impact levels, human-oversight gates, TEVV + monitoring evidence | Identifiers may have been superseded; verify before citing |
| National-security AI guidance (e.g., NSM-based frameworks; verify current) | Same evidence classes for restricted enclaves; air-gapped operation | Applicability is org-determined |

Each policy in the Federal Agent Release Baseline carries
framework_mappings metadata with the same caveats. Last reviewed:
2026-07-17 (offline build; primary sources not re-fetched).
