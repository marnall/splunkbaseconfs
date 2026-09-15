# Changelog

All notable changes to the **Zero Trust Compliance & IMS Splunk App** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.6] - 2026-08-18

### Added
- **Enterprise vs. Component Implementation Delineation**:
  - Added `implementation_scope` metadata (`Enterprise`, `Component`, `Enterprise and Component`) to `[zt_agile_stories]` KV Store collection schema, `[zt_agile_stories_lookup]`, and `lookups/zt_agile_stories.csv`.
  - Added visual scope tags (`.card-scope-badge`, `.scope-enterprise`, `.scope-component`, `.scope-shared`) to all Kanban card faces and detail modals.
  - Implemented **Swimlane: By Responsibility (Enterprise vs Component)** in `zt_kanban.xml` and `jira_board.js` separating top-level enterprise policy/ICAM from component-level technical executions.
  - Added Responsibility scope filter dropdown (`#jira-scope-select`) and quick filter badge (`[Enterprise Only]`).
- **Product Manager Acceptance Test Cases (TC-PM-01 to TC-PM-03)**:
  - Multi-User Concurrency & Optimistic Locking Test Plan (`409 Conflict` + UI auto-sync).
  - RBAC & CAC Digital Signature Stage-Gate Isolation (`403 Forbidden` for unprivileged users; 10-digit EDIPI + X.509 Subject DN + SHA-256 digest for authorized ISSO/ISSM).
  - Manual Override Persistence (`override_lock: true` non-destructive discovery protection + `🛡️ ISSO LOCKED` / `🛡️ CERTIFIED` visual badges).
- **Automated Scope Coverage Verification**:
  - Added `test_enterprise_vs_component_delineation` in `tests/test_jira_board_and_152_activities.py` ensuring 100% of 160 activities delineate responsibilities cleanly (97 Shared, 61 Component, 2 Enterprise).
- **Server-Side Session RBAC & Proof of Delivery (PoD) Guard**:
  - Upgraded `bin/zt_stories_handler.py` with server-side Splunk authentication context role introspection (`_resolve_user_roles`).
  - Added server-side PoD Evidence Guard requiring attached evidence IDs, linked SHA-256 hash digests, or authorized ISSO/ISSM CAC attestation before transitioning cards to `Done / Certified` (`HTTP 422 POD_EVIDENCE_REQUIRED`).
- **Unified Cross-Collection Write-Through Synchronization**:
  - Unified the Three Sources of Truth: mutating Agile stories now atomically synchronizes compliance status and completion percentage into `[zt_compliance_items]` and `[zt_milestones_ims]`.
  - Preserved `nist_plane`, `nist_p_components`, and `dfd_tier` across all story save operations.
- **QA Test Suite & Compliance Gates Expansion**:
  - Added 2 new automated unit tests (`test_stories_handler_server_rbac_and_pod_guard`, `test_stories_handler_cross_collection_sync_and_schema_retention`), bringing the unit test suite to 24 tests (100% pass).
  - Added QA Compliance Gate `T2-06` (PoD Evidence Mandatory Guard on Done Transition) in `bin/qa_validator_engine.py`, bringing total DoD compliance gates to 13.

---

## [1.1.5] - 2026-08-15

### Added
- **NIST SP 800-207 "P*" Three-Plane Architectural Integration**:
  - Deep bidirectional mapping of all 160 activities to core Zero Trust components: `PEP`, `PIP`, `PDP`, `PE`, `PA`, and `PAP`.
  - Structured classification across Identity Plane, Control/Policy Plane, and Infrastructure/Data Plane.
- **Enterprise Custom Search Command (CSC) Hardening**:
  - Vendored pure-Python `splunklib` into `bin/lib/` with automatic dynamic `sys.path.insert(0, LIB_DIR)` injection.
  - Explicit configuration integrity in `default/commands.conf` (`chunked = true`, `streaming = true`, `generating = true`, `python.version = python3`, `python.required = 3.13`).
  - Scoped RBAC permissions for custom commands (`[commands/getcriticalpath]`, `[commands/ztvalidate]`) in `metadata/default.meta`.
