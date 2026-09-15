# Evidence Export

Per release: (1) human-readable authorization/assurance report
(report.txt), (2) canonical JSON evidence package (evidence.json)
containing the registry record, manifest + hashes, diff, policies and
findings, test runs, review, risk acceptance, waivers, authorization +
seal, observations/attestations, dependency evidence, audit-chain export,
and provenance, (3) a hash manifest (manifest.json) listing every entry
with size and SHA-256, packaged as (4) an offline transfer archive (.zip)
that is byte-deterministic for identical input (tested) and hash-verified
on import, with (5) a verification report produced by the Verify action.
