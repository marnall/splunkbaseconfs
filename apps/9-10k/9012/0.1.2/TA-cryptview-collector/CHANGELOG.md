# Changelog

## v0.1.2

- Packaging hygiene release.
- Normalized package archive metadata.
- No collector logic changes.
- No event schema changes.
- No dashboard compatibility changes.

## v0.1.1 Beta

- **Self-contained tarball.** The CryptView Collector Core and its certificate parser are now bundled inside `bin/lib/cryptview/` in the packaged Splunkbase artifact. Installers no longer need to set `CRYPTVIEW_HOME` or manually install the `cryptview` Python package for the common case. `CRYPTVIEW_HOME` is still honored as an override for private-beta or development installs.
- **Observation-only NDJSON wire format.** The collector no longer emits verdict fields on asset events:
  - Removed `pqc_ready` (bool). Server-side importer now derives PQC posture from `signature_algorithm` and `key_algorithm`.
  - Removed `risk_flags` (list). Server-side importer now derives risk flags from `expires_in_days`, `key_algorithm`, `key_size`, `signature_algorithm`, `has_private_key_material_detected`, `asset_type`, and `keystore_type`.
  - All raw observation fields are preserved. Any downstream tool reading the NDJSON can classify against the same raw data the CryptView server uses.
- **Compatibility.** The companion `TA-cryptview` Splunkbase dashboard v0.1.1 renders equivalently against v0.1.0 (verdict fields present) and v0.1.1 (observation-only) collector output.

## v0.1.0 Beta

- Initial private-beta wrapper. Metadata-only filesystem collection for certificates, private-key file presence, and keystore inventory. Scripted input disabled by default. Requires `CRYPTVIEW_HOME` pointing at a CryptView repository checkout or a Python environment where `cryptview.collector` is importable.