- **Splunk App Icon Contract Compliance**:
  - Generated and dimension-verified official high-contrast Zero Trust Cybersecurity Shield icons.
  - Verified exact pixel dimensions: `appIcon.png` (`36×36` px) and `appIcon_2x.png` (`72×72` px).
  - Deployed to both modern `appserver/static/` and classic SimpleXML `static/` locations to eliminate silent UI fallbacks.
- **Strict POSIX Build & Packaging Pipeline**:
  - Configured `Makefile` with `SHELL := /bin/bash` and `.SHELLFLAGS := -eu -o pipefail -c` for fail-fast pipeline execution.
  - Added automated `make vendor` target in packaging lifecycle.
  - Validated with Splunk AppInspect (Cloud Precert) with **0 errors, 0 failures, 128 successful checks**.
- **Agent Governance & Institutional Memory**:
  - Added modular rules in `.agents/rules/` (`01-environment.md`, `02-build-and-packaging.md`, `03-agent-safety.md`, `04-custom-search-commands.md`).
  - Initialized repository `LESSONS_LEARNED.md` documenting incidents LL-001 through LL-004.

### Fixed
- **Custom Search Command CLI Stdin Block (LL-001)**:
  - Removed raw script invocation of `get_critical_path.py` from `make test`, preventing `sys.stdin.read()` blocking on Splunk chunked stream protocol.
  - Verified pure in-memory algorithmic testing across all 18 unit tests (pass time ~10ms).

---

## [1.1.0] - 2026-08-15

### Added
- **DoD Zero Trust Execution Roadmap (COAs 1-3, v1.1) Complete Dataset**:
  - Full ingestion of all **152 Activities** across the 7 pillars: User (28), Device (24), Apps & Workloads (18), Data (31), Network & Environment (13), Automation & Orchestration (20), and Visibility & Analytics (18).
  - Categorized into 91 Target Level ZT (FY2027 Mandate) and 61 Advanced Level ZT activities.
  - Linked COA 1 schedule durations, predecessor/successor graph, official descriptions, numbered outcomes, and end states.
- **Sprint 0 Technical Enablers & Integration Tasks (8 Board Items)**:
  - Seeded 8 explicit data-wiring and telemetry enabler stories (`ZTA-0.1.1` to `ZTA-0.8.1`) for ACAS/Tenable, IdP/CAC, EDR/C2C, VRAM CSV, eMASS, GOTS, NetFlow, and SOAR feeds.
  - Linked as direct predecessors to Sprint 1 foundational milestones with dependency warning guards.
- **Jira Software-Style Agile Sprint Board (`zt_kanban.xml`)**:
  - Configured as the **default landing view** in `default/data/ui/nav/default.xml`.
  - 5 Visual Workflow Columns: `Backlog`, `To Do`, `In Progress`, `Testing / In Review`, `Done / Certified`.
  - Real-time Work-in-Progress (WIP) limits with visual overload alerts.
  - Backlog Commitment Point and Final Delivery Point visual demarcations.
  - Dynamic Swimlanes: Group by Pillar, COA/Phase, Priority/Expedite, Assigned Team, or Flat.
  - Flow Metrics Header Panel: Live calculation of Lead Time, Cycle Time, Throughput, and Active WIP Load.
  - 5-Tab Issue Detail Modal: Overview, DoD Outcomes (ZTOM Definition of Done), Proof of Delivery (PoD Evidence), ISSO/ISSM Stage-Gate Sign-off, and Audit History.
- **Real-Time Kanban ➔ IMS Synchronization**:
  - Dual-write KV store handler in `bin/zt_stories_handler.py` automatically updates `[zt_milestones_ims]` (`status`, `completion_pct`, `actual_start_date`, `actual_end_date`) on every card transition.
  - Triggers real-time Critical Path recalculation (`| getcriticalpath`) on the IMS Gantt view (`zt_ims_gantt.xml`) with zero manual schedule reconciliation.
