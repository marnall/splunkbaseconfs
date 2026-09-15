# Invicti Platform Add-on for Splunk

Collects vulnerability findings from the [Invicti Platform](https://www.invicti.com/)
Inventory API and indexes them in Splunk as JSON events.

Each vulnerability is written as a single self-contained event under the
sourcetype `invicti:platform:vulnerability`, so every field in the API response
is available for search without additional configuration.

- **Add-on ID:** `TA-invicti-platform`
- **Version:** 1.0.0
- **Sourcetype:** `invicti:platform:vulnerability`
- **Compatibility:** Splunk Enterprise 9.0 or later, and Splunk Cloud
- **Vendor support:** support@invicti.com

---

## Requirements

- Splunk Enterprise 9.0 or later, or Splunk Cloud.
- An Invicti Platform account with API access.
- An **API token** for the Invicti Platform API. The add-on sends it in the
  `X-Auth` header of every request. The token is stored encrypted by Splunk.
- Network access from the Splunk instance running the input to
  `https://platform.invicti.com` (or your Invicti Platform base URL). An
  outbound HTTP/HTTPS/SOCKS proxy can be configured if required.

## Where to install

Install on a **search head** (single instance, search head cluster, or a heavy
forwarder used for data collection). The add-on only runs a modular input and
does not require an indexer-side component.

---

## Configuration

### 1. Add an account

**Apps → Invicti Platform Add-on for Splunk → Configuration → Account → Add**

| Field | Description |
|---|---|
| Account name | A friendly label for this account, e.g. `prod`. |
| Base URL | Base URL of the Invicti Platform API. Default: `https://platform.invicti.com` |
| API Token | The value sent in the `X-Auth` header. Stored encrypted. |

### 2. (Optional) Proxy and logging

The **Proxy** tab configures an outbound proxy (HTTP, HTTPS, SOCKS4, SOCKS5)
with optional credentials. The **Logging** tab sets the add-on log level;
`INFO` is the default and is sufficient for normal operation.

### 3. Create an input

**Apps → Invicti Platform Add-on for Splunk → Inputs → Create New Input →
Invicti Vulnerabilities**

| Field | Required | Default | Description |
|---|---|---|---|
| Name | Yes | — | A unique name for this data input. |
| Interval | Yes | 300 | Seconds between collection runs (minimum 60). |
| Index | Yes | default | Destination index. |
| Invicti Account | Yes | — | The account configured in step 1. |
| Asset ID | No | — | Collect only vulnerabilities belonging to this asset. |
| Origin ID | No | — | Collect only vulnerabilities belonging to this origin. |
| Page size | No | 50 | Vulnerabilities requested per API page (1–200). |

---

## How collection works

The input calls `/api/inventory/v1/vulnerabilities` and pages through the
results, writing one event per vulnerability.

**Incremental collection.** After each run the input stores the highest
`lastSeen` timestamp it observed in a per-input checkpoint. The next run
requests only newer records using `lastSeen=<timestamp>&lastSeenOperator=after`.
The first run therefore performs a full collection, and subsequent runs are
incremental.

**Event time.** The event timestamp is taken from the vulnerability's
`lastSeen` field, not from collection time. Events therefore appear on the
timeline when the finding was last seen by Invicti.

**Retries.** Transient failures (HTTP 429, 500, 502, 503, 504, and network
errors) are retried up to three times with backoff, honouring `Retry-After`
when the API sends it. Non-retryable responses are logged with the response
body for diagnosis and the run ends without advancing the checkpoint.

---

## Searching the data

```spl
index=* sourcetype="invicti:platform:vulnerability"
| stats count by severity
```

```spl
index=* sourcetype="invicti:platform:vulnerability" severity=Critical
| table _time, name, target, cvssScore, lastSeen
```

`INDEXED_EXTRACTIONS = json` is configured for the sourcetype, so all JSON
keys returned by the API are available as fields.

---

## Troubleshooting

The add-on writes a dedicated log file per input:

```
$SPLUNK_HOME/var/log/splunk/ta-invicti-platform_invicti_vulnerabilities_<input-name>.log
```

Or search it from Splunk Web:

```spl
index=_internal source=*ta-invicti-platform_invicti_vulnerabilities_*.log
```

| Symptom | What to check |
|---|---|
| No events at all | Confirm the input is enabled under **Settings → Data inputs → Invicti Vulnerabilities**, and check the input log for a `GENERAL_ERROR` line. |
| `has no API token configured` | Re-enter the API token on the account under **Configuration → Account**. |
| `Invicti API error status=401` | The API token is invalid or expired. |
| `Invicti API error status=403` | The token lacks permission for the Inventory API. |
| Network or timeout errors | Verify outbound access to the Base URL, and configure the **Proxy** tab if egress requires one. |
| Only old events appear | Event time comes from `lastSeen`. Widen the search time range, or use `earliest=0` to confirm data is present. |
| Need to re-collect everything | Reset the checkpoint by removing the input's entry from the KV Store collection `ta-invicti-platform_invicti_vulnerabilities_ckpt`, then let the input run again. |

Set the log level to `DEBUG` under **Configuration → Logging** to record the
query parameters sent for each page.

---

## Release notes

### 1.0.0

Initial release.

- Modular input collecting vulnerabilities from the Invicti Platform Inventory API.
- Incremental collection using a per-input `lastSeen` checkpoint.
- Optional filtering by Asset ID and Origin ID, configurable page size.
- Proxy support (HTTP, HTTPS, SOCKS4, SOCKS5) with optional authentication.
- Encrypted storage of the API token.
- Configurable log level with a dedicated log file per input.

---

## Support

For questions about this add-on or the Invicti Platform API, contact
Invicti Security at support@invicti.com.

Licensed under the Apache License, Version 2.0. See the `LICENSE` file
included with the add-on.
