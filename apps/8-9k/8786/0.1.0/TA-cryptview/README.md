# TA-cryptview

## Purpose

`TA-cryptview` is a minimal Splunk Technology Add-on for ingesting CryptView CBOM (Cryptographic Bill of Materials) inventory, PQC (Post-Quantum Cryptography) readiness evidence, posture summary, asset change events, audit events, and optional CycloneDX CBOM standards artifacts.

This MVP is file-monitor based. It is not yet an API or HEC integration.

## Beta Notice and Usage Disclaimer

CryptView for Splunk is provided as a beta/community preview for evaluation, testing, and feedback. It is provided "as is" without warranties, and results are evidence-based and advisory only. CryptView output is not legal, compliance, regulatory, security certification, audit certification, or procurement advice; users must validate results before relying on them.

Authorized/authorised use only: only scan public domains, systems, endpoints, or data that you own or are authorized/authorised to assess. Do not use CryptView, the CryptView Collector/CLI, or this TA to assess third-party infrastructure without permission. Do not submit private keys, secrets, credentials, keystore passwords, API tokens, session tokens, cookies, or other sensitive material.

The Splunk app visualizes CryptView-generated data and does not perform active scans from Splunk, run PQC probes from Splunk, or include the CryptView Collector/CLI. The CryptView Collector/CLI is separate and must be run outside Splunk by authorized users.

This TA has no modular input, scripted collector, or bundled scanner, and does not initiate outbound network activity. Splunk file monitoring reads local files only from paths configured by the Splunk administrator.

PQC evidence limitation: standard TLS-only evidence does not prove PQC transport support or lack of support. CryptView reports PQC transport as `not tested` unless active or otherwise proven PQC transport evidence exists. This is readiness visibility and not a certification.

Support and feedback: hello@qwocks.com

## Installation Location

Install the package with Splunk's app install flow, or extract/install the app folder at:

- `$SPLUNK_HOME/etc/apps/TA-cryptview/`

Do not place deployment-specific inputs in `default/`. Create `$SPLUNK_HOME/etc/apps/TA-cryptview/local/inputs.conf` after installation by using the example file in this package.

## Quick Start

1. Install `TA-cryptview` with Splunk's app install flow or under `$SPLUNK_HOME/etc/apps/TA-cryptview/`.
2. Create or confirm the Splunk index `cryptview` through Splunk index management.

3. Generate CryptView NDJSON outside Splunk:

```bash
python3 -m cryptview.cli export-splunk
```

4. Copy the packaged input example to a local runtime config:

```bash
cp $SPLUNK_HOME/etc/apps/TA-cryptview/examples/inputs.conf.example $SPLUNK_HOME/etc/apps/TA-cryptview/local/inputs.conf
```

5. Edit `local/inputs.conf` for the CryptView export paths and set the desired stanzas to `disabled = 0`.
6. Restart Splunk or reload the app and inputs.
7. Validate ingestion:

```spl
`cryptview_index` sourcetype=cryptview:*
| stats count by sourcetype
```

8. Open the dashboard:

- `TA-cryptview` -> `CryptView CBOM Overview`

Direct Splunk Web path:

- `/app/TA-cryptview/cryptview_overview`

## How To Get CryptView Collector/CLI

The CryptView Collector/CLI is provided separately from this Splunk TA during beta. Contact hello@qwocks.com for private beta access, onboarding instructions, and supported export workflows.

## Developer Packaging

For repository development, the TA source lives at:

- `splunk/TA-cryptview`

Build a clean Splunkbase beta archive from the repository root:

```bash
scripts/package_splunk_ta.sh
```

The script writes a tarball under `dist/` and leaves the `local/` directory out of the package.

On macOS, the script also strips extended attributes and removes AppleDouble/resource-fork metadata such as `.DS_Store`, `._*`, and `__MACOSX` before creating the tarball.

## Generate NDJSON From CryptView

Generate the Splunk export files from the current latest inventory:

```bash
python -m cryptview.cli export-splunk
```

If your environment uses `python3`, run:

```bash
python3 -m cryptview.cli export-splunk
```

CryptView Collector/exporter produces these files outside Splunk. The TA only ingests and visualizes the generated NDJSON.

Raw CSV files must not be monitored directly by Splunk. Customer CSV inputs should be processed by the CryptView Collector/CLI first, then Splunk should ingest the generated NDJSON files from `reports/splunk/`.

The exporter writes fixed compatibility files:

