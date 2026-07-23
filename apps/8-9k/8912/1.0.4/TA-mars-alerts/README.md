# TA-mars-alerts — "Send to Mars" custom alert action

A Splunk app (technology add-on) that forwards a saved search's alert to
Mars ISE in **one outbound delivery**. It runs inside Splunk, so it reads
the full result set, the SPL, and the saved search's configured severity
locally and pushes them to the Mars webhook. Because everything is sent in
the push, Mars doesn't make a REST callback to enrich the alert, and there
are **no `| eval severity=...` SPL edits** to maintain.

## Payload contract (app → Mars)

The handler POSTs this JSON to the Mars webhook with
`Authorization: Bearer <token>`. Mars distinguishes it from the stock
webhook structurally: a `results` **list** plus a `spl` field (the stock
webhook has a singular `result` object and neither field).

```json
{
  "schema_version": "splunk-app/v1",
  "sid": "scheduler_...__search__MyDetection_at_1778...",
  "search_name": "My Detection",
  "app": "search",
  "owner": "analyst@corp.com",
  "results_link": "https://<stack>/app/search/...",
  "spl": "index=main sourcetype=auth action=failure | stats count by user",
  "alert_severity": "4",
  "description": "Brute-force login detector",
  "cron_schedule": "*/5 * * * *",
  "earliest_time": "-15m",
  "latest_time": "now",
  "result_count": 42,
  "results_truncated": false,
  "results": [ { "_time": "1778...", "user": "...", "count": "17" } ]
}
```

`alert_severity` is Splunk's 1–5 string scale (Mars maps it: 1–2→low,
3→medium, 4→high, 5→critical). It is the saved search's configured
`alert.severity` unless the action's **Severity** dropdown is set to an
explicit override (the dropdown defaults to *Auto*).

`result_count` is the true match total. `results` carries every matching
row up to a cap of 200; when the match set is larger, the first 200 ride
along and `results_truncated` is `true`.

## Build

```bash
cd vendor_apps/splunk
./build.sh                 # → dist/TA-mars-alerts.spl
```

## Install (Splunk Enterprise or a private-app-enabled Cloud stack)

Apps → Manage Apps → **Install app from file** → upload
`dist/TA-mars-alerts.spl`. Custom alert actions install freely on Splunk
Enterprise; Splunk Cloud requires the stack to allow private/unvetted app
upload (AppInspect vetting for self-service install is a follow-up).

## Configure (once)

After install, Splunk opens the app's setup page (or open it from
**Manage Apps → Mars Alert Forwarding → Set up**). Enter:

- **Mars webhook URL** — `https://<your-mars-host>/api/v1/webhooks/alerts/splunk`
- **Mars webhook token** — issued in Mars under *Settings → Alert sources → Splunk*

The setup page is a Cloud-vetting-clean configuration view (no `setup.xml`,
which Splunk Cloud prohibits): it writes the URL to `mars_alerts.conf` and
the token to `storage/passwords` (realm `TA-mars-alerts`, username
`mars_webhook_token`), encrypted, sent as a Bearer token on each delivery.

The token can also be set directly against the REST API if you prefer:

```bash
curl -k -u admin:<pw> https://<splunk-host>:8089/servicesNS/nobody/TA-mars-alerts/storage/passwords \
  -d name=mars_webhook_token -d realm=TA-mars-alerts -d password=<mars-token>
```

## Enable per saved search

Edit a saved search → **Edit → Edit Alert → Trigger Actions → Add Actions
→ Send to Mars**. Save. On the next trigger, the full alert is forwarded.

## Isolated testing

- **Step 2 (installs + shows up):** install the `.spl`, confirm the setup
  view persists URL + token, and confirm **Send to Mars** appears in a
  saved search's Trigger Actions list.
- **Step 3 (correct payload):** point the webhook URL at a throwaway echo
  endpoint (e.g. `webhook.site`) instead of Mars, trigger a saved search,
  and confirm the captured JSON matches the contract above — **all** rows
  present and the correct `alert_severity`.
- **Step 4 (E2E):** point the URL at the real Mars endpoint and confirm
  Mars dispatches the alert with no REST callback.

The handler's pure logic (gzipped-CSV parsing, payload assembly) has a
dependency-free unit test:

```bash
python3 -m unittest discover -s vendor_apps/splunk/TA-mars-alerts/tests
```
