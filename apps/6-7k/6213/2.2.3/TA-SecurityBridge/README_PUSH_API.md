# SAP SecurityBridge Push API Integration

This implementation extends the existing SAP SecurityBridge Technology Add-on to support **Push API** integration alongside the existing Pull API functionality.

## Overview

The Push API implementation allows SAP systems to actively send security events to Splunk in real-time, replacing the periodic polling mechanism. This provides:

- **Near real-time data ingestion** (vs 5-minute polling intervals)
- **Reduced SAP system load** (no periodic API calls)
- **Better scalability** for high-volume environments
- **Alignment with existing Microsoft Sentinel and Rapid7 implementations**

## Architecture

### Components Added

1. **Webhook Receiver** (`sap_push_webhook.py`)
   - HTTP endpoint for receiving SAP push notifications
   - Signature validation for security
   - Data transformation and HEC forwarding

2. **Configuration Management** (`TA_SecurityBridge_rh_push_settings.py`)
   - REST handler for push API settings
   - Secure token and secret management
   - IP allowlisting and validation

3. **Monitoring System** (`sap_push_monitor.py`)
   - Health monitoring for webhook endpoints
   - Error alerting and logging
   - Performance metrics collection

4. **Updated Data Parsing** (`props.conf` additions)
   - New sourcetype `sapsb_push_json` for push data
   - Field extraction rules optimized for push format
   - Backward compatibility with existing pull data

## Setup Instructions

### 1. Enable Push API Support

1. **Configure HEC (HTTP Event Collector)**:
   ```bash
   # In Splunk Web UI:
   # Settings → Data Inputs → HTTP Event Collector
   # Create new token or use existing one
   ```

2. **Configure Push Settings**:
   ```bash
   # Navigate to: Apps → TA-SecurityBridge → Configuration
   # Add new Push Settings configuration
   ```

3. **Update inputs.conf**:
   ```ini
   # Replace <HEC_TOKEN_PLACEHOLDER> with actual token
   [http://sap_securitybridge_push]
   sourcetype = sapsb_push_json
   index = main
   disabled = 0
   token = your-hec-token-here
   ```

### 2. Configure SAP System

Configure your SAP SecurityBridge installation to send events to:

**Webhook URL**: `https://your-splunk-server:8088/services/collector/event`

**OR**

**Custom Webhook URL**: `https://your-splunk-server:8000/en-US/app/TA-SecurityBridge/sap_push_webhook`

### 3. Security Configuration

#### Option A: HEC with Authentication
- Use HEC token authentication (recommended)
- Configure firewall rules to allow SAP system IPs

#### Option B: Custom Webhook with Signature Validation
- Enable signature validation in Push Settings
- Configure webhook secret (auto-generated)
- Use `X-SAP-Signature` header with HMAC-SHA256

### 4. Enable Monitoring (Optional)

```ini
# In inputs.conf, enable monitoring:
[sap_push_monitor://default]
disabled = 0
check_interval = 60
alert_threshold = 5
```

## Data Format

### Expected Push JSON Format

```json
{
  \"timestamp\": 1634567890,
  \"system\": \"PRD001\",
  \"event_type\": \"security_violation\",
  \"severity\": \"High\",
  \"account\": \"USER001\",
  \"client\": \"100\",
  \"terminal\": \"192.168.1.100\",
  \"transaction\": \"SE80\",
  \"object\": \"TABLE_READ\",
  \"action\": \"UNAUTHORIZED_ACCESS\",
  \"eventMsg\": \"Unauthorized table access attempt\",
  \"eventUserEmail\": \"user@company.com\",
  \"eventUserFullname\": \"John Doe\"
}
```

### Batch Format Support

```json
{
  \"events\": [
    { /* event 1 */ },
    { /* event 2 */ }
  ]
}
```

## Migration from Pull to Push

### Phase 1: Parallel Operation
1. Keep existing pull configuration enabled
2. Configure push API alongside
3. Validate data consistency
4. Monitor performance

### Phase 2: Transition
1. Disable pull API: Set `disabled = 1` in pull input
2. Enable push API: Set `disabled = 0` in HEC input
3. Enable monitoring: Set `disabled = 0` in monitor input

### Rollback Plan
If issues occur, quickly revert by:
1. Disable push: `disabled = 1` in HEC input
2. Re-enable pull: `disabled = 0` in pull input
3. Restart Splunk or reload deployment

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Data**
   - Check firewall rules between SAP and Splunk
   - Verify URL configuration in SAP system
   - Check Splunk web server logs

2. **Authentication Failures**
   - Validate HEC token in inputs.conf
   - Check webhook secret configuration
   - Verify signature validation settings

3. **Data Parsing Issues**
   - Check sourcetype assignment (`sapsb_push_json`)
   - Validate JSON format from SAP system
   - Review field extraction rules

### Log Files

- **Webhook logs**: `/opt/splunk/var/log/splunk/sap_push_webhook.log`
- **Monitor logs**: Check internal logs for `sap_push_monitor`
- **Splunk logs**: `$SPLUNK_HOME/var/log/splunk/splunkd.log`

### Performance Monitoring

Search for monitoring events:
```spl
index=main sourcetype=\"sap:push:monitor\" 
| stats latest(webhook_status) as webhook_status, latest(overall_status) as status by host
```

Check for alerts:
```spl
index=main sourcetype=\"sap:push:alert\"
| dedup alert_message
| sort - _time
```

## API Endpoints

- **Webhook Receiver**: `/sap_push_webhook` (POST)
- **Health Check**: `/sap_push_webhook/health` (GET)
- **Configuration**: REST API via Splunk management interface

## Security Best Practices

1. **Use HTTPS**: Always configure SSL/TLS for webhook endpoints
2. **IP Allowlisting**: Configure allowed source IPs in settings
3. **Signature Validation**: Enable HMAC-SHA256 signature validation
4. **Token Rotation**: Regularly rotate HEC tokens and webhook secrets
5. **Monitor Access**: Enable detailed logging for security events

## Performance Considerations

- **Payload Size**: Maximum 1MB per request (configurable)
- **Request Timeout**: 30 seconds (configurable)
- **Concurrent Requests**: Splunk HEC handles multiple concurrent requests
- **Batch Processing**: Support for event batches to improve performance

## Support

For issues specific to the push API implementation:
1. Check this documentation
2. Review log files for errors
3. Validate configuration settings
4. Test with sample data

For general SAP SecurityBridge issues, contact your SAP administrator.