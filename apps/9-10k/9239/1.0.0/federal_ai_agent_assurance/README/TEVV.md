# TEVV (Testing, Evaluation, Verification, Validation)

Three deterministic day-one paths, none requiring a live agent or LLM:
1. Static manifest + policy evaluation.
2. Offline execution-transcript import + deterministic evaluation.
3. Runtime snapshot comparison (see RUNTIME_ATTESTATION.md).

Suites are versioned and immutable once saved; completed runs are
immutable. Transcript format: schema_version 1.0, agent/release/suite/case
ids, environment and model metadata, ordered steps (tool calls with
sanitized arguments, result hashes, errors, side-effect classes, data
access), final status/output, human approvals, evidence refs, and a
content hash that is verified on import (tampered transcripts are
rejected).

The evaluator checks required/prohibited tools, ordering, step/duration
limits, side-effect and data-access boundaries vs. the manifest, required
evidence refs, expected status, escalation/fail-safe behavior, and bounded
output assertions. Every check is labeled with what it actually
establishes — string matching verifies recorded behavior, not semantic
correctness. No user-provided code is ever executed.

Samples: passing suite/transcripts, unauthorized-tool failure,
permission-boundary failure, and (via tests) tampered-transcript
rejection.
