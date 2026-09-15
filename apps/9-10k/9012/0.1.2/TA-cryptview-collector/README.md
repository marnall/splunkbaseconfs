# TA-cryptview-collector

## Purpose

`TA-cryptview-collector` is a self-contained Splunk Technology Add-on that runs the CryptView Collector Core on a Universal Forwarder or Heavy Forwarder host and emits metadata-only NDJSON to stdout for scripted input ingestion.

The `cryptview.collector` and `cryptview.parsers.cert_file_parser` Python modules are bundled inside the tarball (under `bin/lib/`) so the wrapper works out of the box on standard Splunk hosts. No CryptView repository checkout is required for the common install path.

CryptView Collector collects cryptographic metadata only. It does not collect private keys, passwords, keystore secrets, tokens, cookies, or confidential file contents.

## Companion App and Private Beta

- **[CryptView CBOM Overview (`TA-cryptview`) &mdash; Splunkbase app 8786](https://splunkbase.splunk.com/app/8786)** &mdash; companion Splunkbase dashboard app that visualizes the NDJSON this collector emits (certificate inventory, expiry pressure, weak-key/signature flags, PQC readiness posture derived from raw observations). Install both apps for end-to-end value.
- **CryptView private beta** &mdash; active PQC/hybrid TLS transport probing, fleet-wide CBOM aggregation, migration prioritization, CycloneDX audit export, and ownership/business-unit overlays live outside the two Splunkbase apps. Contact `hello@qwocks.com` for private beta access.

## What This TA Emits (Observation-Only Wire Format, v0.1.1)

The collector emits NDJSON events with **raw observation fields only**. Verdict/classification fields (`pqc_ready`, `risk_flags`) are intentionally **not** included &mdash; the CryptView server-side importer and the companion dashboard SPL derive PQC posture, priority, risk score, and risk flags from the same raw fields any downstream tool can read.

Per-event observation fields (see the [TA-cryptview dashboard app 8786](https://splunkbase.splunk.com/app/8786) for full field documentation):

- Certificate events: `subject`, `issuer`, `serial_number`, `not_before`, `not_after`, `san_dns_names`, `key_algorithm`, `key_size`, `signature_algorithm`, `is_ca`, `expires_in_days`, `fingerprint_sha256`, `has_private_key_material_detected`.
- Private-key-file events: `asset_type=private_key_file`, `has_private_key_material_detected=true`, plus file/path metadata. The file content is never emitted.
- Keystore events: `asset_type=keystore`, `keystore_type`, plus file/path metadata. Keystore content is never emitted.
- Status events (`event_type=collector_status`): `level`, `message` describing scan progress or per-file exceptions.

## Current Scope

- Filesystem-only collection
- Linux/macOS wrapper (shell + Python)
- NDJSON stdout output for scripted input ingestion
- X.509 metadata parsing via `cryptography`
- Private-key file presence detection (content never collected)
- Keystore inventory-only handling

Not included in v0.1:

- remote scanning
- Windows wrapper
- authenticated network scanning
- Splunk Cloud certification

## Prerequisites

- **Python 3.8+** available on the wrapper host. The shell wrapper (`bin/cryptview_collect.sh`) resolves the interpreter from `$CRYPTVIEW_PYTHON` if set, otherwise from `python3` on `PATH`.
- **`cryptography` Python package** importable to that interpreter. Splunk 9.x's bundled Python already includes it; system Python 3 may need `pip install cryptography`. Point `CRYPTVIEW_PYTHON=$SPLUNK_HOME/bin/python3` to reuse Splunk's runtime and avoid a separate install.

## Install Location

Install the app folder at:

- `$SPLUNK_HOME/etc/apps/TA-cryptview-collector/`

The bundled `bin/lib/cryptview/` provides everything the wrapper needs. For the private-beta workflow you can override with `CRYPTVIEW_HOME=/path/to/Qwocks-CryptView` to run against a live repository checkout.

## Safety and Default Behavior

- The scripted input is disabled by default.
- The wrapper does not auto-scan broad system paths by default.
- If enabled without explicit path configuration, the wrapper emits a valid `collector_status` NDJSON warning instead of scanning default system locations.
- Wrapper errors go to `stderr` so they do not corrupt NDJSON data output.

## Scripted Input

Default stanza:

```ini
[script://$SPLUNK_HOME/etc/apps/TA-cryptview-collector/bin/cryptview_collect.sh]
disabled = 1
interval = 86400
index = cryptview
sourcetype = cryptview:crypto_asset
```

## Required Wrapper Environment

Before enabling the scripted input, configure explicit collection paths for the wrapper.

Supported environment variables:

- `CRYPTVIEW_HOME`
  Path to the CryptView repository root if `cryptview.collector` is not already installed in the Python environment.
- `CRYPTVIEW_PYTHON`
  Optional explicit Python interpreter path for the shell wrapper, for example a virtualenv or system Python 3.
- `CRYPTVIEW_COLLECTOR_PATHS`
  Comma-separated filesystem paths to scan. Required for active collection.
- `CRYPTVIEW_COLLECTOR_REDACT_PATHS`
  `true` or `false`. Defaults to `true`.
- `CRYPTVIEW_COLLECTOR_FOLLOW_SYMLINKS`
  `true` or `false`. Defaults to `false`.
- `CRYPTVIEW_COLLECTOR_MAX_FILE_SIZE_BYTES`
  Max file size to inspect. Defaults to `5242880`.

Example paths:

- `/etc/nginx,/etc/ssl`
- `/opt/cryptview-demo/samples`

## Standalone Splunk Enterprise / Heavy Forwarder Setup

1. Install `TA-cryptview-collector` into:
   - `$SPLUNK_HOME/etc/apps/TA-cryptview-collector/`
2. Ensure Python 3 is available to the wrapper host.
3. Ensure the shared CryptView collector code is available:
   - set `CRYPTVIEW_HOME=/path/to/Qwocks-CryptView`
   - or install the CryptView Python package into the runtime environment used by the wrapper
4. Configure explicit collector paths in the wrapper environment or local wrapper copy.
5. Enable the scripted input manually in:
   - `$SPLUNK_HOME/etc/apps/TA-cryptview-collector/local/inputs.conf`
6. Restart Splunk or reload inputs.

Suggested local stanza:

```ini
[script://$SPLUNK_HOME/etc/apps/TA-cryptview-collector/bin/cryptview_collect.sh]
disabled = 0
interval = 86400
index = cryptview
sourcetype = cryptview:crypto_asset
```

## Local Testing Commands

Run the wrapper directly:

```bash
CRYPTVIEW_HOME=/path/to/Qwocks-CryptView \
CRYPTVIEW_PYTHON=/path/to/python3 \
CRYPTVIEW_COLLECTOR_PATHS=/etc/ssl,/etc/nginx \
python3 TA-cryptview-collector/bin/cryptview_collect.py
```

Run the shell wrapper:

```bash
CRYPTVIEW_HOME=/path/to/Qwocks-CryptView \
CRYPTVIEW_PYTHON=/path/to/python3 \
CRYPTVIEW_COLLECTOR_PATHS=./samples \
sh TA-cryptview-collector/bin/cryptview_collect.sh
```

Search in Splunk:

```spl
index=cryptview sourcetype=cryptview:crypto_asset
```

## Packaging

Create a tarball from the repository root:

```bash
tar -czf TA-cryptview-collector.tar.gz TA-cryptview-collector
```

Install into Splunk:

```bash
cp TA-cryptview-collector.tar.gz $SPLUNK_HOME/etc/apps/
cd $SPLUNK_HOME/etc/apps
tar -xzf TA-cryptview-collector.tar.gz
```

Then enable the scripted input manually in local config.

## AppInspect Note

Do not claim Splunk Cloud readiness yet. Splunk Cloud and AppInspect compatibility still require validation.

If Splunk AppInspect is available locally later, the expected command is:

```bash
splunk-appinspect inspect dist/TA-cryptview-collector.tar.gz --mode precert
```

## Universal Forwarder Note

Universal Forwarder deployment may require:

- system Python 3 availability
- an adjusted wrapper path/bootstrap strategy for the local environment
- an explicit `CRYPTVIEW_PYTHON` override when the default `python3` does not include the shared collector dependencies

This v0.1 package is documented first for standalone Splunk Enterprise or Heavy Forwarder use.

## Known Limitations

- no remote scanning
- no Windows wrapper yet
- no Splunk Cloud certification yet
- no private key or secret collection
- Universal Forwarder may require system Python 3 depending on deployment
