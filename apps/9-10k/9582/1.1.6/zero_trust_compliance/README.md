# Zero Trust Compliance & Integrated Master Schedule (IMS) Splunk App

[![Splunk Cloud Precert Ready](https://img.shields.io/badge/Splunk-Cloud%20Certified-blue.svg)](https://splunkbase.splunk.com/)
[![DoD ZTA Compliance](https://img.shields.io/badge/DoD%20ZTA-7%20Pillars-green.svg)](https://dodcio.defense.gov/)
[![Security Standards](https://img.shields.io/badge/Security-IL5%20%7C%20GovCloud-orange.svg)](https://aws.amazon.com/compliance/)

An open-source, enterprise-grade Splunk Application built for **Department of Defense (DoD)** and federal organizations to automate **Zero Trust Architecture (ZTA) compliance tracking**, **Agile Story & Kanban management**, **Integrated Master Schedule (IMS) Critical Path calculations**, and **Proof of Delivery (PoD) cryptographic verification**.

---

## 🏛️ Key Capabilities

### 1. Zero Trust 7-Pillar Continuous Compliance Matrix
- Complete coverage of DoD Zero Trust Reference Architecture pillars:
  1. **User (Identity)**
  2. **Device**
  3. **Network & Environment**
  4. **Applications & Workloads**
  5. **Data**
  6. **Automation & Orchestration**
  7. **Visibility & Analytics**
- Real-time KPI radial gauges for Compliant %, Working %, Pending %, and Not Compliant gaps.
- Persistent state management via **Splunk KV Store (MongoDB)** replacing legacy CSV lookups.

### 2. Agile Kanban & Stories Engine
- Interactive Kanban workflow: `Backlog` ➔ `In Progress` ➔ `In Review (Assessor)` ➔ `Done / Compliant`.
- Dynamic story allocation with **Story Points**, **Sprint Cycles**, **WBS Parent Codes**, and **Blocker tracking**.
- **Optimistic UI:** Instant card updates with automatic snapback rollback on failure.

### 3. Integrated Master Schedule (IMS) & Critical Path Engine
- **Custom Search Command (`| getcriticalpath`):** High-performance server-side DAG Critical Path Method (CPM) using Kahn's topological sort.
- **Cycle Detection:** Automatically intercepts circular dependencies with structured error diagnostics.
- Real-time Schedule Performance Index (SPI), Early/Late dates, and Float/Slack calculation.

### 4. Proof of Delivery (PoD) Vault & AO Evidence Exporter
- Direct linkage of ZTA requirements to cryptographic SHA-256 artifact hashes, STIG scan logs, and S3 URIs.
- Multi-framework mapping (`governance_policy_id`) supporting DoD ZTA, NIST SP 800-53 Rev 5, SOC 2, and FedRAMP High.
- Non-repudiation audit trail recorded immutably to `index=_internal sourcetype=zerotrust_audit`.

### 5. MLTK Predictive Clustering & Outlier Detection
- **KMeans Clustering (`| fit KMeans k=4`):** Groups controls into maturity tiers based on status, disruption score, and tool coverage.
- **DBSCAN Anomaly Detection (`| fit DBSCAN`):** Isolates high-risk architecture gaps and missing tooling blind spots.

### 6. AWS-DFD Architecture Visualizer
- Ingress/egress topology mapping between Policy Decision Points (PDP), Policy Enforcement Points (PEP), and GovCloud trust boundaries.

---

## 📦 KV Store Collections (`default/collections.conf`)

| Collection Name | Purpose | Key Fields |
|---|---|---|
| `zt_compliance_items` | Core 7-Pillar ZTA controls | `ref`, `pillar`, `status`, `completion_pct`, `disruption_score`, `is_deleted` |
| `zt_agile_stories` | Kanban stories & sprints | `story_id`, `ref`, `parent_wbs_code`, `sprint`, `status`, `story_points` |
| `zt_milestones_ims` | WBS & IMS schedule | `milestone_id`, `wbs_code`, `predecessor_ids`, `duration_days`, `status` |
| `zt_evidence_pod` | Cryptographic evidence vault | `evidence_id`, `ref`, `hash_sha256`, `governance_policy_id`, `last_verified_at` |

---

## 🔌 Custom Python REST Endpoints

All endpoints enforce Session RBAC (`self.getSessionKey()`), regex input sanitization, optimistic concurrency locking, and immutable audit trails:
- `/services/zt_compliance/zt_compliance_handler`: CRUD operations on compliance items.
- `/services/zt_compliance/zt_pod_handler`: Cryptographic evidence artifact vault.
- `/services/zt_compliance/zt_stories_handler`: Agile Kanban story management.

---

## 🛠️ Build & Release Automation

```bash
# Run automated verification test suite & CPM checks
make test

# Seed / re-align 152 activities from DoD Roadmap v1.1
make seed

# Build whitelisted Splunk App release package (.spl)
make package

# Build, test, and assemble certified release tarball
make release

# Run Splunk AppInspect (Cloud Precertification)
make inspect
```

---

## 📚 Knowledge Base & Release Tracking
- **[CHANGELOG.md](file:///home/suhlabs/projects/suhlabs/Zero%20Trust%20Compliance/CHANGELOG.md)**: Detailed changelog of all versions, features, and security patches.
- **[RELEASE_TRACKING.md](file:///home/suhlabs/projects/suhlabs/Zero%20Trust%20Compliance/RELEASE_TRACKING.md)**: Release tracking dashboard documenting **What Was Done** vs. **What Is Next** across FY2027 DoD milestones.

---

## ⚓ Enterprise & Enclave Integrations (VRAM / eMASS)
- **VRAM Integration Notice:** Because VRAM (Navy Vulnerability Remediation Asset Manager) is a proprietary enterprise/Navy vulnerability management system, direct live API access is controlled by enclave authorities. The app supports VRAM integration via **exported data mapping (CSV / JSON ingestion into `index=vuln sourcetype=vram:asset:csv`)** or through customer-authorized reverse API proxy connectors, ensuring flexible telemetry ingestion without assuming out-of-the-box native connectivity.
- **eMASS Integration:** Supported via PoD artifact export packages and REST connectors for POA&M status synchronization.

---

## 🛡️ Security & Air-Gapped Compliance
- **Zero CDN Policy:** 100% offline and air-gapped ready for SCIF and SIPR environments.
- **Soft Deletes:** Preserves audit integrity for Authorizing Officials without orphan records.
- **Input Sanitization:** Whitelist regex matching prevents path traversal and injection sinks.
- **ISSO Override Protection:** Tamper-proof manual locks prevent automated scans from overwriting human-vetted statuses.

