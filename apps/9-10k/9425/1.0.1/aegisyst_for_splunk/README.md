# Aegisyst for Splunk

AI-Native Detection Engineering rules — automatically pulled from your Aegisyst
tenant into Splunk as scheduled searches.

**Version:** 1.0.0
**Author:** Aegisyst — https://aegisyst.com
**License:** Commercial — see https://aegisyst.com/terms
**Supported:** Splunk Enterprise 8.x/9.x, Splunk Cloud Platform, standalone
& search-head clustering

---

## What this app does

1. Authenticates to your Aegisyst tenant using an API key you mint in the
   Aegisyst UI.
2. Every 6 hours (configurable), pulls every **approved** or **deployed**
   Sigma rule you own, translated to Splunk SPL by Aegisyst's deterministic
   translator. Native SPL rules are returned as-is.
3. Writes each pulled rule payload to
   `$SPLUNK_HOME/var/log/splunk/aegisyst.log` so you can inspect what
   arrived and index it if you want an audit trail.
4. Ships a **Detection Status** dashboard that graphs rule counts, severity
   mix, and pull health.

## Setup

### 1. Get an API Key from Aegisyst
- Sign in to https://aegisyst.com and open **Settings → API Keys**.
- Click **Generate new key**, give it a name (e.g. "Prod Splunk cluster").
- Copy the raw key — it's shown exactly once. It looks like
  `sk_aegisyst_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.

### 2. Install the app in Splunk
- Splunk Enterprise: **Apps → Manage Apps → Install app from file** → select
  `aegisyst-for-splunk-1.0.0.spl` → **Upload**.
- Splunk Cloud (self-service): **Apps → Manage Private Apps → Install** and
  upload the same file.

### 3. Configure the API key
On the Splunk search head (or on one search-head cluster member), create
`local/aegisyst.conf` inside the app:

```
$SPLUNK_HOME/etc/apps/aegisyst_for_splunk/local/aegisyst.conf
```

with these contents:

```ini
[aegisyst]
api_key = sk_aegisyst_your_actual_key_here
aegisyst_api_url = https://aegisyst.com
```

Then reload the app config:

```
$SPLUNK_HOME/bin/splunk _internal call /services/apps/local/aegisyst_for_splunk/_reload -auth admin:<password>
```

On a **search-head cluster**, edit `local/aegisyst.conf` on the deployer
under `$SPLUNK_HOME/etc/shcluster/apps/aegisyst_for_splunk/local/` and push
the bundle:
```
splunk apply shcluster-bundle -target <captain-url>
```

### 4. Trigger the first pull
- The app schedules a pull every 6 hours automatically. To trigger a
  manual pull immediately:
  ```
  $SPLUNK_HOME/bin/splunk cmd python \
    $SPLUNK_HOME/etc/apps/aegisyst_for_splunk/bin/aegisyst_pull.py
  ```
- Tail the log to watch it happen:
  ```
  tail -f $SPLUNK_HOME/var/log/splunk/aegisyst.log
  ```
- Open the **Aegisyst for Splunk → Detection Status** dashboard to see the
  visual summary.

## Log format

Every rule pull produces one summary line + one line per rule:

```
2026-02-07 12:00:00 INFO aegisyst_pull pull start api_base=https://aegisyst.com
2026-02-07 12:00:01 INFO aegisyst_pull pull ok customer_id=<uuid> total=42 skipped=3
2026-02-07 12:00:01 INFO aegisyst_pull rule id=<uuid> name='PowerShell Download Cradle' severity=high techniques=T1059.001,T1105 spl='# PowerShell Download ⏎ index=* sourcetype=WinEventLog:* ⏎ | search ...'
```

If your Splunk indexes `_internal` (default), the dashboard queries this
directly. You can also search:

```
index=_internal source=*aegisyst.log rule
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No API key configured` | Create `local/aegisyst.conf` (see step 3). |
| `http=401 Invalid or revoked API key` | The key was revoked in Aegisyst. Mint a new one and update `local/aegisyst.conf`. |
| Nothing appears in the log | Trigger a manual pull (see step 4). Check `$SPLUNK_HOME/var/log/splunk/aegisyst.log` for errors. |
| Dashboard is empty | Make sure `_internal` isn't blocklisted from indexing on your deployment. |

## Support

- Portal: https://aegisyst.com
- Email: support@aegisyst.com
