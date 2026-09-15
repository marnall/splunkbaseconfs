# Qualys Universal Technology Add-on (TA) for Splunk

## Overview

The Qualys Universal Technology Add-on (TA) for Splunk collects vulnerability and web application security data from the Qualys Cloud Platform. The add-on supports two data collection modules -- **VMDR** (Vulnerability Management, Detection and Response) and **WAS** (Web Application Scanning) -- and ingests scan lists, scan reports, scan summaries, host-level detection results, and web application findings into Splunk for search, correlation, and visualization.

## Compatibility

* Splunk version: 9.2.x, 9.3.x, 9.4.x and 10.0.x
* Python version: Python 3
* OS Support: Linux (CentOS, Ubuntu, RHEL) and Windows
* Browser Support: Chrome, Firefox and Safari

## Prerequisites

* A Qualys Cloud Platform subscription with API access enabled
* API credentials (username/password for Basic auth, or client ID/secret for OIDC auth)
* Network connectivity from the Splunk instance to your Qualys API server

## Installation

**Installing from file**

1. Log in to the Splunk Web UI and navigate to **Apps | Manage Apps**.
2. Click `Install app from file`.
3. Click `Choose file` and select the `TA-Qualys-Cloud-Connector` installation file (`.tgz`).
4. Click `Upload`.
5. Restart Splunk if prompted.

**Distributed environments:** The add-on should be installed on a Heavy Forwarder for data collection and on a Search Head for search-time field extractions.

## Configuration

### Step 1: Create a Qualys Account

1. Log in to the Splunk Web UI and open the **Qualys Universal Technology Add-on (TA) for Splunk**.
2. Navigate to the **Configuration** page.
3. Click the **Account** tab, then click `Add`.
4. Complete the form with the required settings described in the table below and click `Add`.

| Account Parameter     | Mandatory or Optional | Description                                                                 |
| --------------------- | --------------------- | --------------------------------------------------------------------------- |
| Account Name          | Mandatory             | A unique name to identify this Qualys account                               |
| API Server            | Mandatory             | The Qualys API server URL (e.g. `qualysapi.qualys.com`)                     |
| Authentication Type   | Mandatory             | `basic` (username/password) or `oidc` (client credentials)                  |
| Username              | Mandatory (basic)     | Qualys platform username                                                    |
| Password              | Mandatory (basic)     | Qualys platform password                                                    |
| Client ID             | Mandatory (oidc)      | OAuth 2.0 Client ID for OIDC authentication                                |
| Client Secret         | Mandatory (oidc)      | OAuth 2.0 Client Secret for OIDC authentication                            |

### Step 2: Configure Proxy Settings (Optional)

1. Navigate to the **Configuration** page and click the **Proxy** tab.
2. Complete the form if your environment requires a proxy to reach the Qualys API.

| Proxy Parameter | Mandatory or Optional | Description                                              |
| --------------- | --------------------- | -------------------------------------------------------- |
| Enable Proxy    | Optional              | Enable or disable proxy settings                         |
| Proxy Type      | Mandatory             | The proxy type (HTTP, SOCKS4, SOCKS5)                    |
| Proxy Host      | Mandatory             | Host or IP address of the proxy server                   |
| Proxy Port      | Mandatory             | Port number of the proxy server                          |
| Proxy Username  | Optional              | Username for proxy authentication                        |
| Proxy Password  | Optional              | Password for proxy authentication                        |

### Step 3: Configure Logging and Additional Settings (Optional)

1. Navigate to the **Configuration** page.
2. On the **Logging** tab, set the desired log level (default: `INFO`).
3. On the **Additional Settings** tab, configure optional parameters:

| Setting        | Default | Description                                                        |
| -------------- | ------- | ------------------------------------------------------------------ |
| Preserve XML/JSON Response  | false   | Save raw API responses to disk for debugging                       |
| API Timeout    | 120     | Timeout in seconds for Qualys API requests                         |

### Step 4: Create Data Inputs

Navigate to the **Inputs** page and click **Create New Input**. Select the input type from the dropdown menu.

---

#### VMDR Input

Collects VMDR scan lists, scan reports, scan summaries, and host-level detection results.

| Input Parameter              | Mandatory or Optional | Description                                                                                      |
| ---------------------------- | --------------------- | ------------------------------------------------------------------------------------------------ |
| Name                         | Mandatory             | A unique name to identify this input                                                             |
| Interval                     | Mandatory             | Collection interval in seconds (default: 3600)                                                   |
| Index                        | Mandatory             | Splunk index to store the data                                                                   |
| Account                      | Mandatory             | The Qualys account to use for data collection                                                    |
| Start Date                   | Optional              | Date (RFC 3339) from which to begin collecting data. If omitted, defaults to 30 days ago         |
| Detection Truncation Limit   | Optional              | Maximum number of detections per host (default: 1000)                                            |
| Use Multi-Threading          | Optional              | Enable concurrent API calls for faster collection                                                |
| Number of Threads            | Optional              | Number of concurrent threads (default: 2)                                                        |

---

#### WAS Input

Collects WAS scans, scan reports, and web application findings.