- **Scrum Master Empowerment & COA Telemetry Prioritization**:
  - Added **Tab 4: COA Prioritization (Scrum Master Admin)** in the Sprint 0 Onboarding Wizard.
  - Allows Scrum Masters & PMs to select active strategy (`COA 1`, `COA 2`, `COA 3`), toggle integration feeds, and dynamically scope the discovery engine.
- **Flexible Zero Trust Telemetry & State Discovery Engine**:
  - Universal Tool Registry (`zt_tool_registry.csv`) pre-seeded with 32+ commercial, cloud-native, open-source, and DoD GOTS technologies.
  - **GOTS & Non-CIM Connector Support (Gap 1)**: Custom regex field extractions (`(?i)(?:user_id|uid)\s*=\s*(?P<user>[^\s,;]+)`), JSON paths, and field aliases.
  - **Manual Override Lock Protection (Gap 2)**: Added `override_lock` flag in KV store schema and REST handlers, paired with prominent `🛡️ ISSO LOCKED` / `🛡️ CERTIFIED` visual badges on Kanban card faces.
  - **Throttled Background Summary Cache (Gap 3)**: Discovery evaluations write to `[zt_discovery_cache]`, eliminating search concurrency load on production indexes during board refreshes.
  - **Nightly Scheduled Search**: Added `0 2 * * *` off-peak scheduled auto-discovery evaluation in `default/savedsearches.conf` using accelerated data models (`| tstats summariesonly=t`).
- **Standardized VRAM Ingestion Pipeline**:
  - Added `[vram:asset:csv]` sourcetype in `default/props.conf` with automatic field aliases (`VRAM_Asset_ID AS asset_id`, `Host_Name AS dest`, `STIG_Rule_ID AS signature_id`, etc.) for seamless Navy VRAM CSV report ingestion.
- **Dual ISSO / ISSM CAC Authentication Acceptance**:
  - Multi-persona selector in `zt_kanban.xml` supports `ISSO` and `ISSM` roles.
  - Captures CAC certificate Subject DN, EDIPI, and cryptographic digital signature hash.
- **Automated Verification Test Suite**:
  - 17 automated unit tests in `tests/` covering CPM critical paths, 160 activities completeness, GOTS regex parsing, COA discovery scoping, ISSO/ISSM CAC auth, and VRAM mapping.

### Changed
- Updated `default/collections.conf` and `default/transforms.conf` to support `zt_tool_registry`, `zt_discovery_cache`, CAC auth fields, and expanded `zt_agile_stories` fields.
- Updated `bin/zt_stories_handler.py` to enforce RBAC permissions (ISSO/ISSM role required for `Done` status) and emit immutable audit events to `_internal`.
- Updated `bin/zt_discovery_engine.py` to support COA profile scoping and throttled evaluations.

### Security
- Whitelist regex input sanitization on all REST endpoints.
- Optimistic Concurrency Control (OCC) prevents multi-assessor write collisions.
- Immutable audit logging to `sourcetype=zerotrust_audit` for all card movements, override locks, and ISSO/ISSM digital sign-offs.
- Zero CDN policy: 100% air-gapped ready for SCIF, SIPR, and GovCloud environments.

---

## [1.0.0] - 2026-08-01

### Added
- Initial release of Zero Trust Compliance Splunk App.
- 7-Pillar Zero Trust Matrix dashboard (`zt_overview.xml`).
- Integrated Master Schedule (IMS) Gantt chart with Custom Search Command `| getcriticalpath` (`zt_ims_gantt.xml`).
- Proof of Delivery (PoD) cryptographic vault (`zt_pod_vault.xml`).
- AWS-DFD Architecture Visualizer (`zt_dfd_viz.xml`).
- MLTK Predictive Clustering & Outlier Detection (`zt_analytics.xml`).
- KV Store collections: `zt_compliance_items`, `zt_agile_stories`, `zt_milestones_ims`, `zt_evidence_pod`.
