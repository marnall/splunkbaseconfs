# Search-Head Cluster Deployment

Deploy via the SHC deployer only. All mutable state is in replicated KV
Store; audit chains are object-scoped so concurrent members cannot fork a
verified chain's semantics; state transitions use object locks +
post-write claim verification (KV Store has no CAS — the residual race is
documented in SECURITY.md). No member-local files are written.

Validation checklist before production (real SHC execution was NOT
performed in this build environment — see COMPATIBILITY.md): install via
deployer; run a full lifecycle across two members; trigger a captain
change mid-workflow; race two conflicting transitions (exactly one must
succeed); rolling restart; verify audit chains after each step.
