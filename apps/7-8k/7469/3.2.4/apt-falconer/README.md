# APT Falconer

**APT Falconer** is a signal-driven threat hunting and investigation framework for Splunk, designed to help analysts **understand the “why” behind detections**, not just the alert itself.

Built around the **MITRE ATT&CK® framework**, APT Falconer provides curated **Signals**, rich **Contextual pivots**, and role-aligned dashboards that guide analysts from **initial indication → validation → investigation → outcome**.

APT Falconer is suitable for:
- Security workshops and analyst training
- Production SOC environments
- Detection engineering and threat hunting programs
- Customers with partial or evolving data coverage

---

## Core Concepts

### 1. Signals (What Might Be Happening)

**Signals** are behavioral indicators aligned to ATT&CK tactics and techniques.

Unlike traditional detections:
- Signals are **contextual**, not binary alerts
- They are designed to surface **interesting behavior**, even when data is incomplete
- Multiple weak signals can build analyst confidence during an investigation

Examples:
- PowerShell downloading content from external services
- Rare processes communicating over common ports
- Registry changes associated with persistence mechanisms
- DNS patterns indicative of tunneling or dynamic resolution

Signals are intentionally:
- **Readable** (clear SPL)
- **Composable** (usable in dashboards, hunts, or ES correlation searches)
- **Workshop-safe** (graceful when no data exists)

---

### 2. Contexts (Why It Matters)

**Contexts** answer the analyst’s next question.

Every meaningful field (IP, host, user, process, domain, hash) can be used as an **entry point** into deeper investigation via:
- Context menus
- Drilldowns
- Linked dashboards
- Time-bound pivots

Contexts allow analysts to:
- Move laterally across data sources
- Pivot without rewriting searches
- Maintain investigative flow without “dashboard hopping”

Examples:
- Right-click an IP → pivot to network, DNS, and process history
- Right-click a process → view execution lineage, downloads, and network use
- Right-click a user → view authentication, process execution, and registry activity

---

### 3. Workspaces (Who It’s For)

APT Falconer is organized by **analyst role**, not data source.

#### Host Analyst
Focuses on:
- Process execution
- PowerShell and script activity
- Registry changes
- Persistence mechanisms
- Living-off-the-land techniques

Data sources commonly used:
- Windows Event Logs
- Sysmon
- Endpoint datamodels

#### Network Analyst
Focuses on:
- DNS, HTTP, SSL, and connection behavior
- Command & Control techniques
- Ingress tool transfer
- Port and protocol misuse

Data sources commonly used:
- Zeek / Bro
- Suricata / IDS
- Network Traffic datamodels

#### Intel Analyst
Focuses on:
- IOC management and enrichment
- Threat intelligence correlation
- Analyst-driven tagging and context building

(IOC Management and enrichment capabilities may be extended depending on deployment.)

---

## MITRE ATT&CK Coverage

APT Falconer includes dashboards aligned to ATT&CK tactics, including but not limited to:

- Reconnaissance
- Resource Development
- Initial Access
- Execution
- Persistence
- Privilege Escalation
- Stealth
- Defense Impairment
- Credential Access
- Discovery
- Lateral Movement
- Collection
- Exfiltration
- **Command and Control**

Each tactic dashboard:
- Includes all primary techniques and sub-techniques
- Uses real SPL where data is commonly available
- Falls back gracefully when data is missing
- Provides embedded explanations for analyst education

---

## Design Philosophy

APT Falconer is intentionally built to:

- **Teach analysts how to think**, not just what to click
- Be useful even without “perfect” data
- Avoid brittle, signature-only logic
- Encourage hypothesis-driven investigation
- Complement (not replace) Splunk Enterprise Security

It is **not**:
- A replacement for ES correlation searches
- A threat intel feed
- A single-alert detection engine

It **is**:
- A hunting companion
- A detection development aid
- A SOC workflow accelerator

---

## New & Notable Features

### v3.2.2 Release Candidate Status
APT Falconer core v3.2.2 is the current release-candidate build for the core app.

Release-candidate highlights:
- Production ATT&CK dashboards were stabilized on the original XML views rather than the `*_v2.xml` implementation files.
- ATT&CK dashboard base searches now use the established safe `dest` / `user` / `process` scoping pattern.
- Broken `falconer_attack_scope_*` dashboard macro experiments were removed from the production dashboard path.
- Unsafe inline `$dest`, `$user`, and `$process` dashboard-token usage was removed from ATT&CK technique JSON content.
- Malformed quoted token assignment behavior such as `scope_dest=\"$dest|s$\"` was corrected to the standard unquoted pattern.
- Persistence, Execution, and Credential Access technique labels were cleaned so duplicate-looking panels no longer obscure distinct analytics.
- Execution `T1675: ESXi Administration Command` was corrected to use bounded search logic appropriate for dashboard execution.
- Credential Access `T1003: OS Credential Dumping [Share Access]` was repaired so the standalone search and timeline behave correctly in the browser UI.
- Resource Development content was rebuilt so all 50 technique entries now use technique-aligned queries and timelines instead of one repeated filler search.
- Production ATT&CK dashboards were rechecked with browser/headless validation plus JSON, XML, and JavaScript static validation.

### v3.2 Release Focus
APT Falconer v3.2 updates the ATT&CK experience for MITRE ATT&CK Enterprise v19 while preserving the signal-driven investigation workflows introduced in v3.1.

