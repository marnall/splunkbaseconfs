# Canadian Cyber Centre Splunk App - Complete Documentation
## Version 3.1.0 with Advanced Deduplication System

**Author**: Alexandre Argeris  
**Version**: 3.1.0  
**Release Date**: December 18, 2025  
**Package**: cccs_alerts_app_v3.1.tar.gz

---

# Table of Contents

1. [Overview & Features](#overview--features)
2. [Quick Start](#quick-start)
3. [Installation Guide](#installation-guide)
4. [Configuration](#configuration)
5. [MITRE ATT&CK Integration](#mitre-attck-integration)
6. [Data Structure](#data-structure)
7. [Dashboard Guide](#dashboard-guide)
8. [Search Examples](#search-examples)
9. [MITRE Usage Guide](#mitre-usage-guide)
10. [Alert Configuration](#alert-configuration)
11. [Use Cases & Best Practices](#use-cases--best-practices)
12. [Troubleshooting](#troubleshooting)
13. [Technical Architecture](#technical-architecture)
14. [Upgrade Guide](#upgrade-guide)
15. [Support & Resources](#support--resources)

---

# Overview & Features

## What is This App?

This Splunk app collects alerts and advisories from the Canadian Centre for Cyber Security (CCCS) and provides comprehensive dashboards with **MITRE ATT&CK threat intelligence enrichment** for monitoring.

## 🆕 Version 3.1 - Advanced Deduplication System

This version introduces **dual-layer event deduplication** to eliminate duplicate alerts:
- **Feed-level hash validation** for quick detection of unchanged feeds
- **Event-level JSON hashing** to prevent duplicate events
- **Timestamp-based tracking** with 31-day retention window
- **Automatic cleanup** of old event hashes
- **Smart detection** even if CCCS republishes the same alerts

## Previous Major Release: Version 3.0 - MITRE ATT&CK Integration

Automated MITRE ATT&CK framework mapping for all CCCS alerts, providing:
- **Automatic technique detection** from 185+ MITRE techniques
- **Tactical classification** across 14 MITRE tactics
- **Threat scoring** (0-100) based on technique complexity and severity
- **Attack complexity analysis** (simple, moderate, complex)
- **Critical technique alerting** for ransomware, credential dumping, and active exploits

## Core Features

### Data Collection
- **Automated Collection**: Fetches CCCS alerts feed every 15 minutes
- **Dual-Layer Deduplication**: 
  - Layer 1: Feed-level hash comparison (SHA256)
  - Layer 2: Event-level JSON hashing with timestamp tracking
- **Smart Retention**: 31-day hash retention matching CCCS feed lifetime
- **Auto-Cleanup**: Automatic removal of event hashes older than 31 days
- **Dual Feed Support**: Works with both RSS and Atom formats with automatic fallback
- **Zero Duplicates**: Prevents duplicate events even if CCCS republishes alerts

### Content Parsing
- **JSON Parsing**: Automatically extracts key fields from alert data
- **HTML Content Extraction**: Advanced parsing of alert details
- **CVE Extraction**: Automatic identification and deduplication of CVEs
- **Exploit Detection**: Identifies actively exploited vulnerabilities
- **Product Identification**: Extracts affected products with version information
- **Recommendation Extraction**: Parses CCCS security recommendations

### MITRE ATT&CK Enrichment (NEW in v3.0)
- **Technique Mapping**: Automatically maps alert content to MITRE ATT&CK techniques
- **Threat Scoring**: Calculates threat scores (0-100) based on technique severity and complexity
- **Tactical Analysis**: Groups techniques by MITRE tactics (Initial Access, Execution, etc.)
- **Exploit Detection**: Identifies actively exploited vulnerabilities with MITRE context
- **CVE Correlation**: Links CVEs to MITRE techniques and tactics
- **Automated Alerting**: Pre-configured alerts for critical techniques and high threat scores

### Dashboards
1. **CCCS Alerts Dashboard** (Original): 
   - Total alerts count
   - New alerts in last 24 hours
   - Alerts over time (column chart)
   - Alert types distribution (pie chart)
   - Recent alerts table with drilldown to original links
   - Critical alerts (AL-prefixed) table

2. **MITRE ATT&CK Analysis Dashboard** (NEW):
   - MITRE technique and tactic distribution
   - Threat score analytics
   - Top 15 techniques detected
   - Attack complexity analysis
   - Active exploits with MITRE mapping
   - Tactical timeline visualization
   - High-severity alerts (score ≥ 50)

---

# Quick Start

## 5-Minute Setup

### 1. Install the App
```bash
# Via Splunk Web
Apps → Manage Apps → Install app from file
Upload: cccs_alerts_app_v3.0_mitre.tar.gz
Restart Splunk (if prompted)
```

### 2. Verify Installation
```spl
index=cyber_gc_ca sourcetype=cccs:alerts 
| stats count by mitre_enriched
```
Expected: You should see `mitre_enriched=true` for new alerts

### 3. View Dashboards
```
Navigate to: Canadian Cyber Centre app
Dashboards available:
- Overview
- CCCS Alerts
- MITRE ATT&CK Analysis (NEW)
```

### 4. First Searches

**View all alerts**:
```spl
index=cyber_gc_ca sourcetype=cccs:alerts
```

**View critical MITRE threats**:
```spl
index=cyber_gc_ca mitre_severity=critical
| table title, mitre_threat_score, mitre_techniques{}.id
```

**Check for active exploits**:
```spl
index=cyber_gc_ca exploit_mentioned=true mitre_enriched=true
| table title, exploit_context, mitre_tactics{}, cves{}
```

---

# Installation Guide

## Requirements

- Splunk Enterprise 8.0+ or Splunk Cloud
- Python 3.7+ (included with Splunk)
- Outbound HTTPS access to cyber.gc.ca
- Minimum 100MB free disk space

## Method 1: Install via Splunk Web (Recommended)

1. Download `cccs_alerts_app_v3.0_mitre.tar.gz`
2. Navigate to Apps → Manage Apps
3. Click "Install app from file"
4. Upload the .tar.gz file
5. Restart Splunk if prompted
6. Verify in Apps → Manage Apps that "Canadian Cyber Centre" appears

## Method 2: Manual Installation

1. Copy to Splunk apps directory:
   ```bash
   tar -xzf cccs_alerts_app_v3.0_mitre.tar.gz
   cp -r cccs_alerts_app $SPLUNK_HOME/etc/apps/
   chown -R splunk:splunk $SPLUNK_HOME/etc/apps/cccs_alerts_app
   ```

2. Restart Splunk:
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

3. Verify installation:
   ```bash
   $SPLUNK_HOME/bin/splunk list app
   ```

## Post-Installation Verification

### Check Scripted Input Status
```bash
$SPLUNK_HOME/bin/splunk list inputstatus
```
Look for: `script://$SPLUNK_HOME/etc/apps/cccs_alerts_app/bin/cccs_feed_collector.py`

### Test Manual Execution
```bash
cd $SPLUNK_HOME/etc/apps/cccs_alerts_app/bin
python3 cccs_feed_collector.py
```
Expected: JSON output of CCCS alerts

### Verify Data Ingestion
```spl
index=cyber_gc_ca sourcetype=cccs:alerts
| stats count by _time span=1h
```
Expected: Data points every 15 minutes

---

# Configuration

## Basic Setup

No additional configuration needed for standard installations. The app will start collecting data automatically after installation.

## Custom Index

To send events to a specific index, edit `default/inputs.conf`:

```ini
[script://$SPLUNK_HOME/etc/apps/cccs_alerts_app/bin/cccs_feed_collector.py]
index = security  # Change from 'cyber_gc_ca' to your desired index
```

## Change Collection Interval

To modify the collection interval (default: 900 seconds = 15 minutes), edit `default/inputs.conf`:

```ini
[script://$SPLUNK_HOME/etc/apps/cccs_alerts_app/bin/cccs_feed_collector.py]
interval = 1800  # Change to desired seconds (e.g., 1800 = 30 minutes)
```

## Proxy Configuration

If your environment requires a proxy, set environment variables:

```bash
export HTTPS_PROXY=http://proxy.company.com:8080
export HTTP_PROXY=http://proxy.company.com:8080
```

Or modify the collector script to add proxy support in the `fetch_feed()` function.

## Index Configuration

The app creates a custom index `cyber_gc_ca`. To use Splunk's default settings, edit `default/indexes.conf`:

```ini
[cyber_gc_ca]
# Customize retention, size, etc.
maxTotalDataSizeMB = 500000
frozenTimePeriodInSecs = 188697600  # 6 years
```

---

# MITRE ATT&CK Integration

## What Gets Enriched?

Every CCCS alert is automatically analyzed for MITRE ATT&CK techniques by:
- Scanning alert title, summary, and recommendations
- Matching keywords to 185+ MITRE techniques
- Detecting explicit MITRE technique references (T1234)
- Correlating CVEs with common attack techniques
- Analyzing exploit context for tactical indicators

## Threat Scoring Algorithm

### Score Calculation (0-100)

```
Threat Score = Technique Count (40%) + Tactic Diversity (32%) + Critical Techniques (28%)
```

**Components**:

1. **Technique Count** (up to 40 points)
   - Each technique adds 5 points
   - Maximum: 40 points (8 techniques)

2. **Tactic Diversity** (up to 32 points)
   - Each unique tactic adds 8 points
   - Maximum: 32 points (4 tactics)

3. **Critical Techniques** (up to 28 points)
   - T1190 (Exploit Public-Facing) = +7
   - T1068 (Privilege Escalation) = +7
   - T1486 (Ransomware) = +7
   - T1003 (Credential Dumping) = +7

### Severity Classification

- 🔴 **Critical** (70-100): Advanced attacks, 5+ techniques, diverse tactics
- 🟠 **High** (50-69): Complex attacks, multiple tactics
- 🟡 **Medium** (30-49): Moderate complexity, 2-3 techniques
- 🟢 **Low** (0-29): Simple attacks, single technique

### Example Scoring

**Alert: Cisco IOS XE Remote Code Execution**
```
Techniques Detected:
- T1190: Exploit Public-Facing Application
- T1203: Exploitation for Client Execution
- T1068: Privilege Escalation

Score Calculation:
- Technique Count: 3 × 5 = 15 points
- Tactic Diversity: 3 tactics × 8 = 24 points
- Critical Techniques: T1190 + T1068 = 14 points
Total: 15 + 24 + 14 = 53 points (High Severity)
```

## MITRE Technique Mappings

The app includes comprehensive mappings for 185+ techniques:

### Initial Access (TA0001)
- T1190: Exploit Public-Facing Application
- T1566: Phishing
- T1078: Valid Accounts
- T1133: External Remote Services
- T1189: Drive-by Compromise
- T1195: Supply Chain Compromise

### Execution (TA0002)
- T1059.001: PowerShell
- T1059.003: Windows Command Shell
- T1059.004: Unix Shell
- T1047: Windows Management Instrumentation
- T1053: Scheduled Task/Job

### Privilege Escalation (TA0004)
- T1068: Exploitation for Privilege Escalation
- T1548: Abuse Elevation Control Mechanism
- T1134: Access Token Manipulation

### Defense Evasion (TA0005)
- T1027: Obfuscated Files or Information
- T1055: Process Injection
- T1562: Impair Defenses
- T1070: Indicator Removal

### Credential Access (TA0006)
- T1003: OS Credential Dumping
- T1110: Brute Force
- T1056: Input Capture

### Lateral Movement (TA0008)
- T1021.001: Remote Desktop Protocol
- T1021.004: SSH
- T1021.002: SMB/Windows Admin Shares

### Impact (TA0040)
- T1486: Data Encrypted for Impact (Ransomware)
- T1485: Data Destruction
- T1499: Endpoint Denial of Service

*[Full list of 185+ techniques in the code]*

## Enrichment Fields

Each enriched alert contains:

```json
{
  "mitre_enriched": true,
  "mitre_techniques": [
    {
      "id": "T1190",
      "name": "Exploit Public-Facing Application",
      "tactic": "Initial Access",
      "detection_method": "keyword",
      "base_severity": "critical",
      "exploitability": "high",
      "detection_difficulty": "medium"
    }
  ],
  "mitre_tactics": ["Initial Access", "Execution"],
  "mitre_technique_count": 3,
  "mitre_tactic_count": 2,
  "mitre_attack_complexity": "moderate",
  "mitre_threat_score": 68,
  "mitre_severity": "high"
}
```

---

# Data Structure

## Core Alert Fields

All fields are automatically extracted from the JSON feed. Field names match the original JSON structure.

- `id`: Unique URL identifier for the alert
- `title`: Alert title
- `link`: URL to the full alert details on cyber.gc.ca (may be same as id)
- `published`: Publication timestamp (ISO 8601 format)
- `updated`: Last update timestamp (ISO 8601 format)
- `summary`: Brief summary of the alert
- `author`: Source organization (usually "Canadian Centre for Cyber Security")

## Parsed Content Fields

- `serial_number`: Alert serial number (e.g., AL25-016)
- `date`: Human-readable publication date
- `summary_text`: Array of summary paragraphs
- `recommendations`: Array of CCCS recommendations
- `affected_products`: Array of affected products with versions
  ```json
  [
    {
      "product": "Cisco IOS XE",
      "affected_versions": ["17.6.x", "17.9.x"]
    }
  ]
  ```
- `cves`: Array of CVE identifiers (e.g., ["CVE-2025-1234"])
- `exploit_mentioned`: Boolean indicating active exploitation
- `exploit_context`: Context text around exploit mentions
- `references`: Array of reference links
  ```json
  [
    {
      "name": "Cisco Security Advisory",
      "url": "https://..."
    }
  ]
  ```

## MITRE ATT&CK Fields

- `mitre_enriched`: Boolean flag (true if enrichment performed)
- `mitre_techniques`: Array of technique objects
- `mitre_tactics`: Array of tactic names
- `mitre_technique_count`: Count of unique techniques
- `mitre_tactic_count`: Count of unique tactics
- `mitre_attack_complexity`: "simple", "moderate", or "complex"
- `mitre_threat_score`: Calculated score (0-100)
- `mitre_severity`: "critical", "high", "medium", or "low"

## Complete Event Example

```json
{
  "id": "https://www.cyber.gc.ca/en/alerts-advisories/cisco-security-advisory-av25-759",
  "title": "Cisco Releases Security Advisories for Multiple Products",
  "published": "2025-01-15T14:30:00Z",
  "updated": "2025-01-15T14:30:00Z",
  "serial_number": "AV25-759",
  "date": "January 15, 2025",
  "summary_text": [
    "Cisco has released security advisories addressing vulnerabilities in multiple products.",
    "Organizations should review the advisories and apply necessary updates."
  ],
  "recommendations": [
    "The Cyber Centre recommends organizations review Cisco's advisories and apply patches."
  ],
  "cves": ["CVE-2025-1234", "CVE-2025-5678"],
  "affected_products": [
    {
      "product": "Cisco IOS XE",
      "affected_versions": ["17.6.x", "17.9.x"]
    }
  ],
  "exploit_mentioned": false,
  "references": [
    {
      "name": "Cisco Security Advisory",
      "url": "https://sec.cloudapps.cisco.com/security/center/content/..."
    }
  ],
  "mitre_enriched": true,
  "mitre_techniques": [
    {
      "id": "T1190",
      "name": "Exploit Public-Facing Application",
      "tactic": "Initial Access",
      "detection_method": "keyword",
      "base_severity": "critical",
      "exploitability": "high"
    },
    {
      "id": "T1068",
      "name": "Exploitation for Privilege Escalation",
      "tactic": "Privilege Escalation",
      "detection_method": "keyword",
      "base_severity": "critical"
    }
  ],
  "mitre_tactics": ["Initial Access", "Privilege Escalation", "Execution"],
  "mitre_technique_count": 3,
  "mitre_tactic_count": 3,
  "mitre_attack_complexity": "moderate",
  "mitre_threat_score": 53,
  "mitre_severity": "high"
}
```

---

# Dashboard Guide

## CCCS Alerts Dashboard

Traditional alert monitoring dashboard with:

### Key Metrics
- **Total Alerts**: Count of unique alerts in selected time range
- **New Alerts (24h)**: Alerts from last 24 hours

### Visualizations
- **Alerts Over Time**: Column chart showing alert volume trends
- **Alert Types**: Pie chart of alert distribution by vendor
- **Recent Alerts**: Table with latest alerts, clickable to cyber.gc.ca
- **Critical Alerts**: AL-prefixed alerts requiring immediate attention

### Usage
1. Select time range (default: last 7 days)
2. Use search filter for keywords
3. Click alert titles to view full details on cyber.gc.ca
4. Export tables for reporting

## MITRE ATT&CK Analysis Dashboard (NEW)

Comprehensive threat intelligence dashboard with:

### Top Row: Key Metrics
- **Total Enriched Alerts**: Count of alerts with MITRE data
- **Unique Techniques**: Number of distinct MITRE techniques detected
- **Critical Severity**: Count of critical-severity alerts
- **Average Threat Score**: Mean threat score across all alerts

### MITRE Visualizations
- **Tactics Distribution**: Bar chart of top 14 MITRE tactics
- **Threat Score Distribution**: Pie chart of score ranges
- **Top 15 Techniques**: Table with technique ID, name, tactic, count
- **Tactics Timeline**: Stacked column chart showing tactics over time

### Critical Alerts Section
- **Active Exploits with MITRE**: Table of exploited vulns with techniques
- **High-Severity Alerts**: Alerts with threat score ≥ 50

### Attack Analysis
- **Attack Complexity**: Distribution of simple/moderate/complex attacks
- **Technique Count per Alert**: How many techniques per alert

### Product Analysis
- **Top Affected Products**: Products with MITRE technique mapping

### Interactive Features
- Time range selection (default: last 30 days)
- Severity filtering (critical/high/medium/low/all)
- Keyword search across all fields
- Drilldown to detailed searches
- Direct links to original CCCS alerts

---

# Search Examples

## Basic Searches

### View All Alerts
```spl
index=cyber_gc_ca sourcetype=cccs:alerts
```

### Search by Vendor
```spl
index=cyber_gc_ca sourcetype=cccs:alerts alert_title="Cisco*"
```

### Find Critical Alerts
```spl
index=cyber_gc_ca sourcetype=cccs:alerts alert_id="*AL*"
```

### Recent Alerts
```spl
index=cyber_gc_ca sourcetype=cccs:alerts earliest=-24h
```

### Count by Vendor
```spl
index=cyber_gc_ca sourcetype=cccs:alerts 
| rex field=alert_title "(?<vendor>^\w+)\s" 
| stats count by vendor 
| sort -count
```

### Alert Timeline
```spl
index=cyber_gc_ca sourcetype=cccs:alerts 
| timechart count span=1d
```

## MITRE ATT&CK Searches

### Find Specific Technique
```spl
index=cyber_gc_ca sourcetype=cccs:alerts mitre_techniques{}.id="T1190"
```

### Search by Tactic
```spl
index=cyber_gc_ca sourcetype=cccs:alerts mitre_tactics{}="Initial Access"
```

### High Threat Score Alerts
```spl
index=cyber_gc_ca sourcetype=cccs:alerts mitre_threat_score>=70
| table title, mitre_threat_score, mitre_severity, mitre_techniques{}.id
| sort -mitre_threat_score
```

### Critical with Active Exploits
```spl
index=cyber_gc_ca sourcetype=cccs:alerts 
    mitre_severity=critical 
    exploit_mentioned=true
| table title, exploit_context, mitre_tactics{}, cves{}
```

### Count by MITRE Tactic
```spl
index=cyber_gc_ca sourcetype=cccs:alerts mitre_tactics{}=*
| stats count by mitre_tactics{}
| sort -count
```

### Top MITRE Techniques
```spl
index=cyber_gc_ca sourcetype=cccs:alerts mitre_techniques{}.id=*
| stats count by mitre_techniques{}.id, mitre_techniques{}.name
| sort -count
| head 10
```

### Ransomware Alerts
```spl
index=cyber_gc_ca sourcetype=cccs:alerts mitre_techniques{}.id="T1486"
| table title, affected_products{}.product, cves{}, mitre_threat_score
```

### Complex Attacks (5+ Techniques)
```spl
index=cyber_gc_ca sourcetype=cccs:alerts mitre_technique_count>=5
| table title, mitre_technique_count, mitre_tactics{}, mitre_attack_complexity
```

## Advanced Analysis

### Daily Threat Intelligence Summary
```spl
index=cyber_gc_ca sourcetype=cccs:alerts earliest=-24h
| stats count as total_alerts,
        dc(mitre_techniques{}.id) as unique_techniques,
        dc(mitre_tactics{}) as unique_tactics,
        avg(mitre_threat_score) as avg_score,
        count(eval(mitre_severity="critical")) as critical_count,
        count(eval(exploit_mentioned="true")) as exploit_count
| eval avg_score=round(avg_score, 1)
```

### Technique Trend Analysis
```spl
index=cyber_gc_ca sourcetype=cccs:alerts mitre_techniques{}.id=*
| timechart span=1d dc(mitre_techniques{}.id) as unique_techniques
```

### CVE to MITRE Correlation
```spl
index=cyber_gc_ca sourcetype=cccs:alerts cves{}=* mitre_techniques{}.id=*
| stats values(mitre_techniques{}.id) as techniques by cves{}
| sort cves{}
```

### Product Vulnerability Matrix
```spl
index=cyber_gc_ca sourcetype=cccs:alerts 
    affected_products{}.product=* 
    mitre_threat_score>=50
| stats values(cves{}) as cves,
        values(mitre_techniques{}.id) as techniques,
        max(mitre_threat_score) as max_score
        by affected_products{}.product
| sort -max_score
```

### Correlation with Internal Detections
```spl
# Find CCCS techniques observed in your environment
index=cyber_gc_ca sourcetype=cccs:alerts mitre_techniques{}.id=*
| stats values(mitre_techniques{}.id) as cccs_techniques by _time
| append [
    search index=security (sourcetype=windows:security OR sourcetype=linux:auth)
    | eval technique="T1078"  # Valid Accounts example
    | stats count by technique, _time
  ]
| stats count by technique
| where count > 1
| eval status="⚠️ CCCS technique matches environment activity!"
```

---

# MITRE Usage Guide

## Threat Score Interpretation

### Understanding Your Score

**0-29 (Low)**:
- Simple, single-technique attacks
- Low sophistication
- Often automated scans or probes
- Action: Monitor, apply standard patches

**30-49 (Medium)**:
- 2-3 techniques involved
- Moderate attacker sophistication
- May target specific vulnerabilities
- Action: Prioritize patching, review logs

**50-69 (High)**:
- Complex, multi-technique attacks
- Skilled attacker with diverse tactics
- Multiple attack vectors
- Action: Immediate patching, threat hunt, alert SOC

**70-100 (Critical)**:
- Advanced persistent threat indicators
- 5+ techniques across diverse tactics
- Nation-state or sophisticated cybercrime groups
- Action: Emergency response, incident investigation, CISO notification

## Common Use Cases

### 1. Daily Threat Intelligence Review

**Goal**: Start your day with MITRE-enriched intelligence

```spl
index=cyber_gc_ca sourcetype=cccs:alerts mitre_enriched=true earliest=-24h
| stats count as alerts, 
        avg(mitre_threat_score) as avg_score,
        values(mitre_tactics{}) as tactics,
        dc(mitre_techniques{}.id) as unique_techniques
| eval avg_score=round(avg_score, 1)
```

**Interpretation**:
- `avg_score > 60`: Elevated threat landscape
- Many `unique_techniques`: Diverse attack vectors
- New tactics: Emerging threat patterns

### 2. Prioritize Vulnerabilities for Patching

**Goal**: Focus on exploitable techniques

```spl
index=cyber_gc_ca sourcetype=cccs:alerts 
    cves{}=* 
    mitre_techniques{}.exploitability="high"
| stats values(cves{}) as cves, 
        values(mitre_techniques{}.id) as techniques,
        max(mitre_threat_score) as max_score
        by affected_products{}.product
| where max_score >= 60
| sort -max_score
```

**Action Plan**:
1. Patch products with `max_score ≥ 70` immediately
2. Schedule `60-69` within 7 days
3. Review high exploitability CVEs first

### 3. Detect Ransomware Campaigns

**Goal**: Early ransomware identification

```spl
index=cyber_gc_ca sourcetype=cccs:alerts 
    (mitre_techniques{}.id="T1486" OR 
     mitre_techniques{}.id="T1485" OR
     keywords IN ("ransomware", "data encrypted"))
| eval published_time=strftime(strptime(published, "%Y-%m-%dT%H:%M:%SZ"), "%Y-%m-%d %H:%M")
| table published_time, title, mitre_threat_score, affected_products{}.product, cves{}
| sort -published_time
```

**Response Actions**:
- Verify backup integrity immediately
- Review endpoint protection coverage
- Brief incident response team
- Update IOCs in detection tools

### 4. Gap Analysis - Detection Coverage

**Goal**: Identify detection blind spots

```spl
index=cyber_gc_ca sourcetype=cccs:alerts mitre_techniques{}.id=*
| stats count by mitre_techniques{}.id, mitre_techniques{}.name, mitre_techniques{}.detection_difficulty
| eval can_detect=case(
    mitre_techniques{}.detection_difficulty="easy", "Yes - High Confidence",
    mitre_techniques{}.detection_difficulty="medium", "Partial - Medium Confidence",
    mitre_techniques{}.detection_difficulty="hard", "No - Detection Gap"
)
| sort -count
```

**Action Plan**:
- "No - Detection Gap" = priority for new detection rules
- "Partial" = enhance existing detections
- Document gaps in risk register

### 5. Threat Hunting by Technique

**Goal**: Proactively hunt for specific techniques

```spl
# Hunt for credential dumping attempts
index=cyber_gc_ca sourcetype=cccs:alerts mitre_techniques{}.id="T1003"
| append [
    search index=security sourcetype=windows:security EventCode=10 
        TargetImage="*lsass.exe"
    | eval technique="T1003"
  ]
| stats count by technique, source
```

### 6. Executive Reporting

**Goal**: MITRE-based threat landscape summary

```spl
index=cyber_gc_ca sourcetype=cccs:alerts earliest=-7d
| stats count as total_alerts,
        dc(mitre_techniques{}.id) as unique_techniques,
        avg(mitre_threat_score) as avg_threat,
        count(eval(mitre_severity="critical")) as critical,
        count(eval(exploit_mentioned="true")) as active_exploits
        by _time span=1d
| eval avg_threat=round(avg_threat, 1)
```

### 7. Correlation with SIEM/EDR

**Goal**: Match CCCS techniques to internal alerts

```spl
# Splunk ES Example
index=cyber_gc_ca sourcetype=cccs:alerts mitre_techniques{}.id=*
| join type=inner mitre_techniques{}.id 
    [search index=notable 
     | eval mitre_techniques{}.id=mitre_technique_id]
| table _time, title, mitre_techniques{}.id, notable_event_title, urgency
```

## Best Practices

### For SOC Teams
1. **Start Small**: Enable 1-2 critical alerts, monitor for false positives
2. **Daily Review**: Check MITRE dashboard first thing each morning
3. **Technique Library**: Build playbooks for top 10 techniques
4. **Correlation Rules**: Create detections for high-frequency techniques
5. **Training**: Use real CCCS alerts in tabletop exercises

### For Threat Intelligence
1. **Trend Analysis**: Track technique frequency over time
2. **Threat Profiles**: Build profiles of attacker groups by technique set
3. **Gap Documentation**: Maintain list of undetectable techniques
4. **Intelligence Sharing**: Brief teams on critical new techniques

### For Management
1. **Executive Dashboard**: Weekly MITRE-based threat briefings
2. **Risk Metrics**: Use threat scores for risk quantification
3. **Budget Justification**: Link tool purchases to technique coverage
4. **Compliance**: Reference MITRE in audit responses (NIST, ISO)

---

# Alert Configuration

## Pre-configured Alerts

The app includes 7 ready-to-use alerting rules:

### 1. Critical MITRE Techniques Detected
- **Triggers**: T1190, T1068, T1486, T1003, T1078
- **Schedule**: Every 15 minutes
- **Severity**: Critical (5/5)
- **Use Case**: Immediate notification of critical attack techniques

### 2. High Threat Score Alerts
- **Triggers**: Score ≥ 70
- **Schedule**: Hourly
- **Severity**: High (4/5)
- **Use Case**: Advanced persistent threats

### 3. Active Exploits with MITRE Mapping
- **Triggers**: exploit_mentioned=true + MITRE data
- **Schedule**: Every 30 minutes
- **Severity**: Critical (5/5)
- **Use Case**: Zero-day and actively exploited vulnerabilities

### 4. Initial Access Techniques Surge
- **Triggers**: 50% above 7-day average
- **Schedule**: Daily at 8 AM
- **Severity**: Medium (3/5)
- **Use Case**: Detect campaign spikes

### 5. MITRE Daily Summary Report
- **Schedule**: Daily at 9 AM
- **Severity**: Info (2/5)
- **Content**: Full intelligence summary for leadership

### 6. Ransomware Technique Detection
- **Triggers**: T1486 (Data Encrypted for Impact)
- **Schedule**: Every 30 minutes
- **Severity**: Critical (5/5)
- **Use Case**: Ransomware early warning

### 7. Lateral Movement Techniques
- **Triggers**: Lateral Movement tactics
- **Schedule**: Every 2 hours
- **Severity**: High (4/5)
- **Use Case**: Network-wide compromise indicators

## Enabling Alerts

### Via Splunk Web
1. Navigate to Settings → Searches, reports, and alerts
2. Filter by App: "Canadian Cyber Centre"
3. Click on alert name
4. Click "Enable"
5. Configure email recipients under "Trigger Actions"
6. Save

### Via Configuration File

Edit `$SPLUNK_HOME/etc/apps/cccs_alerts_app/local/savedsearches.conf`:

```ini
[CCCS - Critical MITRE Techniques Detected]
enableSched = 1
action.email = 1
action.email.to = soc-team@company.com, ciso@company.com
```

## Customizing Alert Thresholds

### Lower Threshold (More Alerts)
```ini
# In savedsearches.conf
search = ... mitre_threat_score>=50 ...  # Was 70
```

### Add Product Filter
```ini
search = ... affected_products{}.product IN ("Cisco", "Microsoft") ...
```

### Combine Multiple Conditions
```ini
search = ... mitre_threat_score>=60 exploit_mentioned=true cves{}=* ...
```

## Email Alert Templates

Alerts include comprehensive email content:

**Example Email - Critical Technique:**
```
Subject: 🔴 Critical MITRE Technique in CCCS Alert: Cisco IOS XE RCE

A critical MITRE ATT&CK technique has been detected in a new CCCS alert.

Alert: Cisco IOS XE Remote Code Execution Vulnerability
Technique: Exploit Public-Facing Application (T1190)
Severity: critical
Threat Score: 75/100

View full alert: https://www.cyber.gc.ca/en/alerts/...

Immediate action may be required.
```

---

# Use Cases & Best Practices

## Quebec Public Sector Use Cases

### For SAAQ (Société de l'assurance automobile du Québec)
**Challenge**: Monitor threats to public-facing web services
**Solution**:
```spl
index=cyber_gc_ca mitre_techniques{}.id="T1190"
| table title, affected_products{}.product, mitre_threat_score, cves{}
```
**Benefit**: Early warning of web application exploits

### For Intact Insurance
**Challenge**: Prioritize thousands of CVEs for patching
**Solution**:
```spl
index=cyber_gc_ca cves{}=* mitre_threat_score>=60
| stats values(cves{}) by affected_products{}.product, mitre_threat_score
| sort -mitre_threat_score
```
**Benefit**: Risk-based vulnerability management

### For Government Ministries
**Challenge**: Demonstrate due diligence for audits
**Solution**: Weekly executive reports using MITRE dashboard
**Benefit**: Compliance evidence (NIST, ISO 27001)

## Industry Best Practices

### 1. Integration with SIEM
- Map CCCS techniques to internal detection rules
- Create correlation searches matching external intel to internal logs
- Automate ticket creation for high-threat alerts

### 2. Vulnerability Management
- Use MITRE threat scores in CVSS calculations
- Prioritize patches for high-exploitability techniques
- Track remediation time by MITRE severity

### 3. Threat Hunting
- Use CCCS techniques as hunt hypotheses
- Search for technique indicators in historical logs
- Document findings in case management system

### 4. Incident Response
- Reference MITRE techniques in incident reports
- Build playbooks organized by technique
- Track attacker TTPs using MITRE framework

### 5. Security Awareness
- Use real CCCS alerts in tabletop exercises
- Train staff on recognizing technique indicators
- Gamify learning with MITRE technique quizzes

---

# Troubleshooting

## No Data Appearing

### Check Script Status
```bash
$SPLUNK_HOME/bin/splunk list inputstatus
```

### Test Script Manually
```bash
cd $SPLUNK_HOME/etc/apps/cccs_alerts_app/bin
python3 cccs_feed_collector.py
```
Expected: JSON output

### Check Splunk Logs
```bash
tail -f $SPLUNK_HOME/var/log/splunk/splunkd.log | grep cccs
```

### Verify Network Access
```bash
curl -I https://cyber.gc.ca/api/cccs/rss/v1/get?feed=alerts_advisories&lang=en
```
Expected: HTTP 200 OK

## No MITRE Enrichment

### Verify Enrichment Flag
```spl
index=cyber_gc_ca | stats count by mitre_enriched
```

If `mitre_enriched=false` or missing:
- Check Python version: `python3 --version` (need 3.7+)
- Test script manually: Should output JSON with `mitre_techniques` field
- Check for script errors in splunkd.log

### Low Technique Detection Rate

This is normal. CCCS alerts vary in technical detail:
- Some alerts are generic (low detection)
- Others are very specific (high detection)
- Average: 2-4 techniques per alert

## Script Errors

### Check Internal Logs
```spl
index=_internal source=*cccs_feed_collector.py*
| stats count by log_level, message
```

### Common Errors

**"Connection refused"**:
- Check firewall allows outbound HTTPS to cyber.gc.ca
- Verify proxy configuration if required

**"Permission denied" writing to local directory**:
```bash
chown -R splunk:splunk $SPLUNK_HOME/etc/apps/cccs_alerts_app/local/
chmod 755 $SPLUNK_HOME/etc/apps/cccs_alerts_app/local/
```

**"Module not found"**:
```bash
pip3 install requests --break-system-packages
```

## Hash File Issues

The hash file is now stored in the app's `local/` directory for better organization and persistence.

**Location**: `$SPLUNK_HOME/etc/apps/cccs_alerts_app/local/cccs_feed_hash.txt`

### Force Re-collection of All Alerts

To force the app to re-download and re-ingest all CCCS alerts:

```bash
rm $SPLUNK_HOME/etc/apps/cccs_alerts_app/local/cccs_feed_hash.txt
```

The next collection cycle (within 15 minutes) will treat all alerts as new and re-ingest them with fresh MITRE enrichment.

### Check Hash File

```bash
# View current hash
cat $SPLUNK_HOME/etc/apps/cccs_alerts_app/local/cccs_feed_hash.txt

# Check file permissions
ls -l $SPLUNK_HOME/etc/apps/cccs_alerts_app/local/cccs_feed_hash.txt
```

Should be readable/writable by Splunk user.

### Fix Permissions if Needed

```bash
chown splunk:splunk $SPLUNK_HOME/etc/apps/cccs_alerts_app/local/cccs_feed_hash.txt
chmod 644 $SPLUNK_HOME/etc/apps/cccs_alerts_app/local/cccs_feed_hash.txt
```

## Dashboard Issues

### Dashboard Shows No Data

1. Verify index exists:
```spl
| eventcount summarize=false index=cyber_gc_ca
```

2. Check time range (default: last 30 days)

3. Verify data exists:
```spl
index=cyber_gc_ca | head 10
```

### MITRE Dashboard Empty

Check if enrichment is enabled:
```spl
index=cyber_gc_ca mitre_enriched=true | head 1
```

If no results, wait 15 minutes for first enriched alert.

## Performance Issues

### Slow Searches

Add to props.conf for better performance:
```ini
[cccs:alerts]
INDEXED_EXTRACTIONS = json
```

### High Memory Usage

Reduce collection interval:
```ini
[script://...]
interval = 1800  # 30 minutes instead of 15
```

---

# Technical Architecture

## Data Flow

```
1. CCCS Feed (cyber.gc.ca API)
   ↓
2. cccs_feed_collector.py (Scripted Input)
   ↓ [SHA256 hash check]
3. Parse XML/HTML
   ↓
4. Extract Fields (CVEs, products, recommendations)
   ↓
5. MITRE ATT&CK Enrichment
   ├─ Keyword matching (MITRE_MAPPINGS)
   ├─ Explicit technique detection (regex)
   ├─ Threat score calculation
   └─ Severity classification
   ↓
6. JSON Output to Splunk
   ↓
7. Index-time Lookup Enrichment (transforms.conf)
   ↓
8. Indexed in cyber_gc_ca
   ↓
9. Available in Dashboards & Searches
```

## Component Architecture

```
┌─────────────────────────────────────┐
│  CCCS Feed (cyber.gc.ca/api)       │
│  - RSS feed (primary)               │
│  - Atom feed (fallback)             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Scripted Input (every 15 min)     │
│  - cccs_feed_collector.py           │
│  - MITRE enrichment engine          │
│  - Dual-layer deduplication:        │
│    * Feed hash (SHA256)             │
│    * Event JSON hash + timestamp    │
│  - 31-day retention with cleanup    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Hash Storage (local/)              │
│  - cccs_feed_hash.txt               │
│  - cccs_event_hashes.json           │
│    {"hash": "timestamp", ...}       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Splunk Index                       │
│  - cyber_gc_ca                      │
│  - JSON parsing (props.conf)        │
│  - Lookup enrichment (transforms)   │
└──────────────┬──────────────────────┘
               │
        ┌──────┴────────┐
        ▼               ▼
  ┌──────────┐   ┌─────────────┐
  │Dashboards│   │Saved Searches│
  │  - CCCS  │   │  - 7 Alerts │
  │  - MITRE │   └─────────────┘
  └──────────┘
```

## File Structure

```
cccs_alerts_app/
├── bin/
│   └── cccs_feed_collector.py    # Main collector with MITRE enrichment
├── default/
│   ├── app.conf                   # App configuration
│   ├── inputs.conf                # Scripted input configuration
│   ├── props.conf                 # Field extraction & lookup
│   ├── transforms.conf            # Lookup definitions
│   ├── savedsearches.conf         # 7 alerting rules
│   └── data/
│       └── ui/
│           ├── views/
│           │   ├── overview.xml
│           │   ├── cccs_dashboard.xml
│           │   └── mitre_dashboard.xml
│           └── nav/
│               └── default.xml
├── lookups/
│   └── mitre_technique_severity.csv   # Technique metadata
├── metadata/
│   ├── default.meta               # Permissions
│   └── local.meta
├── README.md                      # Complete documentation (this file)
└── RELEASE_NOTES.md              # Version history and changelog
```

## MITRE Enrichment Engine

Located in `bin/cccs_feed_collector.py`:

### Key Functions

**`extract_mitre_techniques(alert_content)`**:
- Input: Combined text from alert fields
- Process: Keyword matching + regex for explicit references
- Output: Dictionary with techniques, tactics, scores

**`send_to_splunk(events)`**:
- Input: Parsed alert events
- Process: Applies MITRE enrichment to each event
- Output: JSON events with MITRE fields

### Performance Characteristics

- Enrichment time: < 50ms per alert
- Memory usage: Negligible (<1MB)
- CPU usage: Minimal (keyword matching)
- Storage impact: +5KB per enriched alert

---

# Upgrade Guide

## From Version 2.x to 3.0

### Pre-Upgrade Checklist

- [ ] Backup current app directory
- [ ] Document custom configurations
- [ ] Note enabled alerts and schedules
- [ ] Export important dashboards (if modified)

### Upgrade Steps

1. **Install New Version**:
   ```
   Apps → Manage Apps → Install app from file
   Upload: cccs_alerts_app_v3.0_mitre.tar.gz
   ```

2. **Restart Splunk** (if prompted)

3. **Verify Installation**:
   ```spl
   index=cyber_gc_ca | stats count by mitre_enriched
   ```

4. **Review New Alerts**:
   - Settings → Searches, reports, and alerts
   - Filter by App: "Canadian Cyber Centre"
   - Enable desired alerts

5. **Test MITRE Dashboard**:
   - Navigate to: MITRE ATT&CK Analysis
   - Verify data appears (may take 15 min for first enriched alert)

### Breaking Changes

**None** - Version 3.0 is fully backward compatible:
- All existing searches continue to work
- Previous data remains intact
- New MITRE fields added transparently
- No configuration changes required

### What's Preserved

✅ All historical alert data  
✅ Custom dashboard modifications  
✅ Local configuration overrides  
✅ Scheduled search configurations  

### What's New

✅ MITRE enrichment fields  
✅ New MITRE dashboard  
✅ 7 pre-configured alerts  
✅ Technique lookup table  
✅ Enhanced documentation  

### Post-Upgrade Recommendations

1. **Enable Critical Alerts**:
   - "CCCS - Critical MITRE Techniques Detected"
   - Configure email recipients

2. **Review MITRE Dashboard**:
   - Familiarize team with new visualizations
   - Set as default view if desired

3. **Update Runbooks**:
   - Add MITRE techniques to incident response procedures
   - Create playbooks for top 10 techniques

4. **Train Team**:
   - Schedule demo of MITRE features
   - Distribute MITRE_USAGE_GUIDE.md

---

# Support & Resources

## Documentation

- **README.md**: Quick start and basic usage
- **MITRE_USAGE_GUIDE.md**: Comprehensive 50+ page guide (this document)
- **RELEASE_NOTES.md**: Version history and changes
- **Splunk Answers**: Search "CCCS alerts app"

## Official Resources

- **CCCS Website**: https://www.cyber.gc.ca/
- **CCCS Feed**: https://www.cyber.gc.ca/api/cccs/atom/v1/get?feed=alerts_advisories&lang=en
- **MITRE ATT&CK**: https://attack.mitre.org/
- **MITRE Navigator**: https://mitre-attack.github.io/attack-navigator/

## Internal Support

For issues or questions:

1. **Check Troubleshooting Section** (above)
2. **Review Internal Logs**:
   ```spl
   index=_internal source=*cccs* OR source=*splunkd.log* "cccs"
   ```
3. **Test Script Manually**:
   ```bash
   cd $SPLUNK_HOME/etc/apps/cccs_alerts_app/bin
   python3 cccs_feed_collector.py
   ```
4. **Contact Splunk Administrator**

## Community & Contribution

**Created by**: Alexandre Argeris  
**Version**: 3.1.0  
**License**: Open Source

**Roadmap Contributions Welcome**:
- MITRE sub-technique support (T1234.001)
- Threat actor group mapping
- MITRE Navigator integration
- ML-based technique confidence scoring

## Version Information

**Current Version**: 3.1.0  
**Release Date**: December 18, 2025  
**Package**: cccs_alerts_app_v3.1.tar.gz  
**Status**: ✅ Production Ready  

---

## Quick Reference Card

### Most Common Searches

```spl
# View all alerts
index=cyber_gc_ca sourcetype=cccs:alerts

# Critical threats
index=cyber_gc_ca mitre_severity=critical

# Active exploits
index=cyber_gc_ca exploit_mentioned=true

# Specific technique
index=cyber_gc_ca mitre_techniques{}.id="T1190"

# High threat score
index=cyber_gc_ca mitre_threat_score>=70

# Daily summary
index=cyber_gc_ca earliest=-24h
| stats dc(mitre_techniques{}.id) as techniques,
        avg(mitre_threat_score) as avg_score
```

### Key Fields

- `mitre_threat_score`: 0-100 threat score
- `mitre_severity`: critical/high/medium/low
- `mitre_techniques{}.id`: T1234 format
- `mitre_tactics{}`: Tactic names
- `exploit_mentioned`: true/false
- `cves{}`: CVE identifiers

### Dashboard Navigation

```
Canadian Cyber Centre → Overview (default)
Canadian Cyber Centre → CCCS Alerts
Canadian Cyber Centre → MITRE ATT&CK Analysis (NEW)
Canadian Cyber Centre → Search
```

### Alert Configuration

```
Settings → Searches, reports, and alerts
Filter: App = "Canadian Cyber Centre"
Enable desired alerts
Configure: Email recipients
```

---

**End of Documentation**

For the latest updates and release notes, see **RELEASE_NOTES.md**.

**Version**: 3.1.0 | **Date**: December 18, 2025 | **Status**: Production Ready ✅
