# PhishIQPlus Splunk Release Runbook

This runbook describes how to install, upgrade, validate, and roll back the packaged app.

---

## Package artifact

- App version: `1.1.0` (build `2`)
- Package file: `splunk/dist/phishiq_ta-enterprise.tgz`
- Authoritative SHA-256: use the sidecar file `phishiq_ta-enterprise.tgz.sha256` shipped next to the tarball (embedding the hash inside the tarball would change the tarball hash).

Verify on target host:

```bash
shasum -a 256 -c phishiq_ta-enterprise.tgz.sha256
```

---

## Install (fresh)

```bash
mkdir -p "$SPLUNK_HOME/etc/apps"
tar -xzf phishiq_ta-enterprise.tgz -C "$SPLUNK_HOME/etc/apps"
$SPLUNK_HOME/bin/splunk restart
```

Expected app path:

```text
$SPLUNK_HOME/etc/apps/phishiq_ta
```

---

## Upgrade (in-place)

```bash
$SPLUNK_HOME/bin/splunk disable input "phishiqplus_enrichment://default" || true
cp -R "$SPLUNK_HOME/etc/apps/phishiq_ta" "$SPLUNK_HOME/etc/apps/phishiq_ta_backup_$(date +%Y%m%d_%H%M%S)"
rm -rf "$SPLUNK_HOME/etc/apps/phishiq_ta"
tar -xzf phishiq_ta-enterprise.tgz -C "$SPLUNK_HOME/etc/apps"
$SPLUNK_HOME/bin/splunk restart
```

One-liner upgrade:

```bash
set -euo pipefail; PKG="phishiq_ta-enterprise.tgz"; shasum -a 256 -c "$PKG.sha256"; BK="$SPLUNK_HOME/etc/apps/phishiq_ta_backup_$(date +%Y%m%d_%H%M%S)"; "$SPLUNK_HOME/bin/splunk" disable input "phishiqplus_enrichment://default" || true; cp -R "$SPLUNK_HOME/etc/apps/phishiq_ta" "$BK"; rm -rf "$SPLUNK_HOME/etc/apps/phishiq_ta"; tar -xzf "$PKG" -C "$SPLUNK_HOME/etc/apps"; "$SPLUNK_HOME/bin/splunk" restart; echo "Backup: $BK"
```

Notes:

- Keep `local/` files from the previous app backup and restore them if needed.
- Re-enable inputs after validation.

---

## Post-deploy validation

1. Splunk UI:
   - Confirm app and dashboards are visible:
     - `PhishIQPlus - Health`
     - `PhishIQPlus - Manual Test`
     - `PhishIQPlus - Correlation`
2. Data input:
   - Confirm `PhishIQPlus URL Enrichment` exists under Data Inputs.
   - Save input once to ensure API key is in credential store.
3. SPL checks:

```spl
index=main sourcetype=phishiq_enriched | head 20
```

```spl
index=phishiqplus_internal sourcetype=phishiqplus:internal event_type=run_summary | head 20
```

```spl
| rest /servicesNS/-/-/saved/searches
| search title="PhishIQPlus - Alert*"
| table title disabled cron_schedule
```

---

## Rollback

If deployment fails:

```bash
$SPLUNK_HOME/bin/splunk disable input "phishiqplus_enrichment://default" || true
rm -rf "$SPLUNK_HOME/etc/apps/phishiq_ta"
cp -R "$SPLUNK_HOME/etc/apps/phishiq_ta_backup_<timestamp>" "$SPLUNK_HOME/etc/apps/phishiq_ta"
$SPLUNK_HOME/bin/splunk restart
```

One-liner rollback:

```bash
set -euo pipefail; BK="$SPLUNK_HOME/etc/apps/phishiq_ta_backup_<timestamp>"; "$SPLUNK_HOME/bin/splunk" disable input "phishiqplus_enrichment://default" || true; rm -rf "$SPLUNK_HOME/etc/apps/phishiq_ta"; cp -R "$BK" "$SPLUNK_HOME/etc/apps/phishiq_ta"; "$SPLUNK_HOME/bin/splunk" restart
```

After rollback, verify:

- Data input loads correctly.
- Existing dashboards and saved searches return expected results.