- `reports/splunk/cryptview_assets.ndjson`
- `reports/splunk/cryptview_summary.ndjson`
- `reports/splunk/cryptview_events.ndjson`

It also writes rotation-friendly timestamped copies to:

- `reports/splunk/assets/cryptview_assets_<timestamp>.ndjson`
- `reports/splunk/summary/cryptview_summary_<timestamp>.ndjson`
- `reports/splunk/events/cryptview_events_<timestamp>.ndjson`

The fixed filenames remain for backward compatibility. For continuous Splunk monitoring, the per-type subfolders are the safer default.

The rotated monitor stanzas should include `crcSalt = <SOURCE>`. CryptView exports often share similar first bytes across runs, and Splunk's file monitor uses CRC/fishbucket tracking to decide whether a file has already been indexed. Salting with the source path tells Splunk to treat each timestamped export file as distinct.

Asset NDJSON keeps legacy fields such as `pqc_posture`, `priority`, `risk_score`, `expiry_status`, `key_type`, and `tls_version`, and now also adds safe flattened layered PQC fields such as:

- `pqc_overall_interpretation`
- `pqc_tls_protocol_observed`
- `pqc_key_exchange_status`
- `pqc_negotiated_group`
- `pqc_certificate_identity`
- `pqc_certificate_in_use`
- `pqc_signature_algorithm`
- `pqc_evidence_level`
- `pqc_confidence`
- `pqc_probe_status`
- `pqc_recommended_next_action`
- `pqc_hardening_notes`
- `pqc_risk_evidence`

## Optional CycloneDX CBOM Artifact

Splunk NDJSON is the operational dashboard feed. The dashboard uses:

- `cryptview:cbom:asset`
- `cryptview:cbom:summary`
- `cryptview:cbom:event`

CycloneDX CBOM is a standards and audit artifact. Index it separately with:

- `cryptview:cbom:cyclonedx`

Generate CycloneDX from CryptView:

```bash
python3 -m cryptview.cli export --format cyclonedx --input reports/cbom_latest.json --output reports/splunk/cyclonedx/cbom_cyclonedx.json
```

You can also write CycloneDX to another controlled folder such as `reports/cyclonedx/` and point the optional monitor stanza there.

Do not use CycloneDX as the primary source for this TA dashboard. It is intentionally kept beside the normalized NDJSON feed so teams can retain a standards-format CBOM for audit, exchange, and compliance review.

## Configure inputs.conf

Copy `examples/inputs.conf.example` to `$SPLUNK_HOME/etc/apps/TA-cryptview/local/inputs.conf` after installing the app, then update the monitored paths to match the CryptView host where the NDJSON files are written.

No monitor inputs are enabled in `default/`. The example stanzas remain under `examples/inputs.conf.example` so Splunkbase packages do not include a `local/` directory.

Example:

```ini
[monitor:///opt/cryptview/reports/splunk/assets/*.ndjson]
disabled = 0
index = cryptview
sourcetype = cryptview:cbom:asset
crcSalt = <SOURCE>

[monitor:///opt/cryptview/reports/splunk/summary/*.ndjson]
disabled = 0
index = cryptview
sourcetype = cryptview:cbom:summary
crcSalt = <SOURCE>

[monitor:///opt/cryptview/reports/splunk/events/*.ndjson]
disabled = 0
index = cryptview
sourcetype = cryptview:cbom:event
crcSalt = <SOURCE>

[monitor:///opt/cryptview/reports/splunk/cyclonedx/*.json]
disabled = 0
index = cryptview
sourcetype = cryptview:cbom:cyclonedx
crcSalt = <SOURCE>

[monitor:///opt/cryptview/reports/workspaces/default/audit.log]
disabled = 0
index = cryptview
sourcetype = cryptview:audit
```

Keep `crcSalt = <SOURCE>` on rotated NDJSON and CycloneDX monitors when enabling continuous ingestion. It is not needed for the audit log monitors because those are append-only log files rather than timestamped replacement-style exports.

Workspace audit logs normally live at `reports/workspaces/<workspace_id>/audit.log`.

Anonymous quick-scan audit lives separately at:

- `reports/public_ephemeral/audit.log`

If you prefer authenticated API export over direct file monitoring, fetch `GET /api/audit/export.ndjson` on a schedule outside Splunk and write it to a local file that Splunk monitors. The TA does not push over HEC in this MVP.

Legacy single-file monitoring still works because the exporter continues to refresh:

