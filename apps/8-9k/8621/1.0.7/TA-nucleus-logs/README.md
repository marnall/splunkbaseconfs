# Nucleus User Logs Technology Add-on

## Overview
Technology Add-on for ingesting Nucleus Security audit logs into Splunk.

## Installation

### Splunk Cloud
1. Upload via Manage Apps > Install app from file
2. Navigate to Settings > Data Inputs > Nucleus Logs (REST)
3. Click "New" to create an input

### On-Premises Splunk
1. Extract to $SPLUNK_HOME/etc/apps/
2. Restart Splunk
3. Configure via Web UI or inputs.conf

## Configuration

### Via Splunk Web UI
1. Settings > Data Inputs > Nucleus Logs (REST)
2. Click "New"
3. Configure:
   - Name: unique identifier (e.g., "production")
   - base_url: Your Nucleus instance URL (e.g., https://your-instance.nucleussec.com)
   - api_key: Your Nucleus API key
   - interval: 300 (5 minutes recommended)
   - index: nucleus
   - Other optional parameters as needed

### Via Configuration File
Create `$SPLUNK_HOME/etc/apps/TA-nucleus-logs/local/inputs.conf`:

```ini
[nucleus_logs://production]
disabled = 0
base_url = https://your-instance.nucleussec.com
api_key = YOUR_API_KEY
interval = 300
limit = 500
initial_since_minutes = 1440
verify_ssl = true
index = nucleus
event_sourcetype = nucleus:logs
```

## Validation

Search for ingested data:
```spl
index=nucleus sourcetype=nucleus:logs
```

Check for errors:
```spl
index=_internal source=*splunkd.log* nucleus_logs
```

## Support
For issues, check the troubleshooting guide in the Splunk app documentation.

## Version
1.0.3

## Requirements
- Splunk Enterprise 8.0+ or Splunk Cloud
- Python 3.7+
- Network access to Nucleus Security API endpoint
