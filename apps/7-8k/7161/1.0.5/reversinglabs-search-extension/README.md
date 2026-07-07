# ReversingLabs Search Extension for Splunk

The ReversingLabs Search Extension for Splunk is a Splunk Enterprise and Splunk Cloud compatible app that brings ReversingLabs TitaniumCloud threat intelligence directly into your Splunk searches. Using a custom `reversinglabs` search command, you can enrich any Splunk record containing file hashes, URLs, IP addresses, or domains with reputation data and file analysis results from TitaniumCloud.


## Requirements

- Splunk Enterprise, or Splunk Cloud
- A valid ReversingLabs TitaniumCloud account (username in `u/` format and password)
- Network connectivity from the Splunk server to `https://data.reversinglabs.com` — either directly or through a proxy


## Installation

Install the app through Splunk's standard app installation workflow:

1. In Splunk Web, go to **Apps → Manage Apps → Install app from file**.
2. Upload the `.tar.gz` package provided by ReversingLabs.
3. Restart Splunk if prompted.

After installation, a **"Set up now"** banner appears on the Splunk home page. Click it to open the setup page, or open it any time by clicking **ReversingLabs Search Extension** in the main app navigation menu.


## Configuring the app

The setup page has two independent sections. You must complete **TitaniumCloud credentials** before the search command will work. **Proxy configuration** is optional and only needed if your environment requires it.

---

### TitaniumCloud credentials

These are your ReversingLabs TitaniumCloud account credentials.

| Field | Description |
|-------|-------------|
| **Username** | Your TitaniumCloud username. It always starts with `u/`, for example `u/john.doe`. |
| **Password** | The password associated with the username above. |

Both fields are marked required (red border when empty). The **Save credentials** button is disabled until both fields are filled in.

Click **Save credentials**. The credentials are stored encrypted in Splunk's `passwords.conf` and are never written to disk in plain text. You are redirected to the Splunk search page after a successful save.

> **Updating credentials:** Open the setup page again at any time, enter the new username and password, and click **Save credentials**. The old entry is replaced automatically.

---

### Proxy configuration

If your Splunk server cannot reach `https://data.reversinglabs.com` directly, you can route TitaniumCloud API requests through an HTTP/HTTPS proxy. If your network uses TLS inspection with a private or self-signed certificate authority, you can also provide a custom CA certificate so that TLS verification succeeds.

Both fields are optional. You can fill in one or both, or leave both blank to use a direct connection with the default system CA bundle.

#### Step 1 — Enter the proxy URL (if required)

In the **Proxy URL** field, enter the full address of your proxy server including the scheme and port:

```
http://proxy.example.com:8080
```

```
https://proxy.example.com:8443
```

The same URL is applied to both HTTP and HTTPS traffic. Leave the field blank if no proxy is needed.

#### Step 2 — Provide a CA certificate (if required)

If TLS verification fails because the proxy or your network uses a certificate signed by a private CA, you must provide the CA certificate bundle in PEM format.

**Preparing the certificate file:**

1. Obtain the CA certificate (or certificate chain) from your network or security team. It must be in PEM format — a plain-text file that starts with `-----BEGIN CERTIFICATE-----`.
2. Copy the file to the **Splunk server** (the machine running Splunk, not your local workstation). A recommended location is:

   ```
   /etc/ssl/certs/corporate-ca-bundle.pem
   ```

   You can use any path that is stable and accessible to the Splunk process.

3. Make the file readable by the OS user that runs Splunk. On most Linux installations that user is `splunk`:

   ```bash
   chown splunk:splunk /etc/ssl/certs/corporate-ca-bundle.pem
   chmod 640 /etc/ssl/certs/corporate-ca-bundle.pem
   ```

   If you are unsure which user runs Splunk, check with:

   ```bash
   ps aux | grep splunkd | head -1
   ```

**Entering the path in the setup page:**

In the **Certificate path** field, enter the absolute path to the file on the Splunk server:

```
/etc/ssl/certs/corporate-ca-bundle.pem
```

> The path must point to a file on the **Splunk server**, not a path on your own machine. Relative paths are not supported.

#### Step 3 — Save the settings

Click **Save settings** under the Proxy configuration section. The values are written to the app's `reversinglabs.conf` configuration file and take effect on the next search command execution. No Splunk restart is required.

The setup page pre-fills these fields with the currently saved values each time you open it, so you can review or change them at any time.

#### Removing proxy or certificate settings

To remove a setting, open the setup page, clear the relevant field, and click **Save settings**. The extension will revert to a direct connection or the system CA bundle respectively.

---

## Using the app

The extension adds a `reversinglabs` custom search command that you append to any Splunk search. The command reads field values from each result record, queries TitaniumCloud, and appends threat intelligence fields to the record.

### Supported parameters

| Parameter | Data type | Description |
|-----------|-----------|-------------|
| `file_reputation_hash` | Field name | Field containing an MD5, SHA1, or SHA256 file hash. Returns threat classification and malware family information. |
| `file_analysis_hash` | Field name | Field containing an MD5, SHA1, or SHA256 file hash. Returns detailed static analysis results. |
| `network_reputaion_location` | Field name | Field containing a URL, IP address, or domain. Returns network reputation data. |

Only one parameter can be used per command invocation.

### Example queries

**File reputation lookup:**
```spl
index=tiscale container_hash=*
| reversinglabs file_reputation_hash=container_hash
```

**File analysis lookup:**
```spl
index=tiscale container_hash=*
| reversinglabs file_analysis_hash=container_hash
```

**Network reputation lookup (URL, IP, or domain):**
```spl
index=tiscale url_field=*
| reversinglabs network_reputaion_location=url_field
```

### Filtering to records that have the required field

Adding `field_name=*` before the command ensures only records that contain the field are passed to the command, preventing empty lookups:

```spl
index=main sha256=*
| reversinglabs file_reputation_hash=sha256
```

### Using with the TitaniumScale Dashboard app

The `tiscale` index is created automatically by the [ReversingLabs TitaniumScale Dashboard app for Splunk](https://splunkbase.splunk.com/app/4318). If you have that app installed and a TitaniumScale instance configured to forward records to `tiscale`, you can use the queries above without modification. The extension also works with any other index that contains the supported field types.


## Viewing application logs

The extension writes a structured log file to:

```
$SPLUNK_HOME/var/log/splunk/reversinglabs.log
```

This file is automatically monitored and indexed by Splunk into the `reversinglabs_logs` index. Each query command logs its start, completion, and any errors — including the proxy URL and certificate path in use. To search the logs:

```spl
index=reversinglabs_logs
```

To see only errors:

```spl
index=reversinglabs_logs log_level=ERROR
```

The log file rotates automatically at 25 MB and keeps the five most recent files.


## API query quota

Each Splunk record processed by the `reversinglabs` command counts as one API query against your TitaniumCloud quota. Use `field_name=*` filters and time range limits in your searches to control the number of records passed to the command.


## Questions and support

For questions and issues related to this app, contact ReversingLabs support at support@reversinglabs.com.