- `reports/splunk/cryptview_assets.ndjson`
- `reports/splunk/cryptview_summary.ndjson`
- `reports/splunk/cryptview_events.ndjson`

## Open the Dashboard

After installing the app and reloading Splunk, open the dashboard from the app navigation:

- `TA-cryptview` → `CryptView CBOM Overview`

Direct view path in Splunk Web:

- `/app/TA-cryptview/cryptview_overview`

The overview is organized for demo screenshots:

- executive command-center header for the CryptView CBOM and PQC readiness story
- global filters for time range, index/search scope, asset search, priority, hybrid/PQC key exchange state, certificate identity, and PQC certificate use
- KPI rows for total assets, expiry pressure, expired certificates, high-priority assets, transport-not-tested assets, classical certificate identity, PQC certificate use, and hybrid/PQC transport observations
- a layered PQC readiness matrix that separates:
  - Hybrid/PQC key exchange
  - Certificate identity
  - Evidence confidence
- short display buckets are used in the PQC charts so Splunk panels show labels such as `Not tested`, `Hybrid/PQC observed`, `Probe ran: no hybrid`, `Classical RSA`, `Classical ECDSA`, `PQC certificate/signature`, `Low`, `Medium`, and `High` instead of long raw strings
- categorical PQC views now use pie-style charts for faster executive reading, while issuer, expiry, priority, and risk panels stay bar-oriented
- certificate lifecycle views for expiry status, renewal windows, issuer concentration, and key-size signals
- risk and migration views for priority distribution, risk score buckets, top risk reasons, and top remediation priorities
- a CBOM inventory explorer with layered PQC fields such as `pqc_key_exchange_status`, `pqc_certificate_identity`, `pqc_evidence_level`, `pqc_confidence`, and `pqc_recommended_next_action`
- recent event panels for `cryptview:cbom:event`
- an audit placeholder panel describing how `cryptview:audit` data will appear once ingested
- asset-based dashboard panels deduplicate to the latest record per `asset_id` so repeated exports do not double-count inventory

## Layered PQC Model In Splunk

The Splunk dashboard intentionally keeps the CryptView layered PQC model intact instead of collapsing everything into a single yes/no score.

- `pqc_posture` is still present for backward compatibility and legacy rollups.
- `pqc_key_exchange_status` represents the transport layer.
- `pqc_certificate_identity` and `pqc_certificate_in_use` represent the certificate/signature layer.
- `pqc_evidence_level` and `pqc_confidence` help distinguish standard TLS-only evidence from stronger PQC-capable probe evidence.
- `pqc_recommended_next_action` is meant for migration and hardening review, not for driving scans from Splunk.

Visual interpretation:

- `Not tested` means the transport layer was not proven either way by the observed scan evidence.
- `Hybrid/PQC observed` means CryptView saw transport-layer hybrid/PQC evidence.
- `Probe ran: no hybrid` means a PQC-capable probe ran but did not negotiate hybrid/PQC transport.
- `Classical RSA` and `Classical ECDSA` describe the certificate identity layer, not the transport layer.
- `PQC certificate/signature` means certificate or signature evidence indicates PQC capability.
- `Low`, `Medium`, and `High` confidence summarize how strong the evidence is, not whether the asset is good or bad by itself.

Splunk visualizes CryptView exports. It does not run TLS scans, PQC probes, or inventory discovery.

## Suggested Index Creation

Create a dedicated index such as:

- `cryptview`

This keeps CryptView asset inventory, posture, change telemetry, and audit events separate from other security data.

## Search Macro

The bundled dashboard and sample searches use the `cryptview_index` macro. The default macro is defined in `default/macros.conf` as:

```spl
index=cryptview
```

If your deployment uses a different index or search scope, override `cryptview_index` after installation in `$SPLUNK_HOME/etc/apps/TA-cryptview/local/macros.conf` rather than editing packaged defaults. Updating this macro changes the default search scope for bundled dashboard panels and sample SPL that call `` `cryptview_index` ``.

## Sourcetypes

- `cryptview:cbom:asset`
- `cryptview:cbom:summary`
- `cryptview:cbom:event`
- `cryptview:cbom:cyclonedx`
- `cryptview:audit`

## Sample SPL Searches

Count by sourcetype:

```spl
`cryptview_index` sourcetype=cryptview:*
| stats count by sourcetype
```

Latest-state CBOM asset table:

