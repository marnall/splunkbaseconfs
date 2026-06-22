# Sophos Central CEF Add-on for Splunk

## Overview
A CIM v5 compliant Splunk Technical Add-on (TA) for parsing Sophos Central events
delivered via CEF syslog to a Heavy Forwarder. This TA provides complete field
extractions, sub-sourcetype routing, and full CIM data model tagging for use with
Splunk Enterprise Security.

## What Makes This TA Different
- Built specifically for **CEF syslog delivery** (not API polling)
- Handles the **syslog header prefix** (`May 1 17:46:49 x.x.x.x CEF:...`)
- **Sub-sourcetype routing** splits events automatically at index time
- **CIM v5 compliant** — works with current Splunk ES data models
- Handles **multi-line CEF events** from Sophos Central
- Covers **Investigation/Case events** — not supported by any other TA

## Supported Event Types

| Sourcetype | Description |
|---|---|
| `sophos:cef:central` | Base — all incoming CEF syslog |
| `sophos:cef:central:threat` | Endpoint threat detections (Intercept X) |
| `sophos:cef:central:investigation` | Case management / investigation events |
| `sophos:cef:central:firewall` | Firewall gateway up/down events |

## CIM Data Model Mapping

| Sourcetype | CIM Data Model | Tags |
|---|---|---|
| `sophos:cef:central:threat` | Malware, IDS | malware, attack, ids |
| `sophos:cef:central:investigation` | Incident Management | incident |
| `sophos:cef:central:firewall` | Network Traffic | network, communicate |
| WebControlViolation events | Web | web, proxy |

## Prerequisites
- Sophos Central configured to send CEF syslog to your Heavy Forwarder
- Splunk Heavy Forwarder (Linux recommended)
- Port 514 UDP/TCP open from Sophos Central to Heavy Forwarder
- Splunk Common Information Model (CIM) v5 app installed on Search Heads

## Installation
1. Copy the TA to `/opt/splunk/etc/apps/` on your Heavy Forwarder
2. Copy the TA to `/opt/splunk/etc/apps/` on your Search Head(s)
3. Configure `inputs.conf` on the Heavy Forwarder (see below)
4. Restart Splunk on all systems

## inputs.conf Configuration
[udp://514]
sourcetype = sophos:cef:central
index      = your_security_index
connection_host = dns

OR for TCP:
[tcp://514]
sourcetype = sophos:cef:central
index      = your_security_index
## Extracted Fields Reference

### Threat Events
| Field | Description |
|---|---|
| `detection_rule` | Sophos detection rule name |
| `attack_type` | Attack category |
| `mitre_tactic` | MITRE ATT&CK tactic |
| `mitre_techniques` | MITRE ATT&CK techniques |
| `suppressed` | Whether the alert was suppressed |
| `external_id` | Unique event ID |
| `device_id` | Device UUID |
| `device_facility` | computer or server |

### Investigation Events
| Field | Description |
|---|---|
| `case_id` | Case reference ID |
| `case_status` | Current case status |
| `case_type` | Type of investigation |
| `initial_detection_rule` | Rule that triggered the case |
| `initial_detection_severity` | Severity score of initial detection |
| `escalated` | Whether the case was escalated |
| `alert_count` | Number of alerts in the case |
| `assigned_to` | Assigned analyst |

## Changelog
### v1.0.0 (2026-05-05)
- Initial release
- CEF syslog parsing with syslog header support
- Sub-sourcetype routing for Threat, Investigation, Firewall events
- CIM v5 compliant tagging
- Full MITRE ATT&CK field extractions

## Support
Raise issues via Splunkbase comments or contact: contact@binaryglobal.com

## License
Apache License 2.0