| Input Parameter              | Mandatory or Optional | Description                                                                                      |
| ---------------------------- | --------------------- | ------------------------------------------------------------------------------------------------ |
| Name                         | Mandatory             | A unique name to identify this input                                                             |
| Interval                     | Mandatory             | Collection interval in seconds (default: 3600)                                                   |
| Index                        | Mandatory             | Splunk index to store the data                                                                   |
| Account                      | Mandatory             | The Qualys account to use for data collection                                                    |
| Start Date                   | Optional              | Date (RFC 3339) from which to begin collecting data. If omitted, defaults to 30 days ago         |
| Use Multi-Threading for WAS  | Optional              | Enable concurrent API calls for faster collection                                                |
| Number of Threads for WAS    | Optional              | Number of concurrent threads (default: 2)                                                        |

## Sourcetypes

The add-on writes events with the following sourcetypes:

### WAS Sourcetypes

| Sourcetype                | Description                                         |
| ------------------------- | --------------------------------------------------- |
| `qualys:was:scan`         | WAS scan metadata                                   |
| `qualys:was:scan_report`  | Detailed WAS scan report data                       |
| `qualys:was:findings`     | WAS findings in JSON format                         |
| `qualys:wasFindings`      | WAS findings in key-value format (legacy)           |

### VMDR Sourcetypes

| Sourcetype                       | Description                                    |
| -------------------------------- | ---------------------------------------------- |
| `qualys:vmdr:scan_list`          | VMDR scan list metadata                        |
| `qualys:vmdr:scan_summary`       | VMDR scan summary with header/trailer fields   |
| `qualys:vmdr:scan_host_results`  | VMDR per-host detection results                |
| `qualys:vmdr:scan_report`        | Raw VMDR scan report data                      |

## Source Naming Convention

Events are ingested with a dynamic `source` field following this pattern:

```
qualys_<input_type>_<account_name>
```

Examples:
- `qualys_vmdr_my_qualys_account`
- `qualys_was_production_account`

## Search Examples

**View WAS scan data:**

```
index=<your_index> sourcetype="qualys:was:scan"
```

**View WAS findings:**

```
index=<your_index> sourcetype="qualys:was:findings"
```

**View VMDR scan list:**

```
index=<your_index> sourcetype="qualys:vmdr:scan_list"
```

**View VMDR host-level results:**

```
index=<your_index> sourcetype="qualys:vmdr:scan_host_results"
```

**Filter by account:**

```
index=<your_index> source="qualys_was_my_account"
```

## Checkpointing

The add-on uses Splunk KV Store for checkpointing to ensure data is not duplicated between collection runs. Checkpoints track the last successful collection timestamp for each input.

The KV Store collection used is `TA_Qualys_Cloud_Connector_checkpointer`.

**Viewing checkpoints:**

```
| inputlookup TA_Qualys_Cloud_Connector_checkpointer
```

**Deleting a specific checkpoint:**

```bash
curl -k -u admin:<password> -X DELETE \
  "https://<splunk_host>:8089/servicesNS/nobody/TA-Qualys-Cloud-Connector/storage/collections/data/TA_Qualys_Cloud_Connector_checkpointer/<url_encoded_key>"
```

**Deleting all checkpoints:**

```bash
curl -k -u admin:<password> -X DELETE \
  "https://<splunk_host>:8089/servicesNS/nobody/TA-Qualys-Cloud-Connector/storage/collections/data/TA_Qualys_Cloud_Connector_checkpointer"
```

## Troubleshooting

### No data is being collected

**Step 1: Validate Account Configuration**

1. Open the **Configuration** page and verify that a Qualys account has been added.
2. Verify the API Server URL, authentication type, and credentials are correct.

**Step 2: Validate Input Configuration**

1. Open the **Inputs** page.
2. Verify that a VMDR or WAS input has been created and is enabled.

**Step 3: Check logs for more information**

For Splunk on-premises:

1. Open a terminal on your Splunk server.
2. Search the log files for errors:

```bash
cat $SPLUNK_HOME/var/log/splunk/ta_qualys_cloud_connector_*.log | grep -A 10 ERROR
```

Via Splunk search:

```
index=_internal source=*ta_qualys_cloud_connector*.log* ERROR
```

### Common Errors

| Error Message                    | Possible Cause                                      | Resolution                                              |
| -------------------------------- | --------------------------------------------------- | ------------------------------------------------------- |
| `kvstore_unavailable_error`      | KV Store is not ready                               | Wait for KV Store to initialize; check Splunk status    |
| `invalid_start_date`             | Malformed start_date in input configuration         | Use RFC 3339 format (e.g. `2026-01-01T00:00:00Z`)      |
| `broken_pipe`                    | Splunk sent a termination signal during collection  | Normal during restarts; data will resume on next run    |
| Authentication failures          | Invalid credentials or expired token                | Verify account credentials on the Configuration page    |

## Uninstall and Cleanup

1. Remove `$SPLUNK_HOME/etc/apps/TA-Qualys-Cloud-Connector`
2. Remove logs: `$SPLUNK_HOME/var/log/splunk/ta_qualys_cloud_connector_*.log`
3. (Optional) Delete KV Store checkpoint data using the curl command above.
4. Restart the Splunk instance to reflect the changes in the UI.

## Support

For issues or questions, please contact Qualys Support.

**Copyright (c) 2026 Qualys, Inc. All rights reserved.**