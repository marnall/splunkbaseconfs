# Canonical JSON Profile and Manifest Schema

Federal.AI canonical JSON profile (NOT claimed to be RFC 8785):
UTF-8 input, NFC-normalized strings, ASCII-escaped output, object keys
sorted by code point, compact separators, NaN/Infinity rejected, floats
rejected in integrity-sealed content (use integers or normalized strings),
null significant and distinct from omitted, volatile keys (_key, _user,
updated_at/by, request_id, ui_state, last_evaluated_at) stripped before
hashing, timestamps as UTC "YYYY-MM-DDTHH:MM:SSZ".

Hashes: SHA-256 (`sha256:<hex>`); manifest hash = canonical hash of the
validated document; component hashes per section; root hashes over sorted
member hashes; evidence IDs = FAAA-EV-<16 hex> derived from canonical
change content (deterministic, never random).

The machine-readable interchange schema is faaa_manifest.schema.json.
Schema versioning: this release accepts schema_version "1.0" only; later
app versions will accept prior versions and upgrade explicitly. Unknown
versions are rejected safely with `unsupported_schema_version`.
