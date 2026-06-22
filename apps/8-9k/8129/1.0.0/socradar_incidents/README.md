# SOCRadar Incidents SOAR App

Version: 1.2.0 (Merged Edition)

## Overview

This Splunk SOAR app ingests incidents from SOCRadar's v4 API, creating containers and artifacts for security automation and response. It combines the best features from production implementations with SOAR platform best practices.

## Key Features

- **Automated Incident Ingestion**: Pulls incidents from SOCRadar API v4
- **State-Based Deduplication**: Prevents duplicate containers using persistent state
- **Status Change Detection**: Tracks and updates incident status changes
- **Rate Limit Handling**: Automatic backoff and retry for API rate limits
- **Pagination Support**: Handles large volumes with configurable limits
- **Proxy Support**: Works in enterprise environments with proxy requirements

## Installation

1. **Upload App Package**:
   - Navigate to **Apps** → **Install App** in SOAR UI
   - Upload the `socradar_merged.tgz` file
   - Click **Install**

2. **Configure Asset**:
   - Go to **Apps** → **SOCRadar Incidents**
   - Click **Asset Settings** → **Configure New Asset**
   - Fill in required configuration

3. **Test Connectivity**:
   - Click **Test Connectivity** button
   - Verify successful connection

4. **Enable Polling**:
   - In Asset settings, enable **Polling**
   - Set schedule (e.g., every 15 minutes)

## Configuration Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `socradar_company_id` | Yes | - | Your SOCRadar company ID |
| `socradar_api_key` | Yes | - | Your SOCRadar API key |
| `lookback_days` | No | 1 | Days to look back for incidents |
| `max_pages` | No | 50 | Maximum pages to fetch per poll |
| `max_incidents_per_poll` | No | 500 | Maximum incidents per polling cycle |
| `verify_ssl` | No | true | Verify SSL certificates |
| `http_proxy` | No | - | HTTP proxy URL |
| `https_proxy` | No | - | HTTPS proxy URL |

## Actions

### Test Connectivity
- **Purpose**: Validates API credentials and network connectivity
- **Type**: Test
- **Parameters**: None
- **Returns**: Success/failure status

### On Poll (Ingestion)
- **Purpose**: Ingests incidents from SOCRadar
- **Type**: Ingest
- **Features**:
  - Fetches incidents for configured time window
  - Creates one container per alarm_id
  - Creates artifacts with IOC enrichment
  - Maintains state for deduplication
  - Handles pagination automatically
  - Implements rate limit backoff

## Data Model

### Container Structure
```python
{
    "name": "SOCRadar Alarm {alarm_id}",
    "description": "{main_type}/{sub_type}",
    "label": "socradar",
    "severity": "high|medium|low",
    "source_data_identifier": "{alarm_id}"
}
```

### Artifact Structure
```python
{
    "name": "Alarm {alarm_id} artifact",
    "label": "event",
    "cef": {
        "alarm_id": "12345",
        "status": "Open",
        "alarm_link": "https://...",
        "ip": "1.2.3.4",  # If present
        "domain": "example.com",  # If present
        "hash": "abc123..."  # If present
    },
    "source_data_identifier": "{alarm_id}-{status}"
}
```

## State Management

The app maintains persistent state in SOAR's PostgreSQL database:

```python
{
    "alarm_status": {
        "12345": "Open",
        "12346": "Closed"
    },
    "last_updated": "2025-09-18T10:00:00Z",
    "total_processed": 1523
}
```

- State persists across app restarts
- Tracks up to 10,000 alarms (configurable)
- Automatically trims oldest entries when limit reached

## Deduplication Strategy

1. **Container Level**: `source_data_identifier = alarm_id`
   - Ensures one container per SOCRadar alarm
   - Updates existing container if alarm already exists

2. **Artifact Level**: `source_data_identifier = alarm_id-status`
   - Creates new artifact only on status change
   - Maintains history of status transitions

## Rate Limiting

The app handles SOCRadar API rate limits gracefully:
- Initial wait: 30 seconds on first 429 response
- Extended wait: 60 seconds on subsequent rate limits
- Automatic resume after wait period

## Troubleshooting

### Common Issues

1. **Authentication Failed (401)**:
   - Verify API key is correct
   - Check company_id matches your SOCRadar account
   - Ensure API key has necessary permissions

2. **No Incidents Ingested**:
   - Check lookback_days configuration
   - Verify incidents exist in time window
   - Review phantom.log for errors

3. **Rate Limit Errors**:
   - Reduce max_pages if consistently hitting limits
   - Increase polling interval
   - Contact SOCRadar for rate limit increase

4. **SSL Certificate Errors**:
   - Set verify_ssl to false (development only)
   - Add proper certificates to system trust store

### Log Locations

- App logs: `/opt/phantom/var/log/phantom/phantom_app_run.log`
- Main logs: `/opt/phantom/var/log/phantom/phantom.log`
- Debug info: Enable debug mode in asset configuration

## Performance Considerations

- Default: 500 incidents per poll (configurable)
- Pagination: 100 incidents per API page
- State tracking: 10,000 alarms maximum
- Text truncation: 5000 characters for large fields

## API Endpoints Used

- Base URL: `https://platform.socradar.com/api`
- Incidents: `/company/{company_id}/incidents/v4`
- Parameters: `key`, `limit`, `page`, `start_date`, `end_date`

## Development

### Local Testing
```bash
python socradar_connector.py test_config.json
```

### Test Configuration
```json
{
    "action": "test connectivity",
    "identifier": "test_connectivity",
    "parameters": {},
    "config": {
        "socradar_company_id": "your_company_id",
        "socradar_api_key": "your_api_key"
    }
}
```

## Version History

- **1.2.0** (2025-09-18): Merged edition with enhanced features
  - Combined ChatGPT implementation with SOAR best practices
  - Added progress percentage tracking
  - Enhanced error handling
  - Improved state management

- **1.1.0**: ChatGPT original implementation
- **1.0.0**: Initial release

## Support

For issues or questions:
1. Check this documentation
2. Review SOAR logs
3. Contact SOCRadar support for API issues
4. File issues in your organization's tracking system

## License

Copyright (c) 2025 SOCRadar Integration Team

## Credits

This app merges best practices from:
- ChatGPT's focused SOCRadar implementation
- Splunk SOAR platform templates
- Community feedback and testing