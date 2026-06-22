# Anchore Add-on For Splunk

**Version:** 1.1.0  
**Author:** Tanuj Bansal  
**Splunk App ID:** TA-anchore-add-on-for-splunk

## Overview

The Anchore Add-on for Splunk connects to Anchore APIs to collect vulnerability scanner metrics and provides a dynamic dashboard for Anchore vulnerability analysis and troubleshooting. This add-on enables security teams to monitor container security posture directly within Splunk with real-time vulnerability data from Anchore Engine/Enterprise.

## Features

### 🔍 **Vulnerability Data Collection**
- Automated collection of vulnerability data from Anchore APIs
- Support for multiple Anchore accounts and registries
- Configurable data collection intervals
- HTTP Event Collector (HEC) integration for reliable data ingestion

### 📊 **Dynamic Security Dashboard**
- **Real-time vulnerability monitoring** with severity-based alerting
- **Dynamic index selection** - automatically detects and uses the index with latest vulnerability data
- **Interactive filtering** by account, registry, repository, and severity levels
- **Security metrics** including vulnerability counts, affected images, and security scores
- **Critical security alerts** with color-coded status indicators

### 📈 **Comprehensive Analytics**
- Vulnerability trends over time
- Top vulnerable packages and repositories 
- Registry security overview with comparative metrics
- Recent scan activity monitoring
- Drill-down capabilities for detailed investigation

## Installation

### Prerequisites
- Splunk Enterprise 9.3+ 
- Anchore Engine/Enterprise with API access
- Valid Anchore API credentials
- HTTP Event Collector (HEC) configured in Splunk

### Install Steps

1. **Download and Install**
   ```bash
   # Install via Splunk CLI
   $SPLUNK_HOME/bin/splunk install app TA-anchore-add-on-for-splunk.tar.gz
   
   # Or extract to apps directory
   tar -xzf TA-anchore-add-on-for-splunk.tar.gz -C $SPLUNK_HOME/etc/apps/
   ```

2. **Restart Splunk**
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

3. **Configure the Add-on** (see Configuration section below)

## Configuration

### 1. Basic Configuration

Navigate to **Splunk Settings > Data Inputs > Anchore Vulnerabilities** or edit the configuration files:

#### `default/inputs.conf`
```conf
[anchore_vulnerabilities]
start_by_shell = false
python.version = python3
sourcetype = anchore:vulnerabilities
interval = 300
api_url = https://your-anchore-engine.com/v2
api_key = YOUR-ANCHORE-API-KEY
anchore_verify_ssl = True
hec_url = https://your-splunk-instance.com/services/collector
hec_token = YOUR-SPLUNK-HEC-TOKEN
hec_verify_ssl = True
disabled = 0
```

### 2. Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `api_url` | Anchore API endpoint URL | `https://anchore-engine.company.com/v2` |
| `api_key` | Anchore API authentication key | `your-api-key-here` |
| `hec_url` | Splunk HTTP Event Collector URL | `https://splunk.company.com/services/collector` |
| `hec_token` | Splunk HEC token for data ingestion | `your-hec-token-here` |
| `interval` | Data collection interval (seconds) | `300` (5 minutes) |

### 3. SSL Configuration
- Set `anchore_verify_ssl = True` for production environments
- Set `hec_verify_ssl = True` for secure HEC connections
- Use `False` only for testing with self-signed certificates

### 4. Index Configuration
The add-on automatically detects available indexes containing vulnerability data. No manual index configuration is required - the dashboard dynamically selects the index with the most recent data.

## Usage

### Accessing the Dashboard

1. Navigate to **Apps > Anchore Add-on For Splunk**
2. Click **Anchore Security Vulnerability Dashboard**
3. The dashboard will automatically load data from the most recent index

### Dashboard Features

#### 🎛️ **Interactive Controls**
- **Index Selector**: Choose from available indexes with vulnerability data
- **Time Range**: Adjust analysis timeframe (default: last 24 hours)
- **Account Filter**: Filter by specific Anchore accounts
- **Registry Filter**: Focus on specific container registries
- **Repository Filter**: Narrow down to specific repositories
- **Severity Filter**: Filter by vulnerability severity levels