Release highlights:
- ATT&CK Enterprise v19 technique lookup generated from the official MITRE STIX release
- New Resource Development, Stealth, and Defense Impairment dashboards
- Defense Evasion navigation replaced by the v19 Stealth and Defense Impairment tactics
- MITRE context pivots updated for Resource Development, Stealth, and Defense Impairment
- ATT&CK v19 Detection Strategy and Analytic objects used to populate detection guidance in the documentation lookup
- Repeatable `tools/update_attack_v19.py` updater for future ATT&CK data refreshes
- Signal-to-hunt workflows with accurate hunt signal counts
- Hunt-scoped Signal Story workbench with direct hunt browsing, filtering, paging, notes, disposition, and ES note handoff
- Enterprise Security adaptive response actions for seeding Falconer hunts with typed investigation context and sending Falconer notes back to ES
- Owner metadata for new hunts/signals created through right-click workflows, standalone Add Signal, and ES adaptive response actions
- Consolidated public navigation that favors canonical dashboard routes over implementation suffixes
- Setup support for all shipped index-scope macros used by the app
- Lightweight release-readiness validation for dashboard assets, nav links, REST handlers, alert action scripts, KVStore lookups, context actions, and setup macro coverage

Validated v3.2 workflows include:
- New v19 tactic dashboards and right-click MITRE context pivots
- ES notable/finding to Falconer hunt creation with deduplicated multi-entity seeding
- Hunt breadcrumb grouping and duplicate signal prevention
- Signal Story notes and disposition capture
- Signal Story direct `Send Notes to ES`
- ES adaptive response `Falconer Send Notes to ES` writing Falconer notes back to notable/finding History

### Signal-First Dashboards
Dashboards emphasize *behavioral signals* rather than pass/fail alerts.

### Context-Driven Investigation
Consistent context menus and pivots across host, network, and intel views.

### Enterprise Security Hunt Seeding
Enterprise Security findings can seed Falconer hunts without discarding the context ES already provided.

Current seeding behavior preserves:
- the durable ES finding correlation key (`source_guid` when available)
- hunt-level root context such as rule/search name, tactic, technique, technique ID, event IDs, host, users, groups, and a compact notable summary
- multiple typed signals for the same finding, such as host, user, group, technique, and signature IDs
- idempotent reseeding so rerunning the action enriches the hunt instead of duplicating signals

See [docs/ES_TO_FALCONER_SEEDING.md](../../docs/ES_TO_FALCONER_SEEDING.md) for the extraction rules, privacy behavior, and local test fixture.

### Workshop-Safe by Design
Dashboards render cleanly even when data is sparse or unavailable.

### Base Search & Performance Optimizations
Where possible, dashboards leverage:
- Base searches
- Data models
- Reduced search duplication

### Analyst Education Built-In
Each technique panel includes:
- ATT&CK-aligned explanations
- “Why this matters” context
- Clear investigative intent

### Canonical UI Surface
APT Falconer may still carry older dashboard generations and compatibility views in the repo.

Current intended direction:

- Canonical dashboard names such as `signals_management`, `command_and_control`, and ATT&CK tactic names define the public user experience
- Navigation should prefer canonical routes over older or implementation-specific equivalents
- User-facing labels should not expose implementation suffixes such as `V2`
- Legacy views may remain in the repo temporarily for compatibility, but they should not define the primary product experience

---

## Deployment Notes

- APT Falconer does **not** require Splunk Enterprise Security
- Works best with CIM-aligned data, but does not strictly require it
- Designed to coexist with ES, custom detections, and third-party tools

### Runtime State vs Vendor Defaults

APT Falconer uses two different storage roles on purpose:

- **Vendor defaults / seed data** ship with the app as versioned files in `lookups/`
- **Runtime state** lives in Splunk KV Store and is the active source of truth for mutable platform features

Current intended model:

- Context action defaults are shipped with the app as vendor seed data
- Setup / upgrade flows merge those defaults into KV Store
- User-modified runtime entries are preserved and should not be overwritten during upgrades
- Dashboards, context menus, and management UIs should read the KV-backed runtime objects, not the seed files directly

This model exists to make upgrades safe for customer environments while still allowing Falconer to ship improved defaults over time.

Recommended data sources (partial list):
- Windows Event Logs
- Sysmon
- Zeek / Bro
- Network Traffic logs
- PowerShell Operational logs

### Setup Macros

The setup page manages the app's index-scope macros so deployments can replace broad defaults such as `index=*` with environment-specific index constraints.

Managed macros include:
- `zeek_index`, `rita_index`, `snort_index`, `suricata_index`, `stream_index`
- `sguild_index`, `ossec_index`
- `win_index`, `nix_index`, `scripts_index`, `sysmon_index`
- `cloudtrail_index`, `aws_index`, `azure_index`, `esxi_index`, `o365_index`

### Threat Intel Workflow

Threat Intel surfaces are intended to support three related workflows:
- `falconer_intel_hunt`: triage observed Zeek intel matches and promote meaningful entities into Falconer hunts
- `intel_detection_builder`: stage and publish Falconer-owned local intelligence into Falconer local intel lookups
- `pivot_threatintel`: pivot a single value across Falconer local intelligence, published builder entries, and Falconer custom feeds

The legacy `intel_dashboard` and bulk upload views remain available for compatibility, but the preferred v3.1 authoring path is the Intel Detection Builder.

---

## Intended Audience

- SOC Analysts (Tier 1–3)
- Threat Hunters
- Detection Engineers
- Security Architects
- Workshop instructors and students

---

## Disclaimer

APT Falconer provides **analytical visibility**, not guarantees of malicious activity.  
All signals should be evaluated within the context of your environment.

MITRE ATT&CK® is a registered trademark of The MITRE Corporation.

---

## Credits

APT Falconer is authored and maintained by **Brent Matlock**  
Built with a focus on real-world SOC operations, analyst experience, and practical threat hunting.

---

## Feedback & Contributions

Feedback, suggestions, and improvements are welcome.  
APT Falconer is designed to evolve alongside detection maturity and analyst needs.
