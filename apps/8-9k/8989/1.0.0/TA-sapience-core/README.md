# Sapience Core Technology Add-on for Splunk

Version 1.0.0 | Sapience Technologies

## Overview

This Technology Add-on (TA) enables Splunk to ingest, parse, and normalise security events from Sapience Core — the autonomous Windows endpoint hardening and self-healing agent. Events are delivered via RFC-5424 syslog with ArcSight Common Event Format (CEF) payload.

Once installed, Sapience Core events are available in the following Splunk CIM data models:
- **Intrusion Detection** — all tamper and drift events
- **Malware** — credential dumping tool detection (TR-008)
- **Authentication** — NTLM pass-the-hash indicators (TR-011)
- **Endpoint** — process, service, and scheduled task events
- **Network Sessions** — lateral movement network events
- **Change** — all auto-remediation actions

---

## Requirements

- Splunk Enterprise 8.0 or later (or Splunk Cloud)
- Splunk Enterprise Security 6.0+ (for ES correlation searches, optional)
- Sapience Core 1.0+ installed on monitored endpoints

---

## Installation

### Step 1 — Install the TA on your Splunk search head and indexer

**Via Splunk Web:**
1. Navigate to Apps → Manage Apps → Install app from file
2. Upload `TA-sapience-core-1.0.0.spl`
3. Restart Splunk if prompted

**Via CLI:**
```bash
$SPLUNK_HOME/bin/splunk install app TA-sapience-core-1.0.0.spl -auth admin:password
$SPLUNK_HOME/bin/splunk restart
```

### Step 2 — Configure the syslog listener

The TA includes default `inputs.conf` with:
- UDP port 514 (standard syslog)
- TCP port 1514 (reliable delivery)

To use a non-standard port, create `$SPLUNK_HOME/etc/apps/TA-sapience-core/local/inputs.conf`:
```ini
[udp://YOUR_PORT]
connection_host = ip
sourcetype = sapience:core
index = sapience
```

**Note:** If running on Linux, ports below 1024 require Splunk to run as root or use `authbind`. For enterprise deployments, use TCP 1514 or HEC (see below).

### Step 3 — Configure each Sapience Core agent to send syslog

On each monitored endpoint, call the Sapience Core REST API:

```powershell
$key = sqlite3 "$env:ProgramData\SapienceCore\agent.db" "SELECT value FROM agent_config WHERE key='api_key';"

Invoke-RestMethod -Uri "http://localhost:5001/api/v1/syslog" `
  -Method PUT `
  -Headers @{"X-Api-Key" = $key} `
  -ContentType "application/json" `
  -Body '{"host":"YOUR-SPLUNK-IP","port":514,"protocol":"udp"}'
```

For MSP deployments, automate this via your RMM tool after agent installation.

#### HTTP Event Collector (HEC) — Enterprise deployments

For large-scale deployments or Splunk Cloud, use HEC instead of syslog:

1. Enable HEC in Splunk: Settings → Data Inputs → HTTP Event Collector
2. Create a new token with sourcetype `sapience:core`
3. Use a syslog-to-HEC proxy (e.g. sc4s, syslog-ng with HEC output) to forward events

---

## Event Types

Search for Sapience Core events using named event types:

| Event Type | Description |
|---|---|
| `eventtype=sapience_event` | All Sapience Core events |
| `eventtype=sapience_detection` | Detection events only |
| `eventtype=sapience_remediation` | Auto-remediation events |
| `eventtype=sapience_credential_dump` | TR-008: Mimikatz and credential tools |
| `eventtype=sapience_lateral_movement` | TR-009/010/011: Lateral movement indicators |
| `eventtype=sapience_pass_the_hash` | TR-011: NTLM pass-the-hash |
| `eventtype=sapience_remote_service` | TR-009: Remote service installation |
| `eventtype=sapience_remote_task` | TR-010: Remote scheduled task creation |
| `eventtype=sapience_admin_account` | TR-002: Rogue administrator account |
| `eventtype=sapience_firewall_tamper` | TR-003: Firewall disabled |
| `eventtype=sapience_critical` | All Critical severity events |
| `eventtype=sapience_blocked` | All auto-remediated threats |

---

## Key Fields

