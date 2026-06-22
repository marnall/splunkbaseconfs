# PhishIQPlus Customer Quickstart

Use this guide for a fast production-oriented installation on Splunk Enterprise / Heavy Forwarder.

---

## 1) Copy package files

Copy the following from the delivery bundle:

- `phishiq_ta-enterprise.tgz`
- `phishiq_ta-enterprise.tgz.sha256`
- `phishiq_ta-enterprise.manifest.txt`

---

## 2) Verify integrity

```bash
shasum -a 256 -c phishiq_ta-enterprise.tgz.sha256
```

The `.sha256` sidecar is the authoritative checksum for the tarball.

---

## 3) Install app

```bash
mkdir -p "$SPLUNK_HOME/etc/apps"
tar -xzf phishiq_ta-enterprise.tgz -C "$SPLUNK_HOME/etc/apps"
$SPLUNK_HOME/bin/splunk restart
```

---

## 4) Configure input

In Splunk Web:

1. Go to **Settings -> Data inputs**.
2. Open **PhishIQPlus URL Enrichment**.
3. Create or update stanza:
   - Set `API Base URL`
   - Set `API Key`
   - Set mode (`batch` or `dynamic`)
4. Save and enable.

---

## 5) Validate quickly

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

## 6) Reference docs

- `RELEASE.md` for upgrade and rollback flow.
- `TESTING.md` for end-to-end validation.
- `ENTERPRISE_HANDOVER.md` for operational handover checklist.

---

## 7) Copy-paste operational snippets

Install one-liner:

```bash
set -euo pipefail; PKG="phishiq_ta-enterprise.tgz"; shasum -a 256 -c "$PKG.sha256"; mkdir -p "$SPLUNK_HOME/etc/apps"; tar -xzf "$PKG" -C "$SPLUNK_HOME/etc/apps"; "$SPLUNK_HOME/bin/splunk" restart
```

Upgrade one-liner:

```bash
set -euo pipefail; PKG="phishiq_ta-enterprise.tgz"; shasum -a 256 -c "$PKG.sha256"; BK="$SPLUNK_HOME/etc/apps/phishiq_ta_backup_$(date +%Y%m%d_%H%M%S)"; "$SPLUNK_HOME/bin/splunk" disable input "phishiqplus_enrichment://default" || true; cp -R "$SPLUNK_HOME/etc/apps/phishiq_ta" "$BK"; rm -rf "$SPLUNK_HOME/etc/apps/phishiq_ta"; tar -xzf "$PKG" -C "$SPLUNK_HOME/etc/apps"; "$SPLUNK_HOME/bin/splunk" restart; echo "Backup: $BK"
```

Rollback one-liner:

```bash
set -euo pipefail; BK="$SPLUNK_HOME/etc/apps/phishiq_ta_backup_<timestamp>"; "$SPLUNK_HOME/bin/splunk" disable input "phishiqplus_enrichment://default" || true; rm -rf "$SPLUNK_HOME/etc/apps/phishiq_ta"; cp -R "$BK" "$SPLUNK_HOME/etc/apps/phishiq_ta"; "$SPLUNK_HOME/bin/splunk" restart
```
