# TA-airtable-auditlogs: installation on a Heavy Forwarder

The Python libraries (`requests`, `splunklib`) and the index definition ship
inside the app. Only three things cannot be bundled, because they are secret or
specific to your tenant.

## Prerequisite

Outbound HTTPS from the HF to `api.airtable.com`. Sort this first, it is usually
the long pole.

---

## 1. Extract

```bash
tar -xzf TA-airtable-auditlogs.tar.gz -C $SPLUNK_HOME/etc/apps/
```

## 2. Store the token

The PAT goes into Splunk's encrypted credential store. It is never written to a
conf file.

```bash
$SPLUNK_HOME/bin/splunk cmd curl -k -u admin:<password> \
  https://localhost:8089/servicesNS/nobody/TA-airtable-auditlogs/storage/passwords \
  -d name=airtable_pat \
  -d password=<THE_PAT> \
  -d realm=airtable_auditlogs
```

## 3. Set the account ID and enable the input

Create `$SPLUNK_HOME/etc/apps/TA-airtable-auditlogs/local/inputs.conf`:

```ini
[airtable_auditlogs://prod]
disabled = 0
enterprise_account_id = entXXXXXXXXXXXXXX
initial_start_time = 2026-07-01T00:00:00Z
```

Everything else (interval, index, sourcetype, category filters, exclusions)
already has a working default in `default/inputs.conf`. Override only what you
need to change.

`initial_start_time` controls how far back the first run backfills. Maximum 180
days ago, that is Airtable's retention limit. Omit it to start from the
retention boundary.

## 4. Restart

```bash
$SPLUNK_HOME/bin/splunk restart
```

---

## Notes on the bundled pieces

**Index.** `airtable_audit` ships in `default/indexes.conf`. That applies if the
HF indexes locally. If the HF forwards to indexers, the index must also exist on
the indexers, this file will not create it there.

**Libraries.** Bundled in `lib/`, with compiled binaries stripped so they are
portable across architectures. If you hit an import error, rebuild on the HF:

```bash
pip install requests splunk-sdk -t $SPLUNK_HOME/etc/apps/TA-airtable-auditlogs/lib
```

---

## Verify

```
index=airtable_audit sourcetype=airtable:auditlog
| stats count by action
```

Input health:

```
index=_internal sourcetype=splunkd component=ExecProcessor "TA-airtable-auditlogs"
```

---

## Test credentials before enabling

Confirm the token and account ID work in isolation, so you are not debugging
auth and Splunk config at the same time:

```bash
curl "https://api.airtable.com/v0/meta/enterpriseAccounts/entXXXXXXXXXXXXXX/auditLogEvents?pageSize=5" \
  -H "Authorization: Bearer <THE_PAT>"
```

A 200 with an `events` array means you are clear.

---

## Things to get right

**Run one instance only.** Several HFs means several checkpoints and duplicated
events. Pin this input to one.

**Changing the category or event type filter invalidates the saved pagination
token.** Delete the checkpoint when you retune, or you will get
`INVALID_PAGINATION_TOKEN`. Checkpoints live in the input's checkpoint
directory, one JSON file per stanza. Deleting one forces a fresh start from
`initial_start_time`.

**Leave `exclude_event_types` alone.** `viewBase` and `viewShare` fire once per
user per base every 5 minutes and will dominate your license volume.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `HTTP 404 NOT_FOUND` | Wrong account ID, or token lacks enterprise access. Airtable returns 404 rather than 403 so it does not leak whether the account exists. |
| `HTTP 401` | Bad or revoked token |
| `INVALID_TIME_RANGE` | `initial_start_time` is more than 180 days ago |
| `INVALID_PAGINATION_TOKEN` | Stale checkpoint, or filters changed. Delete the checkpoint. |
| `ImportError` | Rebuild `lib/` on the HF, see above |
| No events, no errors | Filters too narrow, or genuinely no activity |
| Connection timeout | Egress to `api.airtable.com` blocked |
