# SAP SecurityBridge Push API Setup Guide

This guide explains how to configure SAP SecurityBridge to push security events to Splunk in real-time using the TA-SecurityBridge app.

## Overview

### Pull vs Push

| Feature | Pull API | Push API |
|---------|----------|----------|
| **Direction** | Splunk polls SAP | SAP sends to Splunk |
| **Latency** | Up to 5 minutes | Near real-time (seconds) |
| **SAP Load** | Higher (constant polling) | Lower (event-driven) |
| **Network** | Splunk needs access to SAP | SAP needs access to Splunk |
| **Use Case** | Standard monitoring | Real-time alerting |

### Architecture

```
Pull API:
┌─────────┐    polls every N sec    ┌─────────┐
│ Splunk  │ ───────────────────────>│   SAP   │
│         │ <─────────────────────── │         │
└─────────┘    returns events       └─────────┘

Push API:
┌─────────┐    sends events         ┌─────────┐
│ Splunk  │ <─────────────────────── │   SAP   │
│  (HEC)  │    when they occur      │         │
└─────────┘                         └─────────┘
```

## Prerequisites

- Splunk Enterprise with TA-SecurityBridge app installed
- SAP SecurityBridge installed and configured
- Network connectivity from SAP to Splunk (port 8088)
- Administrative access to both systems

## Part 1: Splunk Configuration (via App)

The TA-SecurityBridge app provides a built-in configuration page that **automatically creates and manages HEC tokens** for you.

### Step 1: Access Push API Settings

1. Log in to Splunk Web
2. Navigate to **Apps** → **TA-SecurityBridge** → **Configuration**
3. Click the **Push API Settings** tab

### Step 2: Configure Push API

| Field | Description | Recommended Value |
|-------|-------------|-------------------|
| **Enable Push API** | Turn on push integration | ✓ Checked |
| **Target Index** | Where push events are stored | `sap` |
| **HEC Token Name** | Auto-generated token name | (auto-generated on save) |
| **HEC Token** | Leave empty for auto-creation | (empty) |
| **HEC URL** | Splunk HEC endpoint | `https://localhost:8088/services/collector` |
| **SAP Webhook URL** | URL to configure in SAP | (copy to SAP after replacing host) |

### Step 3: Save Configuration

Click **Save**. The app will automatically:
- Enable HEC in Splunk (if not already enabled)
- Create a new HEC token named `sap_securitybridge_push_XXXXXXXX`
- Configure the token for sourcetype `sapsb_push_json`
- Store the token securely in the app configuration

### Step 4: Get the HEC Token Value

After saving, retrieve the auto-created token:

