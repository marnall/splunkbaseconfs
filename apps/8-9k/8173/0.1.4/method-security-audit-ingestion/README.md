# Method Security Audit Ingestion App for Splunk

> The **Method Security Audit Ingestion App for Splunk** uses the Method Security Audit API to fetch audit events from the Method Platform into Splunk, enabling comprehensive monitoring and analysis of security events.

## Overview

This application allows you to automatically ingest audit events from the Method Security Platform into your Splunk environment. With this integration, you can:

- Automatically feed Method Security audit data into Splunk for centralized monitoring
- Proactively monitor for security issues and access patterns
- Create custom dashboards and alerts based on Method audit events
- Maintain compliance and audit trails for your Method Platform usage

## Features

- **Automated Collection**: Scheduled collection of audit events via the Method Security API
- **Checkpoint Management**: Tracks the last collected event to prevent duplicates
- **Pagination Support**: Handles large volumes of audit data efficiently
- **OAuth 2.0 Authentication**: Secure authentication using client credentials
- **Flexible Configuration**: Configurable collection intervals and time ranges

## Prerequisites

- Splunk Enterprise 8.0+ or Splunk Cloud
- Python 3.7+
- Method Security account with API access
- Method Security OAuth credentials (Client ID and Client Secret)

## Installation

### For On-Premises Splunk

1. Download the app package from SplunkBase or the releases page
2. Install via Splunk Web:
   - Navigate to **Apps** > **Manage Apps**
   - Click **Install app from file**
   - Upload the package and click **Upload**
3. Restart Splunk if prompted

### For Splunk Cloud

1. Create a support ticket or follow your organization's process for installing custom apps
2. Provide the app package to your Splunk Cloud administrator

## Configuration

### Step 1: Obtain Method Security API Credentials

1. Log into your Method Security Platform
2. Navigate to **Settings** > **API Access** (or contact your Method Security administrator)
3. Create a new OAuth application or service account
4. Note your **Client ID** and **Client Secret**
5. Note your **API Base URL** (typically `https://api.method.security` or your custom domain)

### Step 2: Configure the Input

#### Option A: Via Splunk Web (inputs.conf.spec)

1. Navigate to **Settings** > **Data Inputs**
2. Find **Method Audit Logs** in the list of available inputs
3. Click **New** to create a new input
4. Fill in the configuration:
   - **Name**: A unique name for this input (e.g., `method_production_audit`)
   - **Interval**: Collection interval in seconds (recommended: 300 for 5 minutes)
   - **Index**: Target index for events (default: `main`, recommended: `method_audit`)
   - **Start Time**: Initial collection start time in format `YYYY-MM-DD HH:MM:SS` (e.g., `2025-01-01 00:00:00`)
   - **Base URL**: Your Method Security API base URL (e.g., `https://api.method.security`)
   - **Client ID**: Your OAuth Client ID
   - **Client Secret**: Your OAuth Client Secret
5. Click **Save**

#### Option B: Via Configuration File (inputs.conf)

Create or edit `$SPLUNK_HOME/etc/apps/method-security-audit-ingestion/local/inputs.conf`:

```ini
[method_audit_logs://method_production_audit]
interval = 300
index = method_audit
sourcetype = method:audit
start_time = 2025-01-01 00:00:00
base_url = https://example.method.delivery
client_id = your_client_id_here
client_secret = your_client_secret_here
disabled = 0
```

**Important**: Never commit the `local/inputs.conf` file with credentials to version control.

### Step 3: Create the Target Index (Optional but Recommended)

For better organization, create a dedicated index for Method audit events:

1. Navigate to **Settings** > **Indexes**
2. Click **New Index**
3. Set **Index Name** to `method_audit`
4. Configure retention and size settings as needed
5. Click **Save**

## Configuration Parameters

| Parameter       | Required | Description                       | Default   | Example                           |
| --------------- | -------- | --------------------------------- | --------- | --------------------------------- |
| `name`          | Yes      | Unique identifier for this input  | -         | `method_production_audit`         |
| `interval`      | Yes      | Collection interval in seconds    | 300       | `300` (5 minutes)                 |
| `index`         | Yes      | Target Splunk index               | `default` | `method_audit`                    |
| `start_time`    | Yes      | Initial start time for collection | -         | `2025-01-01 00:00:00`             |
| `base_url`      | Yes      | Method Security API base URL      | -         | `https://example.method.delivery` |
| `client_id`     | Yes      | OAuth Client ID                   | -         | `client_abc123...`                |
| `client_secret` | Yes      | OAuth Client Secret               | -         | `secret_xyz789...`                |

## Event Format

Events are ingested as JSON with the following structure:

