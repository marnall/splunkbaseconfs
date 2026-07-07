# Technical Add-on MS Defender Advanced Hunting

> **Note:** When upgrading from v0.1.x to v0.2.x, you must re-configure your credentials.

## 1. Overview

This add-on allows you to run Advanced Hunting queries (KQL) against Microsoft Defender APIs directly from Splunk search commands.

Microsoft offers three APIs for Advanced Hunting:

- Microsoft Defender for Endpoint
- Microsoft Defender XDR
- Microsoft Graph REST API

This add-on automatically detects which API endpoint your credentials are authorized for. If credentials for multiple APIs are configured, **Microsoft Defender for Endpoint** takes priority.

- [Microsoft Defender for Endpoint](https://learn.microsoft.com/en-us/defender-endpoint/microsoft-defender-endpoint?view=o365-worldwide)


## 2. Installation

1. Register an application in Microsoft Entra ID for one of the following APIs. **Microsoft Graph REST API is recommended.**
    - Microsoft Defender for Endpoint
        - [Create an app to access Microsoft Defender for Endpoint without a user](https://learn.microsoft.com/en-us/defender-endpoint/api/exposed-apis-create-app-webapp)
        - Grant `AdvancedQuery.Read.All` permission.
    - Microsoft Defender XDR
        - [Create an app to access Microsoft Defender XDR without a user](https://learn.microsoft.com/en-us/defender-xdr/api-create-app-web?view=o365-worldwide)
        - Grant `AdvancedHunting.Read.All` permission.
    - Microsoft Graph REST API
        - [Get access without a user](https://learn.microsoft.com/en-us/graph/auth-v2-service?tabs=http)
        - Grant `ThreatHunting.Read.All` permission.
2. Note your **Directory (Tenant) ID**, **Application (Client) ID**, and **Client Secret**.
3. Open the Splunk configuration page: **App → Configuration → Account Settings**.
4. Enter the credential name, Tenant ID, Client ID, and Client Secret.

### 2.1 Account Settings

| Label | Description |
| --- | --- |
| Account name | Required. A unique name for this credential. |
| Client ID | Required. Application (Client) ID. |
| Client Secret | Required. Client Secret. |
| Tenant ID | Required. Directory (Tenant) ID. |
| Default Credential | Optional. If checked, this credential is used by default. |
| Request read timeout (seconds) | Optional. Read timeout for API requests. Default: 60s. |
| Request connection timeout (seconds) | Optional. Connection timeout for API requests. Default: 10s. |
| Request retry num | Optional. Number of retries on server errors (5xx). Default: 0. |

## 3. Usage

| Command | Type | Description |
| --- | --- | --- |
| advhunt | Generating Command | Fetch data using an Advanced Hunting query. |

### 3.1 advhunt command

Returns the results of an Advanced Hunting query.

| Option | Description |
| --- | --- |
| query | Required. The Advanced Hunting query (KQL). |
| renew | Optional. Set to `True` to force an access token renewal. |
| cred | Optional. Credential name to use. Omitted: default credential / Single: `cred="cred1"` / Multiple: `cred="cred1,cred2"` / All: `cred="all"` |

**Example 1** — Backslash in query

To search for a path containing `\`, use `\\\\\\\` or `\\\x5c` in SPL.

```
| advhunt query="DeviceFileEvents
  | where Timestamp > ago(1d)
  | where FolderPath matches regex 'C:\\\x5cUsers' or FolderPath matches regex 'C:\\\\\\\Users'
  | project Timestamp, DeviceId, DeviceName, ActionType, FolderPath, FileName"
| spath input=_raw
```

**Example 2** — Force token renewal

```
| advhunt renew=True query="AlertInfo
  | where Timestamp > ago(3d)
  | limit 2"
| spath input=_raw
```

**Example 3** — Use previous SPL results as query input

```
| makeresults
| eval ActionType = "AntivirusReport,HogeReport"
| makemv delim="," ActionType
| mvexpand ActionType
| mvcombine ActionType
| eval query = "('" . mvjoin(ActionType, "', '") . "')"
| map search="| advhunt query=\"DeviceEvents | where ActionType has_any $query$ \" | spath input=_raw | table *"
```

**Example 4** — Query multiple tenants

```
| advhunt cred="tenant1_cred,tenant2_cred" query="AlertInfo"
```

**Example 5** — Subsearch pattern

```
| advhunt [| makeresults
  | eval query = "DeviceFileEvents
    | where Timestamp > ago(1d)
    | limit 1"
  | return query]
| spath
```

## 4. Notes

### Required Privileges

Users need the following Splunk privileges:
- `list_storage_passwords`
- `admin_all_objects`

If you do not want to grant `admin_all_objects`, there are three workarounds:

1. Update `local.meta` to grant `edit_storage_passwords` to the user:
    ```
    [passwords]
    access = read : [*], write : [*]
    ```
2. Schedule a report (run by a user with `admin_all_objects`) to refresh the access token every 30 minutes. Regular users only need `list_storage_passwords` to use the cached token.
3. Do nothing. Without `admin_all_objects`, the add-on will request a new access token on every `advhunt` call, which increases latency.

### Differences Between API Endpoints

- **Microsoft Defender for Endpoint** does not support all schemas (e.g., `AlertInfo`, `AlertEvidence`).

### API Rate Limits

- Microsoft Defender for Endpoint: [Limitations](https://learn.microsoft.com/en-us/defender-endpoint/api/run-advanced-query-api?view=o365-worldwide#limitations)
- Microsoft Defender XDR: [Quotas and resource allocation](https://learn.microsoft.com/en-us/defender-xdr/api-advanced-hunting?view=o365-worldwide#quotas-and-resource-allocation)
- Microsoft Graph security API: [Quotas and resource allocation](https://learn.microsoft.com/en-us/graph/api/resources/security-api-overview?view=graph-rest-1.0#quotas-and-resource-allocation)

## 5. Debugging

Check the internal Splunk log:

```
index=_internal source="*advanced_hunting*" NOT "__init__"
```
