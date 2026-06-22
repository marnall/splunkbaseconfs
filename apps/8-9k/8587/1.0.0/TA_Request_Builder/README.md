# Request Builder — TA for Splunk

> **Make outbound HTTP/HTTPS API calls directly from SPL using the `| req` custom search command.**

Request Builder adds a `| req` streaming command to your Splunk search pipeline. Run REST calls, enrich events with live API data, trigger webhooks, or integrate with any external system — all without leaving Splunk.

---

## Details

### What It Does

The `| req` command performs an HTTP or HTTPS request for every event that flows through it. Request parameters (URL, method, headers, body, cookies, timeout, SSL settings) can be supplied as SPL arguments **or** as event fields, giving you full control from within your search.

On success each event is enriched with:

| Field | Description |
|---|---|
| `status_code` | HTTP status code returned by the server |
| `response` | Full response body as text |
| `response_headers` | JSON string of all response headers |
| `ssl_verify` | Effective SSL verification setting (`true`/`false`) |

On failure an `error` field is added with the exception message.

### Authentication

Credentials are stored in **Splunk Storage Passwords** (Settings → Passwords) and referenced by `realm` + `identity` — they never appear in plain text in your searches.

| `auth_type` | Behaviour |
|---|---|
| `basic` _(default)_ | HTTP Basic Auth (`username:password`) |
| `bearer` | Adds `Authorization: Bearer <password>` header |
| `apikey` | Adds `<api_key_header>: <password>` header (default header name: `x-api-key`) |

### Command Syntax

```
| req
    [url=<string>]
    [identity=<string>]
    [realm=<string>]
    [auth_type=basic|bearer|apikey]
    [api_key_header=<string>]
```

### Event Fields Read by the Command

| Field | Required | Default | Description |
|---|---|---|---|
| `url` | Yes* | — | Target URL (`*` required if not passed as argument) |
| `method` | No | `GET` | HTTP method (GET, POST, PUT, DELETE, …) |
| `headers` | No | `{}` | JSON object of custom HTTP headers |
| `data` | No | — | Request body (JSON string or plain text) |
| `cookies` | No | `{}` | JSON object of cookies |
| `verify` | No | `true` | SSL certificate verification (`true`/`false`/`1`/`0`/`yes`/`no`) |
| `timeout` | No | `15` | Timeout in seconds |

### Examples

**Simple GET request**
```spl
| makeresults | eval url="https://httpbin.org/get" | req
```

**POST with JSON body and custom header**
```spl
| makeresults
| eval url="https://httpbin.org/post",
       method="POST",
       data="{\"key\":\"value\"}",
       headers="{\"Content-Type\":\"application/json\"}"
| req
```

**Bearer token authentication using stored credentials**
```spl
| makeresults | eval url="https://api.example.com/data"
| req realm=my_realm identity=my_user auth_type=bearer
```

**API key authentication with a custom header name**
```spl
| makeresults | eval url="https://api.example.com/v1/assets"
| req realm=my_realm identity=api_key auth_type=apikey api_key_header="X-API-Key"
```

**Enrich search results with live data from an external API**
```spl
index=main sourcetype=my_app
| table host ip
| eval url="https://ipinfo.io/" . ip . "/json"
| req
| spath output=geo_country input=response path=country
```

**Trigger an external webhook from a Splunk alert action (via saved search)**
```spl
index=_internal log_level=ERROR
| stats count by host
| where count > 10
| eval url="https://hooks.example.com/alert",
       method="POST",
       headers="{\"Content-Type\":\"application/json\"}",
       data="{\"host\":\"" . host . "\",\"error_count\":" . count . "}"
| req
```

---

## Installation

### Prerequisites

- Splunk Enterprise 8.x or later, **or** Splunk Cloud
- Python 3 (the bundled Splunk Python 3 interpreter is used automatically)
- The `requests` and `certifi` Python packages — both are included in Splunk's standard Python distribution and in the `lib/` directory of this add-on

### Install from Splunkbase

1. Log in to your Splunk instance as an administrator.
2. Go to **Apps → Find More Apps**.
3. Search for **Request Builder** and click **Install**.
4. Restart Splunk when prompted.

### Install Manually (sideload)

1. Download the latest release archive (`.tar.gz` / `.spl`) from Splunkbase or the GitHub Releases page.
2. In Splunk Web go to **Apps → Manage Apps → Install app from file**.
3. Upload the archive and check **Upgrade app** if replacing an existing version.
4. Restart Splunk when prompted.

### Install via CLI

```bash
$SPLUNK_HOME/bin/splunk install app TA_Request_Builder.tar.gz \
    -auth admin:<password>
$SPLUNK_HOME/bin/splunk restart
```

### Post-Installation: Storing Credentials

To use authentication, add credentials in Splunk Storage Passwords:

1. Navigate to **Settings → Passwords → Add new**.
2. Enter the **Realm**, **Username** (identity), and **Password**.
3. Reference them in `| req` with `realm=<realm> identity=<username>`.

No other configuration is required. The command is immediately available in the Search & Reporting app as `| req`.

---

## Troubleshooting

### The `req` command is not found

- Confirm the add-on is installed and enabled: **Apps → Manage Apps** — the app status must be **Enabled**.
- Restart Splunk after installation.
- Check `$SPLUNK_HOME/var/log/splunk/splunkd.log` for Python import errors related to `request_builder.py`.

### `error` field appears on events instead of a response

The error message is written to the `error` field on the event. Common causes:

| Error message pattern | Likely cause | Fix |
|---|---|---|
| `ConnectionError` / `Failed to establish a new connection` | Target host unreachable | Verify the URL and that Splunk's outbound network access allows the destination |
| `SSLError` | Certificate verification failure | Set `verify=false` for internal/self-signed endpoints, **or** add the CA certificate to the system trust store |
| `Timeout` | Request exceeded the timeout window | Increase the `timeout` field value (e.g., `eval timeout=30`) |
| `JSONDecodeError` (in headers/cookies) | Malformed JSON string | Validate the JSON with `| eval _check=json_valid(headers)` before calling `| req` |
| `No module named 'requests'` | Python dependency missing | Re-install the add-on; the `lib/` directory should contain `requests` and `certifi` |

### Authentication not working

- Verify the **realm** and **identity** values exactly match what is stored in Settings → Passwords (they are case-sensitive).
- For `auth_type=bearer`, the **password** stored in Storage Passwords is used as the token value.
- For `auth_type=apikey`, the **password** is used as the key value; the header name defaults to `x-api-key` unless `api_key_header` is set.

### SSL verification errors on internal endpoints

Add `verify=false` to the event field or set `eval verify="false"` before calling `| req`. For production environments, it is recommended to add the internal CA certificate to the Splunk host's trust store instead.

### Checking logs

```spl
index=_internal sourcetype=splunkd source=*python_modular_input*
| search message="*request_builder*"
```

Or check the Python search command logs directly:

```spl
index=_internal sourcetype=splunkd (component=SearchOperator OR component=ExecProcessor)
| search message="*req*" OR message="*request_builder*"
```