```json
{
  "id": "evt_abc123",
  "tenantId": "tenant_xyz789",
  "timestamp": "2025-01-15T10:30:45.123456Z",
  "actor": {
    "type": "user",
    "user": {
      "id": "user_123",
      "externalUserId": "user@example.com"
    }
  },
  "action": {
    "type": "userLogin",
    "userLogin": {
      "success": true
    }
  },
  "resource": {
    "type": "userAccount",
    "userAccount": {
      "id": "account_456"
    }
  },
  "context": {
    "ipAddress": "xxx.xxx.xxx.xxx",
    "userAgent": "Mozilla/5.0..."
  }
}
```

## Extracted Fields

The app automatically extracts the following fields:

- `action_type`: Type of action performed (e.g., `userLogin`, `userAccountCreation`)
- `actor_type`: Type of actor (e.g., `user`, `serviceAccount`)
- `actor_id`: ID of the actor who performed the action
- `resource_type`: Type of resource affected (e.g., `userAccount`, `group`)
- `tenant_id`: Method Security tenant identifier
- `event_id`: Unique event identifier
- `ip_address`: Source IP address
- `user_agent`: User agent string

## Example Searches

### Recent Login Events

```spl
index=method_audit sourcetype=method:audit action_type="userLogin"
| table _time, actor_id, ip_address, action.userLogin.success
```

### Failed Login Attempts

```spl
index=method_audit sourcetype=method:audit action_type="userLogin" action.userLogin.success=false
| stats count by actor_id, ip_address
| sort -count
```

### User Account Modifications

```spl
index=method_audit sourcetype=method:audit action_type="userAccountModification"
| table _time, actor_id, resource.userAccount.id
```

### Activity by IP Address

```spl
index=method_audit sourcetype=method:audit
| stats count by ip_address, action_type
| sort -count
```

## Troubleshooting

### Check Input Status

```spl
index=_internal source="*method_audit_logs*.log"
| stats count by log_level
```

### View Recent Errors

```spl
index=_internal source="*method_audit_logs*.log" log_level=ERROR
| table _time, message
```

### Verify Data Collection

```spl
index=method_audit sourcetype=method:audit
| stats count by _time span=1h
| timechart span=1h sum(count)
```

### Common Issues

#### No Events Being Collected

1. **Check credentials**: Verify your Client ID and Client Secret are correct
2. **Check API URL**: Ensure the base URL is correct and accessible
3. **Check network**: Verify Splunk can reach the Method API (firewall rules, proxies)
4. **Check logs**: Look for errors in `index=_internal source="*method_audit_logs*.log"`

#### Authentication Errors

```spl
index=_internal source="*method_audit_logs*.log" "authentication" OR "oauth"
```

- Verify credentials are correct
- Check if credentials have expired or been revoked
- Ensure the service account has proper permissions in Method Security

#### Duplicate Events

- Check if multiple inputs are configured for the same data source
- Verify checkpoint is being saved correctly

## Checkpoint Management

The app maintains checkpoints to track the last collected event timestamp. Checkpoints are stored in:

```
$SPLUNK_HOME/etc/apps/method-security-audit-ingestion/local/method_audit_logs_checkpoints.json
```

To reset collection and start over:

1. Stop the input (set `disabled = 1` in inputs.conf)
2. Delete or modify the checkpoint file
3. Update `start_time` in inputs.conf
4. Re-enable the input

## Performance Considerations

- **Interval**: For high-volume environments, consider more frequent collection (60-300 seconds)
- **Page Size**: The app fetches 1000 events per API call (maximum supported)
- **Backfill**: Initial backfill of historical data may take time; consider starting with a recent date

## Support

For issues related to:

- **This Splunk app**: Open an issue on [GitHub](https://github.com/your-org/method-security-audit-splunk)
- **Method Security Platform**: Contact Method Security support
- **Splunk**: Contact Splunk support or visit Splunk Answers

## Version History

### v0.0.1 (Current)

- Initial release
- Basic audit event collection
- OAuth 2.0 authentication
- Checkpoint management
- Pagination support

## Documentation

- **[Development Guide](docs/DEVELOPMENT.md)** - For developers contributing to the app
- **[Release Process](docs/RELEASING.md)** - How to cut a new release
- **[AppInspect Guide](docs/APPINSPECT.md)** - Splunk AppInspect validation

## License

This app is provided under [LICENSE] - see LICENSE file for details.

## Contributing

Contributions are welcome! Please see [DEVELOPMENT.md](docs/DEVELOPMENT.md) for guidelines.

## About Method Security

Method Security provides comprehensive security solutions for modern enterprises. Visit [method.security](https://method.security) to learn more.
