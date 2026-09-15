# Offline Transfer

Verify-then-import on the receiving enclave: every entry hash is checked
before any content is parsed; internal manifest hash and authorization
seal are re-verified. Archives are rejected for: non-allowlisted entries,
directories, path separators/traversal, absolute-style names, duplicate
or case-colliding names, oversized entries/totals, suspicious compression
ratios, entry-list mismatches, unsupported schema versions, or any
checksum mismatch. Imported evidence is reference material only — it
NEVER creates, restores, or alters an authorized state on the receiving
system. Processing is in-memory (no temporary files).