#### 🚨 **Alert System**
- **Critical Alert**: Red banner when critical vulnerabilities detected
- **Warning Alert**: Yellow banner for high-severity issues (>5 high-severity vulns)
- **Normal Status**: Green banner when security posture is acceptable

#### 📊 **Key Metrics**
- Critical and High severity vulnerability counts
- Total vulnerabilities and affected images
- Clean (vulnerability-free) image count
- Overall security score percentage

#### 📋 **Detailed Views**
- **Critical Issues Table**: Prioritized list of critical/high severity vulnerabilities
- **Vulnerability Trends**: Time-series analysis of vulnerability discovery
- **Top Vulnerable Repositories**: Most affected container repositories
- **Package Analysis**: Most vulnerable packages across your environment
- **Registry Overview**: Security posture by registry
- **Recent Activity**: Latest vulnerability scan results

### Search Examples

#### Basic Vulnerability Search
```spl
index="your_index" sourcetype="anchore:vulnerabilities"
| search severity="Critical"
| stats count by repo, vuln_id
```

#### Security Score by Registry
```spl
index="your_index" sourcetype="anchore:vulnerabilities"
| stats count(eval(vulnerability_found=true)) as vulnerable,
        count(eval(vulnerability_found=false)) as clean by registry
| eval security_score = round((clean/(clean+vulnerable))*100, 1)
```

## API Integration

The add-on follows a two-step API integration process:

### Step 1: Image Discovery
```
GET /images
Headers: x-anchore-account: <account_name>
```

### Step 2: Vulnerability Analysis
```
GET /images/{image_digest}/vuln/all  
Headers: x-anchore-account: <account_name>
```

For detailed API flow documentation, see `anchore_api_flow.md`.

## Data Model

### Sourcetype: `anchore:vulnerabilities`

#### Key Fields
| Field | Description | Example Values |
|-------|-------------|----------------|
| `severity` | Vulnerability severity | Critical, High, Medium, Low |
| `vuln_id` | CVE identifier | CVE-2023-1234 |
| `package_name` | Affected package | openssl |
| `package_version` | Package version | 1.1.1k-r0 |
| `repo` | Container repository | nginx, alpine |
| `tag` | Image tag | latest, v1.2.3 |
| `registry` | Container registry | docker.io, gcr.io |
| `account_name` | Anchore account | production, staging |
| `vulnerability_found` | Vulnerability status | true, false |
| `image_digest` | Container image digest | sha256:abc123... |

## Troubleshooting

### Common Issues

#### 1. No Data Appearing
- Verify Anchore API connectivity: `curl -u "_api_key:<API_KEY>" https://your-anchore-url/v2/images`
- Check HEC token validity in Splunk
- Verify `inputs.conf` configuration
- Check Splunk internal logs: `index=_internal source=*anchore*`

#### 2. SSL Certificate Errors
- Set `anchore_verify_ssl = False` for testing
- Install proper CA certificates on Splunk server
- Use IP addresses instead of hostnames if DNS issues exist

#### 3. Authentication Failures
- Verify API key format and permissions
- Ensure account name is correct in API headers
- Check Anchore user permissions for vulnerability data access

#### 4. Dashboard Not Loading
- Verify index contains data: `index=* sourcetype="anchore:vulnerabilities" | head 10`
- Check that dynamic index detection is working
- Ensure proper time range selection

### Log Locations
- **Splunk Internal Logs**: `index=_internal source=*anchore*`
- **Input Logs**: Check `$SPLUNK_HOME/var/log/splunk/ta_anchore_add_on_for_splunk_anchore_vulnerabilities.log`

## Support

### Getting Help
- Review the `anchore_api_flow.md` for API integration details
- Check Splunk internal logs for error messages
- Verify Anchore API documentation for endpoint changes
- Test API connectivity independently before troubleshooting Splunk integration

### Contributing
This add-on was built using Splunk Add-on Builder. For customizations:
1. Use Splunk Add-on Builder for GUI modifications
2. Edit configuration files for input parameter changes
3. Modify dashboard XML for visualization customizations

## Version History

### v1.0.0
- Initial release
- Dynamic index selection
- Comprehensive vulnerability dashboard
- Multi-account and multi-registry support
- Real-time alerting system
- HEC integration for reliable data ingestion

## License

This add-on is provided as-is for integration with Anchore vulnerability scanning platforms.