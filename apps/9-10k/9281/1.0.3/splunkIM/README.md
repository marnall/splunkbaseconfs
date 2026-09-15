# 🚨 Incident Management for Splunk (`splunkIM`)

[![Release Version](https://img.shields.io/badge/version-v1.0.3-blue.svg)](https://github.com/o11yworks/SplunkIM)
[![Splunk Compatibility](https://img.shields.io/badge/Splunk-Enterprise%208.0%2B%20%7C%20Cloud-orange.svg)](https://github.com/o11yworks/SplunkIM)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://opensource.org/licenses/Apache-2.0)
[![License Cost: 0%](https://img.shields.io/badge/License%20Cost-0%25%20(Summary%20Indexed)-brightgreen.svg)](https://github.com/o11yworks/SplunkIM)

A lightweight, universal incident response platform built natively for Splunk Core and Splunk Cloud Platform. It acts as a central Incident Command Console that consolidates alert signals, anomalies, and problem notifications from diverse observability sources — including native **Splunk Saved Searches**, **Dynatrace® Davis AI Problems**, **Datadog® Monitors**, **AWS® CloudWatch Alarms**, **Azure® Monitor**, and **Security Findings** — into unified, 24-hour incident episodes.

> ℹ️ **Trademark & Compatibility Disclaimer**  
> *All product names, logos, brands, trademarks, and registered trademarks (such as Dynatrace®, Datadog®, ServiceNow®, PagerDuty®, AWS®, Azure®) are property of their respective owners. All company, product, and service names used in this documentation are for identification and compatibility purposes only. Use of these names, logos, and brands does not imply endorsement or official affiliation.*

---

## 📖 Technical Documentation Suite

All technical guides, architecture specifications, and administration playbooks are hosted online in the official repository:

| Document Guide | Target Role | Primary Focus |
| :--- | :--- | :--- |
| 📖 **[User & Operator Guide](https://github.com/o11yworks/SplunkIM/blob/main/docs/USER_GUIDE.md)** | Analysts & Admins | Complete user manual, 7-section setup guide, triage workflows, MTTA/MTTR metrics, and troubleshooting. |
| 🏛️ **[Architecture & Design Guide](https://github.com/o11yworks/SplunkIM/blob/main/docs/ARCHITECTURE_AND_DESIGN.md)** | Architects & Leads | System topology, summary indexing data flow, KV Store state engine, deduplication MD5 logic, and state machine transitions. |
| ⚙️ **[Configuration Reference](https://github.com/o11yworks/SplunkIM/blob/main/docs/CONFIGURATION_REFERENCE.md)** | Developers & Admins | Stanza-by-stanza reference for `collections.conf`, `transforms.conf`, `savedsearches.conf`, `macros.conf`, and `app.conf`. |
| 🛠️ **[Administration & Troubleshooting](https://github.com/o11yworks/SplunkIM/blob/main/docs/ADMINISTRATION_AND_TROUBLESHOOTING.md)** | Splunk Admins & SREs | Operational playbooks, diagnostic SPL queries, KV Store maintenance/backups, SHC captain execution, and queue triage. |

---

## ✨ Key Features

- ⚡ **Zero-License Cost Aggregation**: Ingests raw alerts from summary indexes (`index=summary marker="app=splunkIM"`), which are 100% license-exempt in Splunk Enterprise.
- 🔄 **Stateful KV Store Tracking**: Tracks incident lifecycle states (`New`, `Active`, `In Progress`, `Resolved`, `Closed`) using high-performance KV Store collections (`collections.conf`).
- ⏱️ **Auto-Reopen & Deduplication Rules**: Automatically groups duplicate alerts within a 24-hour window and reopens resolved incidents if recurring alerts hit within the SLA window.
- 📜 **Auditable Incident History**: Maintains an analyst audit log (`splunkim_audit_log`) tracking who updated status, owner, or notes for compliance & post-mortem reviews.
- 🌐 **Search Head Cluster (SHC) Ready**: Designed to run background workers safely on SHC Captain nodes without duplicate record creation.

---

## ⚡ Quick Start & Deployment Guide

### 1. Installation on Standalone Search Head
1. Download or clone this repository:
   ```bash
   git clone https://github.com/o11yworks/SplunkIM.git splunkIM
   ```
2. Move the `splunkIM` directory to `$SPLUNK_HOME/etc/apps/`:
   ```bash
   cp -r splunkIM $SPLUNK_HOME/etc/apps/
   ```
3. Restart Splunk or debug reload:
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

---

### 2. Installation on Search Head Clusters (SHC)
1. Copy `splunkIM` to the SHC Deployer node:
   ```bash
   cp -r splunkIM $SPLUNK_HOME/etc/shcluster/apps/
   ```
2. Push the cluster bundle from the Deployer:
   ```bash
   $SPLUNK_HOME/bin/splunk apply shcluster-bundle -target https://<shc-captain>:8089
   ```

---

## 📊 Summary Index Aggregation Workflow

```
[Raw Alerts & Security Searches]
           │
           ▼
[Summary Indexing (index=summary marker="app=splunkIM")]
           │  (Zero License Impact)
           ▼
[SplunkIM Background Aggregator (savedsearches.conf)]
           │  (Runs every 5 mins)
           ▼
[KV Store State Table (splunkim_incidents)]
           │
           ▼
[Analyst Dashboard UI & Incident Triage]
```

---

## 📖 Useful SPL Macros

- **List All Active Incidents**:
  ```spl
  | `splunkim_list_incidents`
  | search status="New" OR status="Active"
  ```

- **Review Analyst Audit Trail**:
  ```spl
  | `splunkim_list_audit_logs("*")`
  | stats count by user, action
  ```

---

## 🛡️ Maintenance & Diagnostics

- **Backup KV Store Collections**:
  ```bash
  $SPLUNK_HOME/bin/splunk backup kvstore -app splunkIM
  ```

- **Diagnostic Manual**:
  Review the [Administration & Troubleshooting Manual](./docs/ADMINISTRATION_AND_TROUBLESHOOTING.md) for KV Store cleanup, summary index verification, and cluster troubleshooting.

---

## 📬 Contact & Maintainer Information

- **Author**: Venkatesh Geriti / o11yworks Architecture Team
- **Contact**: `venkatesh.o11y@gmail.com`
- **GitHub Repository**: [https://github.com/o11yworks/SplunkIM](https://github.com/o11yworks/SplunkIM)
- **License**: Apache-2.0