```spl
`cryptview_index` sourcetype=cryptview:cbom:asset
| stats latest(*) as * by asset_id
| eval owner=coalesce(owner, "-"), business_unit=coalesce(business_unit, "-"), environment=coalesce(environment, "-")
| table asset_display_name asset_host asset_port owner business_unit environment tls_version key_type key_size expiry_status priority risk_score pqc_key_exchange_status pqc_certificate_identity
```

PQC readiness summary:

```spl
`cryptview_index` sourcetype=cryptview:cbom:asset
| stats latest(*) as * by asset_id
| stats count by pqc_key_exchange_status pqc_certificate_identity pqc_confidence
```

Priority and risk distribution:

```spl
`cryptview_index` sourcetype=cryptview:cbom:asset
| stats latest(*) as * by asset_id
| eval risk_score_bucket=case(risk_score>=80,"80-100",risk_score>=60,"60-79",risk_score>=40,"40-59",risk_score>=20,"20-39",isnull(risk_score),"Unknown",1=1,"0-19")
| stats count by priority risk_score_bucket
```

Recent CBOM events:

```spl
`cryptview_index` sourcetype=cryptview:cbom:event
| table _time event_type asset_id display_name previous_priority current_priority previous_pqc_posture current_pqc_posture
| sort - _time
```

Optional CycloneDX artifact check:

```spl
`cryptview_index` sourcetype=cryptview:cbom:cyclonedx
| table _time bomFormat specVersion serialNumber version
```

## Splunk Field Naming Notes

- Asset records now include `asset_host`, `asset_port`, and `asset_display_name` for Splunk-safe dashboards and tables.
- Prefer `asset_host` and `asset_port` over raw `host` and `port` in Splunk searches. Splunk's reserved `host` metadata is the Splunk input host, not necessarily the CryptView asset host.
- Legacy fields such as `host`, `port`, and `display_name` are still exported for backward compatibility.
- Use `stats latest(*) as * by asset_id` for asset dashboard searches so repeated rotated exports do not double-count historical copies of the same asset.
- Use `coalesce(field, "-")` or dashboard display fields for nullable ownership/context values so tables do not show raw nulls.

Example field usage:

```spl
`cryptview_index` sourcetype=cryptview:cbom:asset asset_host="demo.example.com"
```

```spl
`cryptview_index` sourcetype=cryptview:cbom:asset asset_display_name="demo.example.com:443"
```

## Known Limitations

- This is an MVP file-monitor based TA, not yet an API or HEC integration.
- The exporter reads the current latest CBOM inventory and summary files; it does not stream live changes.
- Change events are derived from the latest inventory state fields and reflect the most recently recorded change per asset.
- The exporter stays additive and does not mutate `cbom.json` or `cbom_latest.json`.
- CycloneDX ingestion is optional and intended for standards/audit artifact retention, not as the dashboard's normalized operational source.
- Splunk visualizes CryptView output; it does not execute scanning, discovery, or PQC probes.
- Splunk should prefer `asset_host` over `host` because `host` can collide with Splunk metadata.
- The bundled Splunk dashboard is a Simple XML MVP focused on current CBOM posture visibility.
- The dashboard defaults to the `cryptview_index` macro but allows a search-scope override through the top filter bar.
- dashboard asset panels intentionally deduplicate to the latest state per `asset_id` to avoid double-counting repeated exports
- Panel polish is optimized for screenshots and demo review, not yet for deep analyst investigation flows.
- The exporter preserves the current internal CBOM schema rather than introducing a Splunk-specific source model.
- The current package still bundles ingestion plus dashboard assets together for MVP speed.
- Target future split:
  - `TA-cryptview` for sourcetypes, props, inputs, and ingestion conventions
  - `CryptView` Splunk App for dashboards, reports, and analyst views

## Splunkbase Beta Preparation

Submission draft notes live in:

- `docs/SPLUNKBASE_SUBMISSION.md`

Local package command:

```bash
scripts/package_splunk_ta.sh
```

The package script stages a clean copy, removes macOS metadata files, keeps `examples/inputs.conf.example`, excludes the entire `local/` directory, and creates an archive with one top-level app directory: `TA-cryptview/`.

Optional AppInspect check, if AppInspect is installed:

```bash
splunk-appinspect inspect dist/TA-cryptview-0.1.0.tar.gz
```

Before submitting, confirm that:

- no real secrets are included
- no enabled monitor inputs are present in `default/`
- no local machine paths are present in `default/`
- `examples/inputs.conf.example` uses deployment-specific placeholders
- Splunk visualizes CryptView exports and does not run scans from the TA
