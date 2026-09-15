# Testing

Repository tests (outside the packaged app): `python3 -m pytest` at the
build root — 79 tests covering canonicalization/hashing, manifest
validation, semantic diff, the full policy DSL, state machine + SoD,
TEVV evaluation + tamper rejection, attestation, seals, audit chains +
tamper/delete detection, bundles (incl. byte-determinism and hardening),
security boundaries, AI guards, and the complete Section-28 acceptance
scenario against a splunkd simulator (the same harness pattern that
validated the approved LookupOps app).

Live-Splunk integration was NOT executed in this build environment (no
Splunk instance available); see COMPATIBILITY.md and the build's
TEST_REPORT.md for exactly what ran and what remains.