1. Go to **Settings** → **Data Inputs** → **HTTP Event Collector**
2. Find the token starting with `sap_securitybridge_push_`
3. Copy the **Token Value** (you'll need this for SAP configuration)

## Part 2: Network Configuration

### Firewall/Security Groups

Ensure SAP server can reach Splunk on port 8088.

**For AWS EC2:**
1. Go to EC2 Console → Security Groups
2. Edit inbound rules for the Splunk instance
3. Add rule:
   - Type: Custom TCP
   - Port: 8088
   - Source: SAP server IP or security group

**For on-premises:**
- Open firewall port 8088 from SAP server to Splunk

## Part 3: SAP SecurityBridge Configuration

### Step 1: Access SIEM Configuration

1. Log in to SAP GUI
2. Run transaction: `/n/ABEX/SIEM_CONFIG`

### Step 2: Create SIEM Output Channel

Create a new output channel with the following settings:

| Field | Value |
|-------|-------|
| **Channel Name** | SPLUNK_PUSH |
| **Channel Type** | HTTP/REST |
| **Method** | POST |
| **Content-Type** | application/json |

### Step 3: Configure URL

```
https://<SPLUNK_HOST>:8088/services/collector/raw?sourcetype=sapsb_push_json&index=sap
```

Example:
```
https://54.84.140.207:8088/services/collector/raw?sourcetype=sapsb_push_json&index=sap
```

### Step 4: Configure Authentication Header

| Header Name | Header Value |
|-------------|--------------|
| Authorization | `Splunk <YOUR_HEC_TOKEN>` |

Example:
```
Authorization: Splunk 669f53aa-8b12-4e39-b119-45eb79699d19
```

### Step 5: Link to Service User

1. Assign the output channel to the service user
2. Configure which event types should be pushed
3. Enable the channel

## Part 4: Testing

### Test from Splunk Server (CLI)

Run this command **on the Splunk server** (localhost only works locally):

```bash
# Test HEC endpoint (run on Splunk server)
curl -k -X POST \
  "https://localhost:8088/services/collector/raw?sourcetype=sapsb_push_json&index=sap" \
  -H "Authorization: Splunk <YOUR_HEC_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"event_type": "test", "message": "Push API test", "timestamp": "'$(date +%s)'"}'
```

To test from a **remote machine**, replace `localhost` with the Splunk server IP:

```bash
# Test from remote (replace <SPLUNK_HOST> with actual IP/hostname)
curl -k -X POST \
  "https://<SPLUNK_HOST>:8088/services/collector/raw?sourcetype=sapsb_push_json&index=sap" \
  -H "Authorization: Splunk <YOUR_HEC_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"event_type": "test", "message": "Push API test", "timestamp": "'$(date +%s)'"}'
```

Expected response:
```json
{"text":"Success","code":0}
```

### Test with SAP Data

```bash
# Pull data from SAP
curl -k -u "SPLUNK:<PASSWORD>" \
  "https://<SAP_HOST>:44300/sap/opu/odata/ABEX/EVENTS_SRV/events?\$format=json" \
  -o sap_events.json

# Push to Splunk
curl -k -X POST \
  "https://localhost:8088/services/collector/raw?sourcetype=sapsb_push_json&index=sap" \
  -H "Authorization: Splunk <YOUR_HEC_TOKEN>" \
  -H "Content-Type: application/json" \
  -d @sap_events.json
```

### Verify in Splunk

```spl
index=sap sourcetype=sapsb_push_json
```

## Part 5: Running Both Pull and Push

You can run both methods simultaneously during migration:

| Input | Method | Status |
|-------|--------|--------|
| SecurityBridge REST API | Pull | Enabled |
| HEC (sap_securitybridge_push) | Push | Enabled |

**Benefits:**
- Validate Push data matches Pull data
- No gaps during transition
- Easy rollback if issues occur

**To disable Pull after validation:**
1. Go to **TA-SecurityBridge** → **Inputs**
2. Click the Pull input → **Disable**

## Troubleshooting

### Connection Refused (Port 8088)

**Symptoms:**
```
curl: (7) Failed to connect to host port 8088: Connection refused
```

**Solutions:**
1. Verify HEC is enabled: **Settings** → **Data Inputs** → **HTTP Event Collector** → **Global Settings**
2. Check firewall/security group rules
3. Verify Splunk is running

### Connection Reset by Peer

**Symptoms:**
```
curl: (56) Recv failure: Connection reset by peer
```

**Solutions:**
- Use `https://` instead of `http://`
- Add `-k` flag for self-signed certificates

### Invalid Token

**Symptoms:**
```json
{"text":"Invalid token","code":4}
```

**Solutions:**
1. Verify token value is correct
2. Check token is enabled in Splunk
3. Ensure token has permissions for target index

### Disk Space Error

**Symptoms:**
```
Search not executed: The minimum free disk space (5000MB) reached
```

**Solutions:**
```bash
# Clean dispatch directory
sudo rm -rf /opt/splunk/var/run/splunk/dispatch/*

# Clean introspection data
sudo rm -rf /opt/splunk/var/lib/splunk/_introspection/db/*
sudo rm -rf /opt/splunk/var/lib/splunk/_introspection/colddb/*

# Check space
df -h /
```

### No Data in Splunk

**Check SAP side:**
1. Verify output channel is enabled
2. Check SAP logs for connection errors
3. Test with manual curl from SAP server

**Check Splunk side:**
1. Verify HEC token is enabled
2. Check index exists
3. Review `$SPLUNK_HOME/var/log/splunk/splunkd.log`

## Security Best Practices

1. **Use HTTPS**: Always enable SSL for HEC
2. **Restrict Source IPs**: Use firewall rules or security groups to limit HEC access to SAP server IPs only
3. **Rotate Tokens**: Periodically rotate HEC tokens via Settings > Data Inputs > HTTP Event Collector
4. **Monitor Access**: Review Splunk logs for unauthorized access attempts

## Reference

### Sourcetypes

| Sourcetype | Method | Description |
|------------|--------|-------------|
| `sapsb_json` | Pull API | Events pulled from SAP |
| `sapsb_push_json` | Push API | Events pushed from SAP |

### HEC Endpoints

| Endpoint | Use Case |
|----------|----------|
| `/services/collector/event` | Single JSON event with metadata |
| `/services/collector/raw` | Raw data (recommended for push) |

### App Configuration Location

| Setting | Location |
|---------|----------|
| Push API Settings | `$SPLUNK_HOME/etc/apps/TA-SecurityBridge/local/ta_securitybridge_settings.conf` |
| HEC Tokens | `$SPLUNK_HOME/etc/apps/splunk_httpinput/local/inputs.conf` |

### Sample Push Event Format

```json
{
  "timestamp": 1736776800,
  "system": "PRD001",
  "event_type": "security_violation",
  "severity": "High",
  "account": "USER001",
  "client": "100",
  "terminal": "192.168.1.100",
  "transaction": "SE80",
  "object": "TABLE_READ",
  "action": "UNAUTHORIZED_ACCESS",
  "eventMsg": "Unauthorized table access attempt"
}
```

## Support

For issues:
1. Check this documentation
2. Review Splunk logs: `$SPLUNK_HOME/var/log/splunk/splunkd.log`
3. Enable detailed logging in Push API Settings
4. Test with curl commands to isolate the issue