| Field | Description | Example |
|---|---|---|
| `agentId` | Unique agent UUID | `edcfd2f4-c09a-46af-...` |
| `dest` | Protected endpoint hostname | `DESKTOP-CG4Q01K` |
| `clientTag` | MSP client label | `AcmeCorp-Reception` |
| `signature_id` | Detection rule ID | `TR-008` |
| `signature` | Detection description | `Credential dumping tool executed: mimikatz.exe` |
| `severity` | Normalised severity | `critical`, `high`, `medium`, `low` |
| `category` | Event category | `Process`, `Service`, `LateralMovement` |
| `affected_item` | Item key | `mimikatz.exe:4660` |
| `src_ip` | Source IP (TR-011) | `<splunk-indexer-ip>` |
| `user` | User involved | `DOMAIN\attacker` |
| `action` | Outcome | `detected`, `success`, `failure` |
| `vendor_action` | Remediation action | `REM-009` |
| `sapience_classification` | AI classification | `Malicious`, `Suspicious` |
| `sapience_confidence` | AI confidence score | `0.95` |
| `sapience_process_name` | Malicious process | `mimikatz.exe` |
| `sapience_service_name` | Affected service | `EvilService` |
| `sapience_task_name` | Affected task | `\EvilTask` |
| `sapience_subject_user` | User who made the change | `DOMAIN\attacker` |
| `sapience_auth_package` | Auth package (TR-011) | `NtLmSsp` |
| `sapience_action_id` | Remediation action ID | `REM-009` |

---

## Example SPL Searches

**All critical threats this week:**
```spl
eventtype=sapience_critical earliest=-7d
| table _time, dest, clientTag, signature, affected_item, vendor_action
| sort -_time
```

**Lateral movement by client:**
```spl
eventtype=sapience_lateral_movement earliest=-30d
| stats count by clientTag, signature_id, src_ip, user
| sort -count
```

**Threats blocked per endpoint:**
```spl
eventtype=sapience_blocked earliest=-7d
| stats count by dest, clientTag
| sort -count
```

**Pass-the-hash attempts:**
```spl
eventtype=sapience_pass_the_hash
| table _time, dest, clientTag, src_ip, user, sapience_auth_package
| sort -_time
```

**Credential dump detections:**
```spl
eventtype=sapience_credential_dump
| table _time, dest, clientTag, sapience_process_name, vendor_action, action
```

**MSP summary — all clients:**
```spl
eventtype=sapience_event earliest=-7d
| stats
    count(eval(outcome="detected")) as total_detections,
    count(eval(outcome="success")) as threats_blocked,
    dc(agentId) as endpoints
  by clientTag
| sort -threats_blocked
```

---

## Enterprise Security Integration

With Splunk ES installed, Sapience Core events automatically populate:

- **Incident Review** — critical and high severity events appear as notable events
- **Risk Analysis** — endpoint risk scores are updated on each detection
- **Threat Intelligence** — known credential dump tool hashes feed into threat intel

To enable ES notable event creation, create a correlation search in ES:
```spl
eventtype=sapience_credential_dump OR eventtype=sapience_lateral_movement
```
Set action: Create Notable Event, severity: Critical, owner: SOC Analyst.

---

## MSP Multi-Tenant Deployment

The `clientTag` field identifies which client each event belongs to. Use it to:

**Create per-client indexes:**
```ini
[udp://514]
sourcetype = sapience:core
TRANSFORMS-routing = sapience_client_routing
```

**Route by clientTag in transforms.conf:**
```ini
[sapience_client_routing]
REGEX = clientTag=(\S+)
FORMAT = index::$1
DEST_KEY = _MetaData:Index
```

**Per-client dashboards:**
Filter any search with `clientTag="AcmeCorp-Reception"` to scope to a single client.

---

## Troubleshooting

**No events appearing:**
```bash
# Check Splunk is receiving on UDP 514
netstat -an | grep 514

# Verify sourcetype assignment
index=* sourcetype=sapience:core | head 5

# Check syslog configuration on the agent
curl -H "X-Api-Key: YOUR_KEY" http://ENDPOINT:5001/api/v1/syslog
```

**Fields not extracting:**
```spl
# Verify raw event format
index=* sourcetype=sapience:core | head 1 | table _raw
```
The raw event should start with `<PRI>1 TIMESTAMP HOSTNAME SapienceCore - - - CEF:0|Sapience Technologies|Sapience Core|1.0|...`

**CEF parsing issues:**
Ensure no intermediate syslog relay is modifying the message. The TA expects the CEF payload to be intact in the syslog message body.

---

## Support

- Documentation: docs.sapience.com
- Support portal: support.sapience.com
- Email: support@sapience.com
