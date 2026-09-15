#!/usr/bin/env python3
"""
Seed Script: DoD Zero Trust Execution Roadmap (COAs 1-3, v1.1) - All 152 Activities.
Generates comprehensive lookups:
- lookups/zt_agile_stories.csv (Agile stories for Jira board)
- lookups/zt_baseline_requirements.csv (Compliance baseline matrix)
- lookups/zt_milestones_ims.csv (IMS milestones and critical path)
"""

import os
import csv
import json
import re

DATA = [
    # --- SPRINT 0: PRE-SPRINT TECHNICAL ENABLERS & TELEMETRY INTEGRATIONS (8 activities) ---
    {
        "id": "0.1.1", "name": "Ingest & Normalize ACAS/Tenable Vulnerability Telemetry", "pillar": "Visibility & Analytics", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 2.0,
        "description": "Configure Splunk forwarders, HEC streams, and index parsing for Tenable.sc / ACAS vulnerability scans into index=vuln. Map findings to the CIM Vulnerabilities data model to power automated compliance checks.",
        "outcomes": "1. ACAS/Tenable scan feeds active in index=vuln.\n2. Field mappings normalized to CIM Vulnerabilities model.\n3. Automated discovery heuristics verified against vulnerability repository.",
        "end_state": "Live Tenable/ACAS telemetry feed operational and feeding Zero Trust state discovery.",
        "predecessors": "", "successors": "1.1.1; 2.1.1; 3.1.1", "sprint": "Sprint 0", "team": "SecOps Team", "priority": "Critical"
    },
    {
        "id": "0.2.1", "name": "Establish Enterprise IdP & CAC/PKI Authentication Feed", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 2.0,
        "description": "Connect Keycloak, Entra ID, or DoD PKI authentication logs to index=auth. Validate mapping to CIM Authentication data model to track user logon events, CAC/PIV usage, and MFA attestations.",
        "outcomes": "1. IdP and CAC auth streams streaming to index=auth.\n2. Normalization to CIM Authentication model verified.\n3. Baseline logon telemetry available for Sprint 1 user inventory.",
        "end_state": "Authoritative identity and authentication telemetry active for User pillar discovery.",
        "predecessors": "", "successors": "1.1.1; 1.3.1; 1.8.1", "sprint": "Sprint 0", "team": "IAM Team", "priority": "Critical"
    },
    {
        "id": "0.3.1", "name": "Deploy EDR & Comply-to-Connect (C2C) Endpoint Streams", "pillar": "Device", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 2.0,
        "description": "Stream Trellix / CrowdStrike Falcon EDR endpoint logs and Forescout / C2C NAC network posture checks to index=ep_endpoint. Map to CIM Endpoint data model.",
        "outcomes": "1. EDR agent telemetry streaming to index=ep_endpoint.\n2. C2C network access control decisions mapped to Endpoint model.\n3. Device health baseline telemetry established.",
        "end_state": "Continuous device health and C2C posture telemetry ready for Device pillar tasks.",
        "predecessors": "", "successors": "2.1.1; 2.2.1; 2.7.1", "sprint": "Sprint 0", "team": "Endpoint Sec", "priority": "High"
    },
    {
        "id": "0.4.1", "name": "Configure VRAM Compliance Data Export & Ingestion Pipeline", "pillar": "Applications & Workloads", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 2.0,
        "description": "Establish scheduled or manual CSV report ingestion pipeline for Navy VRAM (Vulnerability Remediation Asset Manager) data into index=vuln sourcetype=vram:asset:csv. Configure field aliases to map VRAM asset statuses to ZTA requirements.",
        "outcomes": "1. VRAM export CSV parser active with sourcetype=vram:asset:csv.\n2. Field aliases configured for VRAM vulnerability severity and patch status.\n3. Cross-walk established between VRAM IDs and ZTA activity outcomes.",
        "end_state": "VRAM compliance exports seamlessly feeding PoD evidence vault and discovery cache.",
        "predecessors": "", "successors": "3.1.1; 3.2.1", "sprint": "Sprint 0", "team": "SecOps Team", "priority": "High"
    },
    {
        "id": "0.5.1", "name": "Establish eMASS REST Connector & POA&M Data-Wiring", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 2.0,
        "description": "Configure eMASS export connector to synchronize DoD security control assessments, artifacts, and Plan of Action & Milestones (POA&M) with Splunk ZTA compliance items.",
        "outcomes": "1. eMASS control mappings configured in zt_evidence_pod lookup.\n2. POA&M status sync operational.\n3. Automated cross-referencing between NIST SP 800-53 controls and ZTA milestones.",
        "end_state": "Two-way eMASS compliance data-wiring active for continuous ATO tracking.",
        "predecessors": "", "successors": "6.1.1; 6.5.2", "sprint": "Sprint 0", "team": "Security Architecture", "priority": "Medium"
    },
    {
        "id": "0.6.1", "name": "Register GOTS Custom Regex & Syslog Extractors", "pillar": "Visibility & Analytics", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 2.0,
        "description": "Register custom DoD GOTS (Government Off-The-Shelf) and proprietary security gateways in zt_tool_registry.csv with custom regex extraction rules and field aliases.",
        "outcomes": "1. Non-CIM GOTS tools registered with extraction patterns in tool registry.\n2. Syslog parser rules active for proprietary DoD guard devices.\n3. Automated discovery engine enabled for non-standard telemetry feeds.",
        "end_state": "Proprietary GOTS telemetry normalized into discovery engine pipeline.",
        "predecessors": "", "successors": "7.1.1; 7.2.1", "sprint": "Sprint 0", "team": "SecOps Team", "priority": "High"
    },
    {
        "id": "0.7.1", "name": "Map Network Traffic Flows & Microsegmentation Telemetry", "pillar": "Network & Environment", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 2.0,
        "description": "Ingest Palo Alto / Cisco firewall NetFlow and SDN microsegmentation logs into index=netflow. Map to CIM Network_Traffic data model for flow mapping.",
        "outcomes": "1. NetFlow and firewall logs streaming to index=netflow.\n2. Microsegmentation block/allow decisions normalized to Network_Traffic model.\n3. Baseline data flow visibility established.",
        "end_state": "Network flow telemetry active for Network & Environment pillar execution.",
        "predecessors": "", "successors": "5.1.1; 5.2.1; 5.4.1", "sprint": "Sprint 0", "team": "NetSec Team", "priority": "High"
    },
    {
        "id": "0.8.1", "name": "Connect SOAR & Security Playbook Execution Feeds", "pillar": "Automation & Orchestration", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 2.0,
        "description": "Connect Splunk SOAR / Phantom playbook audit execution streams to index=change_analysis sourcetype=phantom:playbook to track automated security orchestrations.",
        "outcomes": "1. SOAR execution telemetry streaming to index=change_analysis.\n2. Playbook incident resolution logs indexed.\n3. Automation baseline established for Sprint 6+ orchestration milestones.",
        "end_state": "SOAR playbook telemetry active for Automation & Orchestration pillar.",
        "predecessors": "", "successors": "6.1.1; 6.5.2", "sprint": "Sprint 0", "team": "SecOps Team", "priority": "Medium"
    },

    # --- PILLAR 1: USER (22 activities) ---
    {
        "id": "1.1.1", "name": "Inventory User", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 25.9,
        "description": "DoD Components utilize Enterprise authoritative source of (PE/NPE) identity (PE - AMID, NIS, AFID) and/or establish or augment with local authoritative source. Identity management can be done manually if needed, preparing for automated approach in later stages. Identity source is connected to identity life cycle management processes (i.e. joiner/mover/leaver/returner). IT privileged users are clearly identified.",
        "outcomes": "1. Identified managed non-privileged users.\n2. Identified managed privileged users.\n3. Identified applications using their own user account management for non-administrative and administrative accounts.\n4. Identify the authoritative source of identities.",
        "end_state": "Accurately determine and keep track of users who have both the authorization and authentication to access critical systems or resources. This involves regularly reviewing, communicating, and carefully examining the sources of information that provide the true and up-to-date user data.",
        "predecessors": "", "successors": "Rule Based Dynamic Access Pt1", "sprint": "Sprint 1", "team": "IAM Team", "priority": "High"
    },
    {
        "id": "1.2.1", "name": "Implement App Based Permissions per Enterprise", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 17.7,
        "description": "DoD Components utilize Enterprise authoritative source of (PE/NPE) identity (PE - AMID, NIS, AFID) and/or establish or augment with local authoritative source. Identity management can be done manually if needed, preparing for automated approach in later stages. Identity source is connected to identity life cycle management processes (i.e. joiner/mover/leaver/returner). IT privileged users are clearly identified.",
        "outcomes": "1. Enterprise roles/attributes needed for user authorization to application functions and/or data have been vetted and approved through the ICAM governance processes.\n2. Approved Component ICAM implementations will maintain and make available authoritative information about their personnel (i.e. attributes and entitlements), while maximizing the usage of self-service attributes and entitlements.\n3. Components identify attributes associated with PAM activities within their environment.\n4. Component ICAM implementation obtain authoritative information about personnel (i.e. attributes, and entitlements) from a central attribute source once available, or from other Components using standard profiles.",
        "end_state": "Authoritative attributes required to implement conditional user access into applications are available to support privileged access management.",
        "predecessors": "", "successors": "", "sprint": "Sprint 2", "team": "IAM Team", "priority": "High"
    },
    {
        "id": "1.2.2", "name": "Rule Based Dynamic Access Pt1", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 22.1,
        "description": "DoD Components utilize the rules from the 'Periodic Authentication' activity to build rules enabling and disabling privileges dynamically. IT Privileged user accounts utilize the PAM solution to move to dynamic privileged access using Just-in-Time (JIT) access and Just-Enough-Administration (JEA) methods.",
        "outcomes": "1. Access to an applications'/services' functions and/or data are limited to users with appropriate Attribute-Based Access Control (users, devices, environment etc.), allowing for granular and flexible control.\n2. All possible applications use JIT/JEA permissions for administrative users.",
        "end_state": "Periodic challenges occur where access is affected if challenge is failed within accepted response parameters. Access is always predicated on authentication and authorization with activity happening (decisions made) in real-time.",
        "predecessors": "Single Authentication; Inventory User", "successors": "Rule Based Dynamic Access Pt2; AI-enabled Network Access", "sprint": "Sprint 3", "team": "IAM Team", "priority": "High"
    },
    {
        "id": "1.2.3", "name": "Rule Based Dynamic Access Pt2", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 15.5,
        "description": "DoD Components expand the development of rules for dynamic access decision making accounting for risk. Solutions used for dynamic access are integrated with cross pillar Machine Learning (ML) and Artificial Intelligence (AI) functionality enabling automated rule management.",
        "outcomes": "1. Components and services are fully utilizing rules to enable dynamic access to applications and services.\n2. Technology utilized for Rule-Based Dynamic Access supports integration with AI/ML tooling.",
        "end_state": "Dynamic access rules automatically adjust based on continuous risk scoring and AI/ML telemetry across user and device vectors.",
        "predecessors": "Rule Based Dynamic Access Pt1; File Activity Monitoring Pt2", "successors": "", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.2.4", "name": "Enterprise Gov't roles and Permissions Pt1", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 11.6,
        "description": "DoD Components federate remaining user and group attributes as appropriate to the Enterprise Identity, Credential and Access Management (ICAM) solution. The updated attribute set is used to create universal roles for Organizations to use. Core functions of the Identity Provider (IdP) and ICAM solutions are migrated to cloud services and/or environments enabling improved resilience and performance.",
        "outcomes": "1. Component attribute and role data repository federated with Enterprise ICAM.\n2. Cloud-based Enterprise IdP can be used by cloud and on-premises applications.\n3. A standardized set of roles and permissions are created and aligned to attributes.",
        "end_state": "Universal roles and cloud IdP federation established across components.",
        "predecessors": "", "successors": "Enterprise Gov't roles and Permissions Pt2", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.2.5", "name": "Enterprise Gov't roles and Permissions Pt2", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 11.2,
        "description": "DoD Components move all possible functions of the Identity Provider (IdP) and Identity, Credential and Access Management (ICAM) solutions to cloud environments. Enclave/Denied, Disrupted, Intermittent, and Limited (DDIL) environments utilize local capabilities to support disconnected functions but ultimately are managed by the centralized ICAM. Updated roles are now mandated for usage and exceptions are reviewed following a risk-based approach.",
        "outcomes": "1. Components utilize cloud IdP functionality Where possible on-premise IdP is decommissioned.\n2. Permissions and roles are mandated for usage when evaluating attributes.",
        "end_state": "All feasible IdP functions operate in cloud environments with DDIL local support.",
        "predecessors": "Enterprise Gov't roles and Permissions Pt1", "successors": "", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.3.1", "name": "Organizational MFA/IDP", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 10.6,
        "description": "DoD Components or Identity Provider (IdP) solution using approved credential or approved alternative Multi-Factor Authentication (MFA). The IdP and MFA solution may be combined in a single application or separated as needed assuming automated integration is supported by both solutions. Both IdP and MFA support integration with the Enterprise PKI capability as well as enabling key pairs to be signed by the trusted root certificate authorities. Authentication for mission/task-critical applications and services authentication is MFA-Enabled and leverages the related authentication mechanisms to manage users and groups.",
        "outcomes": "1. Component is using IdP with MFA for critical applications/services.\n2. Components have implemented an Identity Provider (IdP) that enables DoD PKI Multi-Factor Authentication (e.g. CAC, DPIV, DoD Issued PIV-I, FIPS 201 Compliant softcerts).\n3. DoD Enterprise is the approved organizational PKI for critical services (ECA, FPKI, Category I/II/III PKI, etc.).\n4. Utilize approved Alternative Hardware Tokens as needed - USB Security Key and/or OTP device (e.g. Yubikey FIPS for smartcard, FIDO2, FIDO U2F, OTP, RSA SecurID for OTP, etc.).\n5. For access to low-risk resources (e.g., PII, publicly released information), utilize alternative two-step, two-factor authentication using software authenticators (i.e., Mobile Connect, Yubico, Okta Verify, etc.).",
        "end_state": "Critical applications are identified and use MFA in alignment with a federated IdP solution.",
        "predecessors": "", "successors": "Alternative Flexible MFA Pt1", "sprint": "Sprint 1", "team": "IAM Team", "priority": "Critical"
    },
    {
        "id": "1.3.2", "name": "Alternative Flexible MFA Pt1", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 17.4,
        "description": "DoD Components Identity Provider (IdP) supports alternative methods of Multi-Factor Authentication (MFA) complying with Cyber Security requirements (e.g., FIPS 140-2, FIPS 197, etc.). Alternative tokens can be used for application-based authentication. MFA options support biometric capability and can be managed using a self-service approach. Where possible MFA provider(s) are moved to cloud services instead of being hosted on-premise.",
        "outcomes": "1. IdP provides user self-service for alternative MFA options for approved applications.\n2. IdP provides alternative token MFA for approved applications per policy.",
        "end_state": "Self-service alternative MFA enabled for approved workloads.",
        "predecessors": "Organizational MFA/IDP", "successors": "Alternative Flexible MFA Pt2", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.3.3", "name": "Alternative Flexible MFA Pt2", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 14.6,
        "description": "Alternative Multi-Factor Authentication (MFA) methods utilize user activity patterns from cross pillar activities such as 'User Activity Monitoring (UAM) and User & Entity Behavior Analytics (UEBA)' to assist with access decision making (e.g., not grant access when pattern deviation occurs).",
        "outcomes": "1. User activity patterns implemented.",
        "end_state": "MFA step-up triggered dynamically based on behavioral pattern deviations.",
        "predecessors": "Alternative Flexible MFA Pt1", "successors": "", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.4.1", "name": "Implement System and Migrate Privileged Users Pt1", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 12.4,
        "description": "DoD Components procure and implement a Privileged Access Management (PAM) solution to support all critical privileged use cases. Application/Service integration points are identified to determine status of support for the PAM solution. Applications/Services that easily integrate with the PAM solution are transitioned to using the solution versus static and direct privileged permissions.",
        "outcomes": "1. Privilege Access Management (PAM) tooling is implemented.\n2. Applications and devices that support and do not support PAM tools are identified.\n3. Applications that support PAM, now use PAM for controlling emergency/built-in accounts.",
        "end_state": "Components implement a PAM tool with a clear transition plan that identifies the applications and decides what applications require a PAM tool.",
        "predecessors": "", "successors": "Implement System and Migrate Privileged Users Pt2", "sprint": "Sprint 2", "team": "IAM Team", "priority": "High"
    },
    {
        "id": "1.4.2", "name": "Implement System and Migrate Privileged Users Pt2", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 14.4,
        "description": "DoD Components utilize the inventory of supported and unsupported Applications/Services for integration with the Privileged Access Management (PAM) solution to extend integrations. PAM is integrated with the more challenging Applications/Services to maximize PAM solution coverage. Exceptions are managed in a risk-based methodical approach with the goal of migration off and/or decommissioning Applications/Services that do not support the PAM solution.",
        "outcomes": "1. Privileged activities are migrated to PAM and access is fully managed.",
        "end_state": "Ensure secure and controlled access to privileged accounts and resources through fully implemented PAM solution, mitigating the risk of unauthorized access and potential cyber threats.",
        "predecessors": "Implement System and Migrate Privileged Users Pt1", "successors": "Real time Approvals & JIT/JEA Analytics Pt1", "sprint": "Sprint 3", "team": "IAM Team", "priority": "High"
    },
    {
        "id": "1.4.3", "name": "Real time Approvals & JIT/JEA Analytics Pt1", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 12.5,
        "description": "Identification of necessary attributes (Users, Groups, etc.) are automated and integrated into the Privileged Access Management (PAM) solution. Privilege access requests are migrated to the PAM solution for automated approvals and denials.",
        "outcomes": "1. Accounts, applications, and data of concern (of greatest risk to DoD mission) are identified.\n2. Using PAM tools, access to applications/services follows JIT/JEA methodology\n3. Privileged access requests are automated as appropriate.",
        "end_state": "JIT/JEA automated approvals and denials active for privileged enclaves.",
        "predecessors": "Implement System and Migrate Privileged Users Pt2", "successors": "Real time Approvals & JIT/JEA Analytics Pt2", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.4.4", "name": "Real time Approvals & JIT/JEA Analytics Pt2", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 8.9,
        "description": "DoD Components integrate User & Entity Behavior Analytics (UEBA) and User Activity Monitoring (UAM) solutions with the Privileged Access Management (PAM) solution providing user pattern analytics for decision making.",
        "outcomes": "1. UEBA or similar analytic system integrated with PAM tools for JIT/JEA account approvals.",
        "end_state": "UEBA-driven automated risk checks govern privileged access elevations.",
        "predecessors": "Real time Approvals & JIT/JEA Analytics Pt1", "successors": "", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.5.1", "name": "Organizational Identity Life-Cycle Management", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 14.8,
        "description": "DoD Components establish a process for life cycle management of users both privileged and non-privileged. Utilizing an approved Identity Provider (IdP) the process is implemented and followed by the maximum number of users. Users falling outside of the standard process are approved through risk-based exceptions to be evaluated regularly for decommission.",
        "outcomes": "1. Standardized account life cycle process.",
        "end_state": "Establishes a comprehensive and efficient process that ensures the accurate and secure management of user identities throughout their entire life cycle within the Components environment.",
        "predecessors": "", "successors": "Enterprise Identity Life-Cycle Management Pt1", "sprint": "Sprint 2", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.5.2", "name": "Enterprise Identity Life-Cycle Management Pt 1", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 11.7,
        "description": "Specified policies and supporting process are followed by DoD Components. DoD Components implement the Enterprise Identity Life-Cycle Management process for the maximum number of identities, attributes, groups, credentials, and permissions. Exceptions to the policy are managed in a risk-based methodical approach.",
        "outcomes": "1. Automated identity life cycle processes.\n2. Integrated with Enterprise ICAM process and tools.",
        "end_state": "Implementation of consistent and well-defined processes and controls for managing the maximum number of identities in the life cycle.",
        "predecessors": "Organizational Identity Life-Cycle Management", "successors": "Enterprise Identity LifeCycle Management Pt2", "sprint": "Sprint 3", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.5.3", "name": "Enterprise Identity LifeCycle Management Pt2", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 12.8,
        "description": "DoD Components further integrate the critical automation functions of the Identity Provider (IdP) and Identity, Credential and Access Management (ICAM) solutions following the Enterprise Identity Life-Cycle Management (ILM) process to enable Enterprise automation and analytics. ILM primary processes are integrated into the cloud-based Enterprise ICAM solution.",
        "outcomes": "1. Integration with Critical IDM/IdP functions.\n2. Primary ILM functions are cloud based.",
        "end_state": "Cloud-based Enterprise ICAM automation for identity lifecycle governance.",
        "predecessors": "Enterprise Identity Life-Cycle Management Pt1", "successors": "Enterprise Identity LifeCycle Management Pt3", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.5.4", "name": "Enterprise Identity LifeCycle Management Pt3", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 9.2,
        "description": "DoD Components integrate remaining Identity Lifecycle Management (ILM) processes with the Enterprise Identity, Credential and Access Management (ICAM) solution. Enclave/DDIL environments, while still authorized to operate, integrate with the Enterprise ICAM using local connectors to the cloud environment.",
        "outcomes": "1. All ILM functions moved to cloud as appropriate.\n2. Integration with all IDM/IdP functions.",
        "end_state": "Complete enterprise ILM integration with local DDIL connectors.",
        "predecessors": "Enterprise Identity LifeCycle Management Pt2", "successors": "", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.6.1", "name": "Implement User & Entity Behavior Activity (UEBA) and User Activity Monitoring (UAM) Tooling", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 15.9,
        "description": "DoD Components procure and implement User & Entity Behavior Analytics (UEBA) and User Activity Monitoring (UAM) solutions. Initial integration point with Enterprise IdP is completed, enabling future usage in decision making.",
        "outcomes": "1. UEBA and UAM functionality is correlated with the Master User Record and integrated with Enterprise IdP.",
        "end_state": "Establish a comprehensive and continuously adaptive security solution that leverages behavior analytics, detects anomalies, and protects against unauthorized access.",
        "predecessors": "", "successors": "Establish User Baseline Behavior; User/Device Baselines; Alternative Flexible MFA Pt2", "sprint": "Sprint 2", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "1.6.2", "name": "User Activity Monitoring Pt1", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 13.5,
        "description": "DoD Components integrate User & Entity Behavior Analytics (UEBA) and User Activity Monitoring (UAM) solutions with Identity Providers (IdP) for extended visibility as needed. Analytics and data generated by UEBA and UAM for critical applications/services are integrated with Just-in-Time (JIT) and Just-Enough-Access (JEA) solutions for improving decision.",
        "outcomes": "1. UEBA is integrated with IdPs as appropriate.\n2. UEBA is integrated with JIT/JEA for critical services.",
        "end_state": "UEBA and UAM data dynamically informs JIT/JEA privilege elevations.",
        "predecessors": "User/Device Baselines", "successors": "User Activity Monitoring Pt2", "sprint": "Sprint 6+", "team": "SOC Team", "priority": "Medium"
    },
    {
        "id": "1.6.3", "name": "User Activity Monitoring Pt2", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 11.2,
        "description": "DoD Components continue the analytics usage from User & Entity Behavior Analytics (UEBA) and User Activity Monitoring (UAM) solutions by using generated data for all monitored applications and services when decision making occurs in the Just-in-Time (JIT) and Just-Enough-Access (JEA) solution.",
        "outcomes": "1. UEBA and UAM is integrated with JIT/JEA for all services.",
        "end_state": "All monitored services leverage live behavioral analytics for authorization.",
        "predecessors": "User Activity Monitoring Pt1", "successors": "Real-Time Access Decisions; AIenabled Dynamic Access Control; Enrich Attributes for Resource Authorization Pt1; AI-enabled Network Access", "sprint": "Sprint 6+", "team": "SOC Team", "priority": "Medium"
    },
    {
        "id": "1.7.1", "name": "Deny User by Default Policy", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 22.7,
        "description": "DoD Components audit user and group usage for permissions and revoke permissions when appropriate. This activity includes the revocation and/or decommission of excess permissions and access for application/service-based identities and groups. Where possible, static privileged users are decommissioned or permission are reduced, preparing for future rule/dynamic based access. The implemented audit and governance functions are automated where possible.",
        "outcomes": "1. Applications updated to deny by default to functions/data requiring specific roles/attributes for access.\n2. Reduced default permission levels are implemented.\n3. Applications/services privileged users have been reviewed and audited, and unnecessary access has been removed.\n4. Applications identify functions and data requiring specific roles/attributes for access.\n5. Audit functions and governance processes are implemented and automated when possible to update user authentication and authorization.",
        "end_state": "Users must be authorized and authenticated to access data, applications, assets, and services. Audit and access validation occurs consistently.",
        "predecessors": "", "successors": "", "sprint": "Sprint 2", "team": "IAM Team", "priority": "Critical"
    },
    {
        "id": "1.8.1", "name": "Single Authentication", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 19.2,
        "description": "DoD Components authenticate users and NPEs at least once per session (e.g., logon) using CAC and other DoD approved methods. Users being authenticated are managed by the parallel activity 'Organizational MFA/IdP' with the Component Identity Provider (IdP). Components do not use application/service-based identities and groups.",
        "outcomes": "1. Authentication implemented at least once per session.",
        "end_state": "Component applications apply single authentication to the specified standard.",
        "predecessors": "", "successors": "Rule Based Dynamic Access Pt1; Resource Authorization Pt1; SDC Resource Authorization Pt2", "sprint": "Sprint 2", "team": "IAM Team", "priority": "High"
    },
    {
        "id": "1.8.2", "name": "Periodic Authentication", "pillar": "User", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 25.4,
        "description": "DoD Components enable periodic authentication for applications and services. Traditionally, these are based on duration and/or duration timeout, however, other period-based analytics can be used to enforce re-authentication of user sessions.",
        "outcomes": "1. Authentication implemented multiple times per session based on security attributes and criticality of the data, user, application, system, and source user location.",
        "end_state": "Authentication occurs per the requirement and standard.",
        "predecessors": "Single Authentication", "successors": "Continuous Authentication Pt1; AI-enabled Network Access", "sprint": "Sprint 3", "team": "IAM Team", "priority": "High"
    },
    {
        "id": "1.8.3", "name": "Continuous Authentication Pt 1", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 16.8,
        "description": "DoD Components applications/services utilize multiple session authentications based on security attributes and access requested. Privilege changes and associational transaction requests require additional levels of authentication such as Multi-Factor Authentication (MFA) pushes to users.",
        "outcomes": "1. Transaction authentication implemented per session based on security attributes.",
        "end_state": "Session transactions require dynamic risk-based verification.",
        "predecessors": "Periodic Authentication", "successors": "Continuous Authentication Pt2", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.8.4", "name": "Continuous Authentication Pt 2", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 16.8,
        "description": "DoD Components continue usage of transaction-based authentication to include integration such as user patterns.",
        "outcomes": "1. Transaction authentication implemented per session based on security attributes.",
        "end_state": "Continuous authentication integrated with real-time risk patterns.",
        "predecessors": "Continuous Authentication Pt1", "successors": "Real-Time Access Decisions; AIenabled Dynamic Access Control", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.9.1", "name": "Enterprise PKI/IDP Pt1", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 12.4,
        "description": "The DoD Enterprise works with Components to implement Enterprise Public Key Infrastructure (PKI) solutions in a centralized and/or federated fashion. The Enterprise PKI solution utilizes a single or set of Enterprise level Root Certificate Authorities (CA) that can then be trusted by components to build Intermediate CA. Components PKI Certificated Authorities are integrated with the Enterprise PKI.\nAn Enterprise Identity Provider (IdP) platform is implemented. The IdP solution may either be a single solution or federated set of Component IdPs with standard level of access across Components and standardized set of attributes. Components IdPs are integrated with the Enterprise IdP.",
        "outcomes": "1. Enterprise PE & NPE CONOPS, taxonomy, and naming standards are developed.\n2. Components Certificate Authorities (CA) are integrated with the DoD PKI Hierarchy.\n3. Enterprise level requirements are implemented, including mandated user attributes for a validated and verified Enterprise Identity Provider (IdP) Platform.\n4. Enterprise wide IdP platform is implemented through a single solution or integration of multiple solutions.",
        "end_state": "All PEs and NPEs are issued a validated and verified digital identity that can be tracked at the Enterprise level using the strongest authentication available.",
        "predecessors": "", "successors": "Enterprise PKI/IDP Pt2", "sprint": "Sprint 2", "team": "IAM Team", "priority": "Critical"
    },
    {
        "id": "1.9.2", "name": "Enterprise PKI/IDP Pt2", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 27.2,
        "description": "DoD Components enable biometric support in the Identity Provider (IdP) for mission/task-critical applications and services as appropriate. Biometric functionality is moved from Component solutions to the Enterprise. Multi-Factor Authentication (MFA) and Public Key Infrastructure (PKI) is decommissioned and migrated to the Enterprise as appropriate.",
        "outcomes": "1. Critical services integrated with biometrics.\n2. Decommission organizational MFA/PKI as appropriate in lieu of Enterprise MFA/PKI.\n3. Enterprise biometric functions implemented.",
        "end_state": "Enterprise-level biometric authentication operational for critical missions.",
        "predecessors": "Enterprise PKI/IDP Pt1", "successors": "Enterprise PKI/IDP Pt3", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },
    {
        "id": "1.9.3", "name": "Enterprise PKI/IDP Pt3", "pillar": "User", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 30.0,
        "description": "DoD Components integrate the remaining applications/services with Biometrics functionalities. Alternative Multi-Factor Authentication (MFA) tokens can be used.",
        "outcomes": "1. All Components services integrate with biometrics.",
        "end_state": "Enterprise biometric coverage achieved across all component applications.",
        "predecessors": "Enterprise PKI/IDP Pt2", "successors": "", "sprint": "Sprint 6+", "team": "IAM Team", "priority": "Medium"
    },

    # --- PILLAR 2: DEVICE (22 activities) ---
    {
        "id": "2.1.1", "name": "Device Health Tool Gap Analysis", "pillar": "Device", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 9.8,
        "description": "DoD Components develop an inventory of devices within the environment, and device attributes are tracked.",
        "outcomes": "1. Inventory of authorized and approved devices is created per Component with owners.\n2. Determine and implement tools to gauge device health.",
        "end_state": "A comprehensive inventory of authorized and approved devices with designated owners, and effective tools for monitoring and assessing device health are implemented.",
        "predecessors": "", "successors": "", "sprint": "Sprint 1", "team": "Endpoint Sec", "priority": "High"
    },
    {
        "id": "2.1.2", "name": "NPE/PKI, Device under Management", "pillar": "Device", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 22.8,
        "description": "DoD Components utilize the DoD Enterprise PKI solution/service to deploy x509 certificates to all supported and managed devices. Other Non-Person Entities (NPEs) (e.g., web servers, network devices, routers, applications, etc.) that support x509 certificates are assigned them in the PKI and/or IdP systems.",
        "outcomes": "1. Non-person entities are managed via Component PKI and IdP.",
        "end_state": "Components use established PKI and IdP solutions to manage all NPEs.",
        "predecessors": "Enterprise Device Management Pt1", "successors": "Implement C2C/Compliance Based Network Authorization Pt1; Enterprise PKI Pt1; Deny Device by Default Policy", "sprint": "Sprint 3", "team": "Endpoint Sec", "priority": "High"
    },
    {
        "id": "2.1.3", "name": "Enterprise IDP Pt1", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 12.8,
        "description": "The DoD Enterprise Identity Provider (IdP), either using a centralized technology or federated organizational technologies, integrates Non-Person Entities (NPEs), such as devices and service accounts. Integration is tracked in the Enterprise Device Management solution when applicable as to whether it is integrated or not. NPEs not able to be integrated with the IdP are either marked for retirement or excepted using a risk-based methodical approach.",
        "outcomes": "1. Component NPEs are integrated with Enterprise IdP.\n2. Where applicable, ensure tracking in the UEM solution.",
        "end_state": "All NPEs are assigned static attributes in an identity provider, provided an exception based on risk analysis, or marked for retirement, as part of the Enterprise Life Cycle Management plan.",
        "predecessors": "", "successors": "Enterprise IDP Pt2", "sprint": "Sprint 3", "team": "Endpoint Sec", "priority": "Medium"
    },
    {
        "id": "2.1.4", "name": "Enterprise IDP Pt2", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 8.8,
        "description": "The DoD Enterprise Identity Provider (IdP), either using a centralized technology or federated organizational technologies, adds additional attributes for Non-Person Entities (NPEs) (e.g., location, usage patterns, etc.) to device profiles.",
        "outcomes": "1. Conditional device attributes are part of the IdP profile.",
        "end_state": "Advanced conditional telemetry integrated into all device and NPE identity profiles.",
        "predecessors": "Enterprise IDP Pt1", "successors": "", "sprint": "Sprint 6+", "team": "Endpoint Sec", "priority": "Medium"
    },
    {
        "id": "2.2.1", "name": "Implement C2C/Compliance Based Network Authorization Pt1", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 9.4,
        "description": "The DoD Enterprise refines policy, standards, and requirements for Comply to Connect (C2C). Components implement and enforce compliance-based network authorization to meet ZT Target Level functionalities.",
        "outcomes": "1. C2C is enforced at the Component level for all environments.\n2. All mandated device checks are implemented using C2C at the Component level.",
        "end_state": "A policy exists or is developed that dictates the need for all devices to be authorized, authenticated, and C2C compliant before connecting to the network.",
        "predecessors": "NPE/PKI Device Under Management; Integrate NextGen AV Tools with C2C; Managed and Limited BYOD & IOT Support; Implement Asset, Vulnerability and Patch Management Tools", "successors": "Implement C2C/Compliance Based Network Authorization Pt2", "sprint": "Sprint 3", "team": "Endpoint Sec", "priority": "Critical"
    },
    {
        "id": "2.2.2", "name": "Implement C2C/Compliance Based Network Authorization Pt2", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 18.2,
        "description": "DoD Components expand the deployment and usage of Comply to Connect (C2C) to all supported environments required to meet ZT advanced functionalities. C2C teams integrate their solution(s) with the Enterprise IdP and Authorization Gateways to better manage access and authorizations to resources.",
        "outcomes": "1. C2C is enforced in all supported environments.\n2. Advanced device checks are completed and integrated with dynamic access (Enterprise IdP / Zero Trust Network Access (ZTNA)).",
        "end_state": "Continuous dynamic C2C posture validation enforced across ZTNA gateways.",
        "predecessors": "Implement C2C/Compliance Based Network Authorization Pt1; Fully Integrate Device Security Stack w/C2C as appropriate", "successors": "Real-Time Access Decisions", "sprint": "Sprint 6+", "team": "Endpoint Sec", "priority": "Medium"
    },
    {
        "id": "2.3.1", "name": "Entity Activity Monitoring Pt1", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 16.4,
        "description": "Using the developed User and Device baselines, DoD Components utilize the implemented User and Entity Behavioral Activity (UEBA) solution to integrate baselines. UEBA device attributes and baselines are available to be used for device authorization.",
        "outcomes": "1. UEBA attributes are integrated for device baselining.\n2. UEBA attributes are available for usage with device access.",
        "end_state": "Device baselines integrated into UEBA for adaptive access decisions.",
        "predecessors": "User/Device Baselines; Implement User & Entity Behavior Activity (UEBA); User Activity Monitoring Tooling", "successors": "Entity Activity Monitoring Pt2", "sprint": "Sprint 6+", "team": "SOC Team", "priority": "Medium"
    },
    {
        "id": "2.3.2", "name": "Entity Activity Monitoring Pt2", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 16.7,
        "description": "DoD Components utilize the User and Entity Behavioral Activity (UEBA) solution with network access solutions to mandate UEBA attributes (e.g., device health, logon patterns, etc.) for accessing environments and resources.",
        "outcomes": "1. UEBA attributes are mandated for device access.",
        "end_state": "Mandated UEBA health attributes enforced on all network resource gateways.",
        "predecessors": "Entity Activity Monitoring Pt1", "successors": "Real-Time Access Decisions; AIenabled Dynamic Access Control; Enrich Attributes for Resource Authorization Pt1; AI-enabled Network Access", "sprint": "Sprint 6+", "team": "SOC Team", "priority": "Medium"
    },
    {
        "id": "2.3.3", "name": "Implement Application Control & File Integrity Monitoring (FIM) Tools", "pillar": "Device", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 16.2,
        "description": "DoD Components procure and implement File Integrity Monitoring (FIM) and Application control (e.g., execution deny/allow listing, containment, isolation) solutions. FIM ensures any data altered is authorized, and unauthorized changes are detected by FIM. Application containment is used to isolate any suspicious behavior or permissions to prevent any malicious lateral movement, expanding the capabilities and response of traditional executable containment. Both FIMS and application containment continues the development of the Device, Data, and Application & Workload pillars.",
        "outcomes": "1. Application control and FIM tooling is implemented on all service applications and endpoint devices with C2C orchestration.\n2. EDR tooling covers maximum amount of services applications and endpoint devices.",
        "end_state": "Components deploy FIM and application control tooling in alignment with EDR, SOAR, and UEM. C2C orchestration and regular control audits and alerts are in place.",
        "predecessors": "", "successors": "", "sprint": "Sprint 3", "team": "Endpoint Sec", "priority": "High"
    },
    {
        "id": "2.3.4", "name": "Integrate NextGen AV Tools with C2C", "pillar": "Device", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 18.5,
        "description": "DoD Component procures and implements an Endpoint Protection Platform (EPP). EPP should have the capabilities to use advanced analytics (e.g., artificial intelligence, behavioral detection, machine learning) to mitigate exploits (e.g., zero days, signatureless, fileless), provide Network Access Control, and protect against known and unknown threats. These solutions are orchestrated with the C2C or EDR solution for baseline status checks of signatures, updates, etc.",
        "outcomes": "1. Critical Endpoint Protection Platform (EPP) data is being sent to C2C and EDR for checks.\n2. EPP tooling is implemented on all critical services applications and endpoint devices.",
        "end_state": "Advanced protection on endpoint devices against modern threats, while developing Automation & Orchestration, as well as Visibility & Analytics pillar, through AI, ML and behavior analysis.",
        "predecessors": "", "successors": "Implement C2C/Compliance Based Network Authorization Pt1", "sprint": "Sprint 3", "team": "Endpoint Sec", "priority": "High"
    },
    {
        "id": "2.3.5", "name": "Fully Integrate Device Security stack with C2C as appropriate", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 13.3,
        "description": "DoD Components continue the deployment of Application Control to all environments and in prevention mode. File Integrity Monitoring (FIM) and Application Controls analytics are integrated into Comply to Connect (C2C) for expanded access decision making. C2C analytics are evaluated for further device/endpoint security stack data points such as UEDM and are integrated as necessary.",
        "outcomes": "1. Application Control and FIM deployment is expanded to all necessary services/applications.\n2. Remaining data from Device Security tooling is implemented with C2C.",
        "end_state": "Complete device security stack telemetry integrated with C2C enforcement engine.",
        "predecessors": "", "successors": "Implement C2C/Compliance Based Network Authorization Pt2; Managed and Full BYOD & IOT Support Pt2", "sprint": "Sprint 6+", "team": "Endpoint Sec", "priority": "Medium"
    },
    {
        "id": "2.3.6", "name": "Enterprise PKI Pt1", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 22.7,
        "description": "The DoD Enterprise Public Key Infrastructure (PKI) is expanded to include the addition of NPE and device certificates. NPEs and devices that do not support PKI certificates are marked for retirement.",
        "outcomes": "1. All devices and NPEs have certificates installed for authentication provisioned by the Enterprise PKI.\n2. Devices that are unable to use certificate-based authentication are phased out and/or moved to minimal access environments.",
        "end_state": "Enterprise PKI machine certificates provisioned across all managed devices.",
        "predecessors": "Implement UEDM or equivalent Tools; NPE/PKI Device Under Management", "successors": "Enterprise PKI Pt2", "sprint": "Sprint 6+", "team": "Endpoint Sec", "priority": "Medium"
    },
    {
        "id": "2.3.7", "name": "Enterprise PKI Pt2", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 10.5,
        "description": "DoD Components utilize certificates provisioned by the DoD Enterprise Public Key Infrastructure (PKI) for device authentication and machine to machine communications. Unsupported devices are retired and exceptions are approved and managed using a risk based methodical approach.",
        "outcomes": "1. Devices are required to authenticate with certificate-based authentication to communicate with other services and devices.",
        "end_state": "Strict certificate-based machine-to-machine authentication across all systems.",
        "predecessors": "Enterprise PKI Pt1", "successors": "", "sprint": "Sprint 6+", "team": "Endpoint Sec", "priority": "Medium"
    },
    {
        "id": "2.4.1", "name": "Deny Device by Default Policy", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 9.6,
        "description": "DoD Enterprise sets standards and requirements for overall policy, with Components tailoring to specific environmentse and mission requirements. DoD Components will block access from all unmanaged remote and local devices to resources. Managed compliant devices are provided risk-based, methodical access following ZT Target Level concepts.",
        "outcomes": "1. Enterprise sets standards for Deny Device by Default policy.\n2. Components will block unmanaged devices remotely/locally.\n3. Access is enabled strictly for compliant devices remotely/locally following the 'Deny Device by Default' policy approach.",
        "end_state": "All device access is authorized, verified, and compliant and all other devices are blocked by default.",
        "predecessors": "NPE/PKI Device Under Management", "successors": "", "sprint": "Sprint 2", "team": "Endpoint Sec", "priority": "Critical"
    },
    {
        "id": "2.4.2", "name": "Managed and Limited BYOD & IOT Support", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 39.7,
        "description": "DoD Components utilize Enterprise Device Management Solution to ensure that managed Bring Your Own Device (BYOD) and Internet of Things (IoT) devices are fully integrated with Enterprise IdP. Enabling user and device-based authorization is supported. Device access requires dynamic access policies and the practice of least privilege.",
        "outcomes": "1. All Component access must be governed by dynamic access permissions for BYOD and IoT Devices.\n2. Component BYOD and IoT device permissions are baselined and integrated with Enterprise IdP.",
        "end_state": "Components establish a foundation for risk-based access control for BYOD and IoT with dynamic permissions.",
        "predecessors": "", "successors": "Implement C2C/Compliance Based Network Authorization Pt1; Managed and Full BYOD & IOT Support Pt1", "sprint": "Sprint 3", "team": "Endpoint Sec", "priority": "High"
    },
    {
        "id": "2.4.3", "name": "Managed and Full BYOD & IOT Support Pt1", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 24.7,
        "description": "DoD Components utilize Unified Endpoint and Device Management (UEDM) and similar solutions to enable access for managed and approved devices to Mission and Operational Critical services/applications using dynamic access policies. BYOD and Internet of Things (IoT) devices are required to meet standard baseline checks before authorization.",
        "outcomes": "1. Only BYOD and IoT devices that meet configuration standards are allowed to access resources.\n2. Critical Services require dynamic access for devices.",
        "end_state": "Dynamic access policies enforced on BYOD/IoT accessing critical mission apps.",
        "predecessors": "Managed and Limited BYOD & IOT Support", "successors": "Managed and Full BYOD & IOT Support Pt2", "sprint": "Sprint 6+", "team": "Endpoint Sec", "priority": "Medium"
    },
    {
        "id": "2.4.4", "name": "Managed and Full BYOD & IOT Support Pt2", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 24.6,
        "description": "DoD Components utilize Unified Endpoint and Device Management (UEDM) and similar solutions to grant authorized managed devices access to all services and applications where possible. Unmanaged devices, upon meeting device checks and standard baselines, are granted access to services and applications following a risk-based authorization approach.",
        "outcomes": "1. All possible services require dynamic access for devices.",
        "end_state": "Full zero-trust posture checking for all device classes across all services.",
        "predecessors": "Fully Integrate Device Security Stack w/C2C as appropriate; Managed and Full BYOD & IOT Support Pt1", "successors": "", "sprint": "Sprint 6+", "team": "Endpoint Sec", "priority": "Medium"
    },
    {
        "id": "2.5.1", "name": "Implement Asset, Vulnerability and Patch Management Tools", "pillar": "Device", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 18.4,
        "description": "DoD Components implement solution(s) for managing asset/device configurations, vulnerabilities, and patches. Using minimum compliance standards (e.g., STIGs, C2C, UEM etc.), teams can confirm or deny managed device compliance. As part of the procurement and implementation process for solutions, APIs or other programmatic interfaces will be in scope for future levels of automation and integration.",
        "outcomes": "1. Components can confirm if devices meet minimum compliance standards or not.\n2. Component solutions enable integration across asset management, vulnerability, and patching systems while considering automation capabilities.",
        "end_state": "Continuously identify and address vulnerabilities, manage assets effectively, and apply necessary patches to mitigate potential threats and maintain a secure environment.",
        "predecessors": "", "successors": "Implement C2C/Compliance Based Network Authorization Pt1; Automate Application Security & Code Remediation Pt1", "sprint": "Sprint 3", "team": "Endpoint Sec", "priority": "High"
    },
    {
        "id": "2.6.1", "name": "Implement UEDM or equivalent Tools", "pillar": "Device", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 18.1,
        "description": "DoD Components will work closely with the 'Implement Asset, Vulnerability, and Patch Management Tools' activity to procure and implement a Unified Endpoint Device Management (UEDM) solution ensuring that requirements are integrated with the procurement process. Once a solution is procured the UEDM team(s) ensure that critical ZT Target Level functionalities such as minimum compliance, asset management, and API support are in place.",
        "outcomes": "1. Components can confirm if devices meet minimum compliance standards or not.\n2. Components have asset management system(s) for user devices (phones, desktops, laptops) that maintains IT compliance, which is reported up to DoD enterprise.\n3. Components asset management systems can programmatically (i.e., API) provide device compliance status and if it meets minimum standards.",
        "end_state": "UEDM implementation enables effective patch management and configuration baselines. It also provides an ability to deny/quarantine devices remotely that are not in compliance.",
        "predecessors": "", "successors": "Enterprise PKI Pt1", "sprint": "Sprint 3", "team": "Endpoint Sec", "priority": "High"
    },
    {
        "id": "2.6.2", "name": "Enterprise Device Management Pt1", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 17.6,
        "description": "DoD Enterprise sets standards and policies for Enterprise Device Management (EDM). DoD Components migrate the manual device inventory to an automated approach using an EDM solution. Approved devices are able to be managed regardless of location. Devices part of critical services are managed by the EDM solution supporting automation.",
        "outcomes": "1. Enterprise sets standards and policies for EDM.\n2. Components manual inventory is integrated with an automated management solution for critical services.\n3. Components enable ZT device management (from any location with or without remote access).\n4. Where applicable, ensure tracking of NPEs in the UEM solution.",
        "end_state": "Implementing consistent and well-defined processes and controls for managing devices.",
        "predecessors": "", "successors": "NPE/PKI Device Under Management; Enterprise Device Management Pt2; Resource Authorization Pt1", "sprint": "Sprint 2", "team": "Endpoint Sec", "priority": "High"
    },
    {
        "id": "2.6.3", "name": "Enterprise Device Management Pt2", "pillar": "Device", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 12.6,
        "description": "DoD Components migrate the remaining devices to Enterprise Device Management (EDM) solution. EDM solution is integrated with risk and compliance solutions as appropriate.",
        "outcomes": "1. Manual inventory of devices, software, and security posture of each device is integrated with an automated management solution for all services.",
        "end_state": "All devices are managed and automation is utilized where applicable for rapid threat mitigation.",
        "predecessors": "Enterprise Device Management Pt1", "successors": "", "sprint": "Sprint 3", "team": "Endpoint Sec", "priority": "Medium"
    },
    {
        "id": "2.7.1", "name": "Implement Endpoint Detection & Response (EDR) Tools and Integrate with C2C", "pillar": "Device", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 16.5,
        "description": "DoD Components procure and implement Endpoint Detection and Response (EDR) solution(s) within environments. EDR is protecting, monitoring, and responding to malicious and anomalous activities enabling ZT Target Level functionality and is sending data to the Comply to Connect (C2C) solution for expanded device and user checks.",
        "outcomes": "1. EDR tooling is implemented.\n2. Critical EDR data is being sent to C2C for checks.\n3. Endpoint Protection Platform (EPP) tooling covers maximum amount of services/applications.",
        "end_state": "Detect advanced threats that are undetectable by a traditional antivirus program, optimizing the response time of incidents, discarding false positives, implement blocking, and protect against multiple threats happening simultaneously across various threat vectors.",
        "predecessors": "Integrate NextGen AV Tools with C2C", "successors": "Implement Extended Detection & Response (XDR) Tools and Integrate w/C2C Pt 1", "sprint": "Sprint 3", "team": "Endpoint Sec", "priority": "Critical"
    },
    {
        "id": "2.7.2", "name": "Implement Extended Detection & Response (XDR) Tools and Integrate with C2C Pt1", "pillar": "Device", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 19.2,
        "description": "DoD Components procure and implement Extended Detection & Response (XDR) solution(s). Integration points with cross pillar capabilities (network, cloud services, applications) are identified and prioritized based on risk. XDR is aligned with C2C program. XDR capabilities either supplement or replace EDR implementations. Analysis and correlation capabilities are sent from the XDR solution stack to the SIEM.",
        "outcomes": "1. XDR solution is implemented, and replaces EDR where possible.\n2. Integration points have been identified and prioritized per capability.\n3. XDR and SIEM have integrations to gain a comprehensive view of data integration, correlation, analytics, incident response, and automation.",
        "end_state": "Expanding from an EDR to an XDR solution provides a holistic view of the threat landscape, allowing for coordinated response, automation, and orchestration when responding to threats.",
        "predecessors": "Implement Endpoint Detection & Response (EDR) Tools and Integrate w/C2C; Threat Alerting Pt1", "successors": "Implement Extended Detection & Response (XDR) Tools and Integrate w/C2C Pt 2", "sprint": "Sprint 4", "team": "Endpoint Sec", "priority": "High"
    },
    {
        "id": "2.7.3", "name": "Implement Extended Detection & Response (XDR) Tools and Integrate with C2C Pt2", "pillar": "Device", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 19.9,
        "description": "Extended Detection & Response (XDR) solution stack completes identification of integration points expanding coverage to the fullest amount possible. Exceptions are tracked and managed using a risk-based approach for continued operation. Extended analytics enabling ZT Advanced Level functionalities are integrated into the SIEM and other appropriate solutions.",
        "outcomes": "1. Remaining integration points have been integrated, with exceptions for operational integrity being tracked.\n2. XDR solutions, along other Analytic tools, enhance alerting and responses with SIEM, and other solutions.",
        "end_state": "Full cross-pillar XDR orchestration with unified SIEM alert correlation.",
        "predecessors": "Implement Extended Detection & Response (XDR) & Integrate w/C2C Pt 1", "successors": "Threat Alerting Pt3", "sprint": "Sprint 6+", "team": "Endpoint Sec", "priority": "Medium"
    },

    # --- PILLAR 3: APPLICATIONS & WORKLOADS (18 activities) ---
    {
        "id": "3.1.1", "name": "Application/Code Identification", "pillar": "Applications & Workloads", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 16.7,
        "description": "DoD Components create an inventory of approved applications and code being used, including open-source, commercial, and in-house developed software. Each Component will track the supportability (i.e., active, legacy, etc.) hosted location (i.e., cloud, on-premises, hybrid, etc.) and record important data (i.e., name, version, team responsible, licensing and support, mapped dependencies).",
        "outcomes": "1. Component has identified applications and classified as either legacy, virtualized on-premises, and cloud hosted.\n2. Applications and codes are tracked by vendor, version number, commercial name, and patch level.",
        "end_state": "Develop an inventory to better support patch management and supply chain risk management increasing security by identifying unauthorized apps and identify security vulnerabilities.",
        "predecessors": "", "successors": "", "sprint": "Sprint 1", "team": "DevSecOps", "priority": "High"
    },
    {
        "id": "3.2.1", "name": "Build DevSecOps Software Factory Pt1", "pillar": "Applications & Workloads", "responsibility": "Enterprise",
        "type": "Target Level ZT", "duration": 19.3,
        "description": "The DoD Enterprise provide best practices for modern DevSecOps processes and CI/CD pipelines. The concepts are applied in a standardized technology stack across DoD Components able to meet future Application Security requirements, including requirements gathering, design, development, testing and deployment.",
        "outcomes": "1. Developed security best practices for DevSecOps and CI/CD pipelines.\n2. Vulnerability management is integrated into CI/CD pipelines.",
        "end_state": "Implementing consistent and well-defined processes and controls for DevSecOps.",
        "predecessors": "", "successors": "Build DevSecOps Software Factory Pt2; Automate Application Security & Code Remediation Pt1", "sprint": "Sprint 4", "team": "DevSecOps", "priority": "High"
    },
    {
        "id": "3.2.2", "name": "Build DevSecOps Software Factory Pt2", "pillar": "Applications & Workloads", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 10.8,
        "description": "DoD Components use their approved CI/CD pipelines to develop most new applications. Any exceptions will follow a standardized approval process to be allowed to develop in a legacy fashion. DevSecOps processes are also used to develop all new applications and update existing applications. Continual validation functions are integrated into the CI/CD pipelines and DevSecOps processes and integrated with existing applications.",
        "outcomes": "1. Implement Component CI/CD pipeline(s) and Software Factory per the DoD CIO DevSecOps Instruction/Directive.\n2. Application development adopts the use of CI/CD pipelines.\n3. Continual validation process/technology is implemented and in use (see 'Continual Validation' activity).\n4. Application development adopts the use of the DevSecOps process and technology.",
        "end_state": "Ensure code changes and updates are secure and compliant, reducing risk of an exploit.",
        "predecessors": "Build DevSecOps Software Factory Pt1", "successors": "Continuous Authorization to Operate (cATO) Pt1", "sprint": "Sprint 5", "team": "DevSecOps", "priority": "High"
    },
    {
        "id": "3.2.3", "name": "Automate Application Security & Code Remediation Pt1", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 18.0,
        "description": "A standardized approach to application security including code remediation is implemented across the DoD enterprise. Part one (1) of this activity includes the integration of securing API gateways (i.e., API management, WAF, continuous API testing, distributed enforcement not just perimeter) with applications utilizing API or similar calls. Code reviews are conducted in a methodical approach, and standardized protections for containers and their infrastructure are in place. Additionally, any serverless functions where the 3rd party manages the infrastructure, such as Platform as a Service, utilize adequate serverless security monitoring and response functions. Code reviews, container and serverless security functions are integrated into the CI/CD and/or DevSecOps process, as appropriate.",
        "outcomes": "1. Enterprise sets standardized approach to application security, including code remediation.\n2. Secure API Gateway is operational, and the majority of API calls are passing through the gateway.\n3. Application Security functions (e.g., code review, container and serverless security) are implemented as part of CI/CD and DevSecOps.",
        "end_state": "Standardize and modernize security infrastructure tools and security integration into application development processes.",
        "predecessors": "Vulnerability Management Program Pt2; Implement Asset, Vulnerability and Patch Management Tools; Build DevSecOps Software Factory Pt1", "successors": "Automate Application Security & Code Remediation Pt2; REST API Micro-Segments", "sprint": "Sprint 4", "team": "DevSecOps", "priority": "High"
    },
    {
        "id": "3.2.4", "name": "Automate Application Security & Code Remediation Pt2", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 16.2,
        "description": "DoD Components modernize approaches to delivering internally developed and managed applications following best practice approaches such as a Microservices architecture. These approaches will enhance security and resilience by enabling rapid code updates within individual microservices to address vulnerabilities. Further enhance application security by integrating runtime security functions for containers where applicable, automating vulnerable library updates, and automating CI/CD approvals during the release process.",
        "outcomes": "1. Secure API Gateway is operational, and majority of API calls are passing through API gateway.\n2. Services are provided following a Service Oriented Architecture (SOA).\n3. Security Remediation activities (e.g., runtime security, library updates, release approvals) are fully automated.",
        "end_state": "Automated runtime container security and automated dependency remediation.",
        "predecessors": "Automate Application Security & Code Remediation Pt1", "successors": "", "sprint": "Sprint 6+", "team": "DevSecOps", "priority": "Medium"
    },
    {
        "id": "3.3.1", "name": "Approved Binaries/Code", "pillar": "Applications & Workloads", "responsibility": "Enterprise",
        "type": "Target Level ZT", "duration": 23.4,
        "description": "The DoD Enterprise uses best practices to manage approved binaries and code in a methodical approach, including supplier sourcing risk management, approved repository usage, Software Bill of Materials (SBOM), supply chain risk management, and industry-standard vulnerability management.",
        "outcomes": "1. Supplier sourcing risk evaluated and identified for approved sources.\n2. Repository and update channel established for use by development teams.\n3. SBOMs are created for applications to identify source, supportability, and risk posture.\n4. Defense Industry Base (DIB) standards and approved vulnerability databases are pulled in to be used in DevSecOps.",
        "end_state": "Safeguard the creation, storage, and delivery of code",
        "predecessors": "", "successors": "Vulnerability Management Program Pt1", "sprint": "Sprint 4", "team": "DevSecOps", "priority": "High"
    },
    {
        "id": "3.3.2", "name": "Vulnerability Management Program Pt1", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 7.8,
        "description": "The DoD Enterprise collaborates with Components to establish and manage a comprehensive Vulnerability Management program. The program, at a minimum, encompasses the tracking and management of public vulnerabilities based on DoD applications and services. Each Component is responsible for establishing a vulnerability management team comprised of key stakeholders. This team convenes to discuss and manage vulnerabilities in accordance with established Enterprise policy and standards.",
        "outcomes": "1. Components establish a vulnerability management governance team with appropriate stakeholder membership.\n2. Enterprise provides a vulnerability management policy and standard for minimum tracking and management of public vulnerabilities based on DoD applications and services.",
        "end_state": "Provide structure and an approach to addressing vulnerabilities in accordance with Enterprise policy.",
        "predecessors": "", "successors": "Approved Binaries/Code; Vulnerability Management Program Pt2", "sprint": "Sprint 4", "team": "SecOps Team", "priority": "High"
    },
    {
        "id": "3.3.3", "name": "Vulnerability Management Program Pt2", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 12.1,
        "description": "Processes are established at the DoD Enterprise level for managing the disclosure of vulnerabilities in DoD maintained and operated services, both publicly and privately accessible. DoD Components expand the vulnerability management program to track and manage closed vulnerability repositories such as DIB-VDP, CERT, and others.",
        "outcomes": "1. Components utilize controlled (e.g., DIB-VDP, CERT) sources for tracking vulnerabilities.\n2. Enterprise sets minimum standards for vulnerability management program accepting external/public disclosures for managed services.\n3. Vulnerability remediation plans are developed and implemented at the Component level.",
        "end_state": "Enterprise-established processes for automated threat sharing from controlled sources are integrated into Component vulnerability management programs.",
        "predecessors": "Vulnerability Management Program Pt1", "successors": "Automate Application Security & Code Remediation Pt1", "sprint": "Sprint 4", "team": "SecOps Team", "priority": "Medium"
    },
    {
        "id": "3.3.4", "name": "Continual Validation", "pillar": "Applications & Workloads", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 11.1,
        "description": "DoD Components implement a continuous validation approach for application development, where security is constantly assessed throughout the development, integration, and deployment. Validation includes security principles when planning and designing, security testing (to include code reviews), incident response, and SIEM alerting/logging. These principles are integrated and continuously executed with the CI/CD pipeline. Applications developed outside of CI/CD process should still adhere to continuous validation in an ad hoc/manual manner.",
        "outcomes": "1. Continual validation tools are implemented and applied to code in the CI/CD pipeline.\n2. Updated applications are only deployed in a live and/or production environment with a continuous validation approach.\n3. Applications developed outside of CI/CD pipeline are still validated in a ad hoc/manual manner, as established in the continuous validation approach.",
        "end_state": "Establish a continuous validation process and tooling that are seamlessly integrated with application planning and design, security testing, incident response, and SIEM alerting/logging.",
        "predecessors": "", "successors": "", "sprint": "Sprint 5", "team": "DevSecOps", "priority": "High"
    },
    {
        "id": "3.4.1", "name": "Resource Authorization Pt1", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 18.5,
        "description": "The DoD Enterprise standardizes policy enforcement approaches (e.g., Software Defined Perimeter) with the Components. At a minimum, the access and authorization gateways will be integrated with identities and devices once authentication is achieved. Components deploy approved resource authorization gateways and enable them for external facing applications and services. Additional applications for migration and applications unable to be migrated are identified for exception or decommission.",
        "outcomes": "1. DoD Enterprise sets standards on policy enforcement approach. At a minimum, access and authorization is integrated with identities and devices once authentication is achieved.\n2. Components deploy approved resource authorization gateways and enable them for external facing applications and services.\n3. DoD Enterprise-wide interoperability guidance is communicated to stakeholders.",
        "end_state": "Policy enforcement points are fully integrated with identity and device management systems, ensuring consistent and secure access control across the Enterprise.",
        "predecessors": "Single Authentication; Datacenter Macro segmentation; Enterprise Device Management Pt1", "successors": "Resource Authorization Pt2", "sprint": "Sprint 5", "team": "DevSecOps", "priority": "Critical"
    },
    {
        "id": "3.4.2", "name": "Resource Authorization Pt2", "pillar": "Applications & Workloads", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 20.6,
        "description": "Policy enforcements and decisions are used for all possible applications and services. Application unable to utilize gateways are either decommissioned or accepted using a risk-based methodical approach. Authorizations are further integrated with the CI/CD pipeline for automated decision making.",
        "outcomes": "1. Policy enforcement is utilized for all applications and services.\n2. Applications and services are identified that are accepted or decommissioned.",
        "end_state": "Resource authorization gateways leveraging PDP and PEP integrated with identity and access management systems are implemented for all applications. Authorization policies are embedded within DevSecOps and the CI/CD pipeline to ensure automated, continuous, and secure access control decisions.",
        "predecessors": "Resource Authorization Pt1", "successors": "", "sprint": "Sprint 5", "team": "DevSecOps", "priority": "High"
    },
    {
        "id": "3.4.3", "name": "SDC Resource Authorization Pt1", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 31.1,
        "description": "The DoD Enterprise establishes best practices for code-based compute management (i.e., Software Defined Compute(SDC)). Using risk-based approaches, baselines are created using the approved set of code libraires and packages. DoD Components work with the approved code/binaries activities to ensure that applications are identified which can and cannot support the approach. Applications that can support a modern software-based configuration and management approaches are identified, and transitioning begins. Applications that cannot follow software-based configuration and management approaches are identified and allowed through exception using a methodical approach.",
        "outcomes": "1. Enterprise-wide guidance on SDC standards are communicated to stakeholders.\n2. Components identify applications that can support the SDC approach.",
        "end_state": "Enterprise best practices support Component efforts in leveraging SDC capabilities.",
        "predecessors": "", "successors": "SDC Resource Authorization Pt2", "sprint": "Sprint 4", "team": "DevSecOps", "priority": "Medium"
    },
    {
        "id": "3.4.4", "name": "SDC Resource Authorization Pt2", "pillar": "Applications & Workloads", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 21.8,
        "description": "Components use approved and validated code/binaries via the Software Bill of Materials (SBOM) process to ensure that applications that can and cannot support the approach are identified. Applications which can support modern Software-Based Configuration and Management (SBCM) approaches are identified and transitioned. Applications that support SBCM have been transitioned to a production/live environment and are in normal operations. Applications which cannot SBCM are identified and allowed through exception using a risk-based approach.",
        "outcomes": "1. Updated applications are deployed in a live and/or production environment.\n2. Applications that were marked for retirement and transition have a decommissioned indicator.\n3. Applications unable to be updated to an approved binaries/code are marked for retirement and transition plans are created.\n4. Identified applications are updated to use approved binaries/code.",
        "end_state": "Components operationalize validated code and binaries through use in the production environment",
        "predecessors": "SDC Resource Authorization Pt1; Single Authentication; Datacenter Macro-Segmentation", "successors": "", "sprint": "Sprint 5", "team": "DevSecOps", "priority": "High"
    },
    {
        "id": "3.4.5", "name": "Enrich Attributes for Resource Authorization Pt1", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 17.6,
        "description": "Initial attributes from various sources, such as User and Entity Activity Monitoring (UEAM), micro-segmentation services, Data Loss Prevention (DLP), and Digital Rights Management (DRM) tools are integrated with the Resource Authorization technology system and policies. Any additional attributes for later integration are identified and planned. Attributes are used to create basic risk posture of users, NPEs and devices allowing for authorization decisions based on the evaluated risk.",
        "outcomes": "1. Most API calls are passing through the Secure API Gateway.\n2. Resource Authorization receives data from Analytics Engine.\n3. Authorization policies incorporate identified attributes in making authorization decisions.\n4. Attributes to be used for initial enrichment are identified and assigned to resources and/or entities.",
        "end_state": "Dynamic resource authorization enriched with live behavioral risk attributes.",
        "predecessors": "User Activity Monitoring Pt2; Entity Activity Monitoring Pt2; Application & Device Micro segmentation; Manual Data Tagging Pt2; DLP Enforcement via Data Tags and Analytics Pt2; DRM Enforcement via Data Tags and Analytics Pt2", "successors": "Enrich Attributes for Resource Authorization Pt2", "sprint": "Sprint 6+", "team": "DevSecOps", "priority": "Medium"
    },
    {
        "id": "3.4.6", "name": "Enrich Attributes for Resource Authorization Pt2", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 17.8,
        "description": "Extended identified attributes are integrated with the resource authorization technology and policy. Confidence scoring system is introduced for identified attributes to create a more advanced method of authorization decision making supporting.",
        "outcomes": "1. Authorization policies incorporate confidence levels in making authorization decisions.\n2. Confidence levels for attributes are defined.",
        "end_state": "Confidence scoring system governs real-time API resource authorization.",
        "predecessors": "Enrich Attributes for Resource Authorization Pt1", "successors": "", "sprint": "Sprint 6+", "team": "DevSecOps", "priority": "Medium"
    },
    {
        "id": "3.4.7", "name": "REST API Micro-Segments", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 18.1,
        "description": "Using the DoD Enterprise approved API gateway(s), application calls are micro-segmented, only allowing authenticated and authorized access to specific destinations (e.g., microservices). When possible, API micro-segmentation consoles are integrated and aware of other micro-segmentation consoles such as Software Defined Perimeter (SDP)controllers and/or Software Defined Networking (SDN) consoles.",
        "outcomes": "1. Approved Enterprise APIs are micro-segmented appropriately.",
        "end_state": "REST APIs micro-segmented with SDP and SDN integration.",
        "predecessors": "Automate Application Security & Code Remediation Pt1", "successors": "", "sprint": "Sprint 6+", "team": "DevSecOps", "priority": "Medium"
    },
    {
        "id": "3.5.1", "name": "Continuous Authorization to Operate (cATO) Pt1", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 15.1,
        "description": "DoD Components utilize automation solutions within the environment to standardize the monitoring of controls and offer the capability to identify deviations. Where appropriate, monitoring and testing is integrated with DevSecOps processes.",
        "outcomes": "1. Controls derivation is standardized and ready for automation.\n2. Controls testing is integrated with DevSecOps processes and technology.",
        "end_state": "Standardized continuous control derivation integrated with DevSecOps CI/CD.",
        "predecessors": "Policy Inventory & Development; Build DevSecOps Software Factory Pt2", "successors": "Continuous Authorization to Operate (cATO) Pt2", "sprint": "Sprint 6+", "team": "DevSecOps", "priority": "High"
    },
    {
        "id": "3.5.2", "name": "Continuous Authorization to Operate (cATO) Pt2", "pillar": "Applications & Workloads", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 21.8,
        "description": "DoD Components fully automate control derivation, testing and monitoring processes. Deviations are automatically tested and resolved using existing cross pillar automation infrastructure. Dashboards are used to monitor the status of authorizations; analytics are integrated with the responsible authorizing officials.",
        "outcomes": "1. Controls testing is fully automated.\n2. Integration with standard IR and SOC operations is automated.\n3. Control derivation and applicability is fully automated.\n4. Dashboards are used to track continuing authorization status.",
        "end_state": "Full cATO pipeline operational with automated AO dashboard integration.",
        "predecessors": "Continuous Authorization to Operate (cATO) Pt1; Threat Alerting Pt3; Automated Workflow", "successors": "", "sprint": "Sprint 6+", "team": "DevSecOps", "priority": "Critical"
    },

    # --- PILLAR 4: DATA (26 activities) ---
    {
        "id": "4.1.1", "name": "Data Analysis", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 17.4,
        "description": "The DoD Enterprise will develop algorithm(s) for components to map data for tagging and labeling, and establish the governing body for oversight. Data at a Component level should be categorized and analyzed by an overseeing governing body.",
        "outcomes": "1. Algorithms are entered into an algorithm registry with appropriate tagging and labeling set by the Enterprise to allow search and retrieval as appropriate (e.g., accommodating data catalog risk alignment).\n2. Component data catalog is updated with data types for each application and service based on data classification levels.",
        "end_state": "Data analysis ensures data protection and reduces risk. All problems have a data analysis algorithm registered in a repository with associated data indicated, and the oversight governance body has awareness that is Visibile, Accessible, Understandable, Linked, Trusted, Interoperable, and Secure (VAULTIS) compliant.",
        "predecessors": "", "successors": "Manual Data Tagging Pt1", "sprint": "Sprint 4", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.2.1", "name": "Define Data Tagging Standards", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 15.8,
        "description": "Data tagging standard for identifying ZT labels must be defined. The DoD Enterprise works with Components to establish data tagging and classification standards based on industry best practices. Classifications are agreed upon and implemented in processes. Tags are identified as manual and automated for future activities.",
        "outcomes": "1. Enterprise establishes the standard pattern for control vocabulary and how it is managed.\n2. Components align to Enterprise standards and begin implementation.\n3. Components implement data tagging and labeling standards.",
        "end_state": "The data dictionary and structure is developed at a broader DoD Enterprise level. ZT specific data attributes are defined in alignment with the Enterprise data dictionary and structure.",
        "predecessors": "", "successors": "Implement Data Tagging & Classification Tools; Manual Data Tagging Pt1; Automated Data Tagging & Support Pt1; Implement Data Tagging & Classification ML Tools", "sprint": "Sprint 4", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.2.2", "name": "Interoperability Standards", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 14.4,
        "description": "The DoD Enterprise, collaborating with Components, develops interoperability standards methods including mandatory Data Rights Management (DRM) overlays and Protection mechanisms with necessary technologies to enable ZT Target Level functionality.",
        "outcomes": "1. Standard patterns are in place by the Enterprise for appropriate interoperability data sharing.",
        "end_state": "Interoperability standards for DRM and protection are established and enforced across the Enterprise. These standards are supported by a common language (terms list and scientific definitions) to ensure consistency and clarity. Equal computation outcomes are produced for any rule, and an action agent (enforcement) based on computational results is executed. this unified approach promotes secure, consistent, and compliant data management.",
        "predecessors": "", "successors": "Implement DRM and Protection Tools Pt1", "sprint": "Sprint 4", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.2.3", "name": "Develop Software Defined Storage (SDS) Policy", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 9.9,
        "description": "The DoD enterprise will work with Components to determine if software define storage (SDS) is in use. DoD Components develop policy and standards based on industry best practices, and evaluate current data storage strategy and technology for implementation of SDS.Components assess their existing data storage strategies and technologies to determine the suitability for implementing SDS. If deemed appropriate, the identified storage technologies are considered for SDS implementation.",
        "outcomes": "1. Enterprise defines and refines minimum attribution requirements for SDS to support Zero Trust enablement.\n2. Components assess their existing data storage for SDS implementation considerations.",
        "end_state": "Ensure holistic approach for SDS security alignment within Components to strengthen access and availability, data protection, and adherence best practices.",
        "predecessors": "", "successors": "Integrate DAAS Access w/SDS Policy Pt1; Integrate Solution & Policy w/Enterprise IDP Pt1; Implement SDS Tool and/or integrate with DRM Tool Pt1", "sprint": "Sprint 4", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.3.1", "name": "Implement Data Tagging & Classification Tools", "pillar": "Data", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 15.9,
        "description": "DoD Components implement a solution to create new rules, modify existing rules, delete existing rules, check for rule collision, rule deviation, or compound rule inconsistency, and testing of collective rule sets for an outcome. Tools must be adaptable to advanced analytic techniques.",
        "outcomes": "1. Tooling is designed based on Component data tagging efforts that are well-formed with Enterprise-dictated patterns and standards, and are machine readable.\n2. Data classification uses data tagging attribution to specify allowed values.",
        "end_state": "All valid tags can be processed; all invalid tags cannot.",
        "predecessors": "Define Data Tagging Standards", "successors": "Implement Enforcement Points", "sprint": "Sprint 4", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.3.2", "name": "Manual Data Tagging Pt1", "pillar": "Data", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 17.6,
        "description": "Components map DoD Enterprise ZT tags to local labeling to meet minimum essential metadata criteria for compliance.",
        "outcomes": "1. Data tagging is conducted at the Component-level with basic attributes.",
        "end_state": "A standardized data tagging and labeling solution is in place, ensuring all Components comply with ZT principles. Metadata criteria are consistently applied, enhancing data security and access control across the Enterprise.",
        "predecessors": "Data Analysis; Define Data Tagging Standards", "successors": "Manual Data Tagging Pt2; DRM Enforcement via Data Tags and Analytics Pt1; DLP Enforcement via Data Tags and Analytics Pt1", "sprint": "Sprint 4", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.3.3", "name": "Manual Data Tagging Pt2", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 16.1,
        "description": "DoD Component specific data level attributes are integrated into the manual data tagging process. DoD Enterprise and Components collaborate to decide which attributes are required to meet ZT Advanced Level functionality. Data level attributes for ZT Advanced Level functionality is standardized across the Enterprise and incorporated.",
        "outcomes": "1. Manual data tagging is expanded to the program/org levels with specific attributes.",
        "end_state": "Program-level specific metadata attributes integrated into manual tagging schema.",
        "predecessors": "Manual Data Tagging Pt1", "successors": "Enrich Attributes for Resource Authorization Pt1", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.3.4", "name": "Automated Data Tagging & Support Pt1", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 14.1,
        "description": "DoD Components use Data Loss Prevention (DLP), Data Rights Management (DRM), and/or protection solutions to conduct scanning of data repositories. Standardized tags are applied to supported data repositories and data types. Unsupported data repositories and types are identified.",
        "outcomes": "1. Basic automation begins scanning data repositories and applying tags.",
        "end_state": "Automated scanning and tag injection across supported file shares and DBs.",
        "predecessors": "Implement Data Tagging & Classification ML Tools", "successors": "Automated Data Tagging & Support Pt2", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.3.5", "name": "Automated Data Tagging & Support Pt2", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 38.8,
        "description": "Remaining supported data repositories have basic and extended data tags applied using Machine Learning (ML) and Artificial Intelligence (AI). Extended data tags are applied to existing repositories. Unsupported data repositories and data types are evaluated for decommissioning using a risk-based methodical approach. Approved exceptions utilize manual data tagging approaches with data owners and/or custodians to manage tagging.",
        "outcomes": "1. Full automation of data tagging is completed.\n2. Results of data tagging are fed into ML algorithms to develop AI driven data tagging.",
        "end_state": "Complete AI/ML driven automated data discovery and tagging engine.",
        "predecessors": "Automated Data Tagging & Support Pt1", "successors": "", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.4.1", "name": "DLP Enforcement Point Logging and Analysis", "pillar": "Data", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 10.8,
        "description": "DoD Components identify business rules for managing data loss prevention (DLP) enforcement points, such as specific services and user endpoints. Using the established DoD Enterprise cybersecurity incident response standard, DoD Components ensure the appropriate level of detail of data is captured. Additionally, protection, detection, and response use cases are developed to better outline solution coverage.",
        "outcomes": "1. Business rules for access control are established and coordinated with Cyber Operations to support standardized logging for managing DLP enforcement.\n2. Standardized logging schema is enforced at the Component-level.\n3. Components identify enforcement points.",
        "end_state": "The right people are allowed to access the right data in the right place at the right time. Data loss prevention rules restrict exfiltration of information from an access control boundary, enhance visibility, and prevent data breaches when aligned with an incident response standard",
        "predecessors": "", "successors": "Comprehensive Data Activity Monitoring", "sprint": "Sprint 4", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.4.2", "name": "DRM Enforcement Point Logging and Analysis", "pillar": "Data", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 12.6,
        "description": "DoD Components identify business rules for managing the accepted use of the assets managing Data Rights Management (DRM) enforcement points, such as specific services and user endpoints. Using the established DoD Enterprise cybersecurity incident response standard, DoD Components ensure the appropriate detail of data is captured. Additionally, protection, detection, and response use cases are developed to better outline solution coverage.",
        "outcomes": "1. Business rules for managing accepted use of data assets are established and coordinated with Cyber Operations to support standardized logging for managing DRM.\n2. Standardized logging schema is enforced at the Component-level.\n3. Components identify enforcement points.",
        "end_state": "Data Rights Management rules restrict the allowed use of information from the access control boundary.",
        "predecessors": "", "successors": "Comprehensive Data Activity Monitoring", "sprint": "Sprint 4", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.4.3", "name": "File Activity Monitoring Pt1", "pillar": "Data", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 16.8,
        "description": "DoD Components utilize File Monitoring tools to monitor the most critical data classification levels in applications, services, and repositories. Analytics from monitoring is fed into the SIEM with basic data attributes to accomplish ZT Target Level functionality.",
        "outcomes": "1. Data and files of critical data designation are identified and actively monitored.\n2. Establish and manage business rules to consume critical data designations and manage outcomes.\n3. Integration is in place with monitoring system (e.g., SIEM, XDR).",
        "end_state": "Files are associated with data assets and objects. File integrity monitoring occurs at the data asset and object levels, allowing for greater visibility and accuracy.",
        "predecessors": "", "successors": "File Activity Monitoring Pt2", "sprint": "Sprint 4", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.4.4", "name": "File Activity Monitoring Pt2", "pillar": "Data", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 18.9,
        "description": "DoD Components utilize File Monitoring tools to monitor all regulatory protected data (e.g., CUI, PII, PHI, etc.) in applications, services, and repositories. Extended integration is used to send data to appropriate inter/intra-pillar solutions such as Data Loss Prevention, Data Rights Management/Protection and User & Entity Behavior Analytics.",
        "outcomes": "1. Data and files of all regulated designations are identified and actively monitored.\n2. Establish and manage business rules to consume regulated designations and manage outcomes.",
        "end_state": "Components extend regulation to data files and integrations to strengthen data loss prevention, and prevent malicious attacks from spreading.",
        "predecessors": "File Activity Monitoring Pt1", "successors": "Rule Based Dynamic Access Pt2; Database Activity Monitoring; Comprehensive Data Activity Monitoring", "sprint": "Sprint 5", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.4.5", "name": "Database Activity Monitoring", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 18.2,
        "description": "DoD Components procure, implement, and utilize database monitoring solutions to monitor all databases containing regulated data types (e.g., CUI, PII, PHI, etc.). Logs and analytics from the database monitoring solution are provided to the SIEM for monitoring and response. Analytics are utilized in cross pillar activities such as 'Enterprise Security Profile Pt 1, Pt 2' and 'Real Time Access Decisions' to better direct decision making.",
        "outcomes": "1. Appropriate database are being actively monitored.\n2. Monitoring technology is integrated with solutions such as SIEM, PDP and dynamic access control mechanisms.",
        "end_state": "Continuous DAM telemetry sent to SIEM and PDP access controllers.",
        "predecessors": "File Activity Monitoring Pt2", "successors": "Comprehensive Data Activity Monitoring", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.4.6", "name": "Comprehensive Data Activity Monitoring", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 27.2,
        "description": "DoD Components expand monitoring of data repositories including databases as appropriate, based on a methodical risk-based approach. Additional data attributes to meet the ZT Advanced Level functionalities are integrated into the analytics for additional integrations.",
        "outcomes": "1. Data activity monitoring mechanisms are integrated to provide a unified view of monitoring across data repositories.\n2. Appropriate integrations exist.",
        "end_state": "Unified data activity telemetry across all structured and unstructured stores.",
        "predecessors": "DLP Enforcement Point Logging and Analysis; DRM Enforcement Point Logging and Analysis; Database Activity Monitoring", "successors": "AI-enabled Dynamic Access Control; FF Baseline & Profiling Pt. 2; AI-enabled Network Access", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.5.1", "name": "Implement DRM and Protection Tools Pt1", "pillar": "Data", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 11.7,
        "description": "DoD Components procure and implement DRM and Protection solution(s) as needed, following the DoD Enterprise standard and requirements. Newly implement DRM and protection solution(s) are applied with high-risk data objects.",
        "outcomes": "1. DRM and protection tools are enabled for high-risk data repositories with protections.",
        "end_state": "No high-risk data object bypasses the compliance requirement.",
        "predecessors": "Interoperability Standards", "successors": "Implement DRM and Protection Tools Pt2", "sprint": "Sprint 4", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.5.2", "name": "Implement DRM and Protection Tools Pt2", "pillar": "Data", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 22.0,
        "description": "DRM and protection coverage is expanded to cover all required data objects. Protection mechanisms are automatically managed to meet best practices (e.g., FIPS). Extended data protection attributes are implemented based on the environment classification.",
        "outcomes": "1. DRM and protection tools are enabled for all required repositories.",
        "end_state": "No data object bypasses the compliance requirement.",
        "predecessors": "Implement DRM and Protection Tools Pt1", "successors": "", "sprint": "Sprint 5", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.5.3", "name": "DRM Enforcement via Data Tags and Analytics Pt1", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 16.2,
        "description": "DoD Enterprise provides a standard for data access control and protections. Components establish data rights management (DRM) and protection solutions that are used with data tags defined by the data producer. High-risk data objects are identified and monitored with protect and response actions enabled. Data at rest is encrypted and protected (e.g., hardware/object/disk encryption, access control) in repositories.",
        "outcomes": "1. Components DRM utilizes Attribute-Based Access Control standards set by Enterprise.\n2. Based on data tags, data is encrypted at rest.",
        "end_state": "Protections are applied and appropriate access is enforced for each data object.",
        "predecessors": "Manual Data Tagging Pt1", "successors": "DRM Enforcement via Data Tags and Analytics Pt2", "sprint": "Sprint 5", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.5.4", "name": "DRM Enforcement via Data Tags and Analytics Pt2", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 19.0,
        "description": "Extended data repositories are protected with DRM and protection solutions. DoD Components implement extended data tags applicable to Components versus Enterprise. Data is encrypted in extended repositories using additional tags.",
        "outcomes": "1. All applicable data repositories are protected using DRM.\n2. Data is encrypted using extended data tags from the Component level.",
        "end_state": "Component-specific extended tags drive granular cryptographic access controls.",
        "predecessors": "DRM Enforcement via Data Tags and Analytics Pt1", "successors": "Enrich Attributes for Resource Authorization Pt1; DRM Enforcement via Data Tags and Analytics Pt3", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.5.5", "name": "DRM Enforcement via Data Tags and Analytics Pt3", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 23.3,
        "description": "DRM and protection solutions integrate with AI and ML tooling for encryption, rights management, and protection functions.",
        "outcomes": "1. Analytics from ML/AI are integrated with DRM to better automate protections.\n2. Encryption protection is integrated with AI/ML and updated encryption methods are used as needed.",
        "end_state": "AI/ML automation dynamically manages encryption algorithms and rights.",
        "predecessors": "DRM Enforcement via Data Tags and Analytics Pt2", "successors": "", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.6.1", "name": "Implement Enforcement Points", "pillar": "Data", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 21.2,
        "description": "Data loss prevention (DLP) is aligned to and strengthened by Data Privacy and Protection (DPP). Then through attribution, attributes can be injected that address where data is coming from, its movement across ZT control boundaries, and the invocation of protection measures (e.g., encryption, obfuscation, etc.). Data loss prevention (DLP) solution is deployed to the in-scope enforcement points. It is recommended to start with 'monitor-only' and/or 'learning' mode limiting impact. Collaboration with cyber functions should occur with respect to any observed data loss activity.",
        "outcomes": "1. A formal process is established with cybersecurity to share loss activity observations.\n2. Identified enforcement points have DLP tool deployed.",
        "end_state": "DLP solutions are effectively deployed at all identified enforcement points operating in monitor mode with standardized logging. Policies are continuously refined based on DLP results to ensure robust data protection and risk management. Collaborative efforts are established to share insights and strategies, enhancing overall data loss prevention activities across the Enterprise.",
        "predecessors": "Implement Data Tagging & Classification Tools", "successors": "Process Micro segmentation", "sprint": "Sprint 4", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.6.2", "name": "DLP Enforcement via Data Tags and Analytics Pt1", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 21.3,
        "description": "Data loss prevention (DLP) solution is updated from monitor only mode to prevention mode. Zero Trust tagging incorporates indicators to facilitate DLP through cooperative cyber enforcement.",
        "outcomes": "1. Enterprise sets the minimum standards for indicators that support cyber enforcement.\n2. Components technology is enabled for enforcement.",
        "end_state": "Support prevention of data loss through development of data attributes that support cyber enforcement of data loss.",
        "predecessors": "Manual Data Tagging Pt1", "successors": "DLP Enforcement via Data Tags and Analytics Pt2", "sprint": "Sprint 5", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.6.3", "name": "DLP Enforcement via Data Tags and Analytics Pt2", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 19.0,
        "description": "Data Loss Prevention (DLP) solution is updated to include extended data tags based on parallel automation activities.",
        "outcomes": "1. Enforcement points have extended data tag attributes applied for additional prevention.",
        "end_state": "Automated extended data tags enforced at all boundary egress points.",
        "predecessors": "DLP Enforcement via Data Tags and Analytics Pt1", "successors": "Enrich Attributes for Resource Authorization Pt1; DLP Enforcement via Data Tags and Analytics Pt3", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.6.4", "name": "DLP Enforcement via Data Tags and Analytics Pt3", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 41.6,
        "description": "Data Loss Prevention (DLP) solution is integrated with automated data tagging techniques, to include any missing enforcement points and tags.",
        "outcomes": "1. Automated tagging attributes are integrated with DLP and resulting metrics are used for ML.",
        "end_state": "Autonomous DLP prevention leveraging continuous ML classification streams.",
        "predecessors": "DLP Enforcement via Data Tags and Analytics Pt2", "successors": "", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.7.1", "name": "Integrate DAAS Access w/SDS Policy Pt1", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 15.3,
        "description": "Governance mechanisms ensure that component DAAS policy is sufficient for Zero Trust outcomes as established by the SDS policy, if deemed appropriate as established in '4.2.3 Develop Software Defined Storage (SDS) Policy'.",
        "outcomes": "1. DAAS access policy is developed with Enterprise and Component support.",
        "end_state": "A centralized DAAS security approach is implemented across the Enterprise exercising best practices, reducing risk and attack surface area.",
        "predecessors": "Develop Software Defined Storage (SDS) Policy", "successors": "Integrate DAAS Access w/SDS Policy Pt2", "sprint": "Sprint 5", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.7.2", "name": "Integrate DAAS Access w/SDS Policy Pt2", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 12.6,
        "description": "DoD Components implement the DAAS policy in an automated fashion.",
        "outcomes": "1. Attribute-based fine-grained DAAS Policy implemented in an automated fashion.",
        "end_state": "Attribute-based fine-grained DAAS automated access enforcement.",
        "predecessors": "Integrate DAAS Access w/SDS Policy Pt1; Implement SDS Tool and/or Integrate w/DRM Tool Pt1", "successors": "Integrate DAAS Access w/SDS Policy Pt3", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.7.3", "name": "Integrate DAAS Access w/SDS Policy Pt3", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 9.2,
        "description": "Newly implemented SDS technology and/or functionalities are integrated with the DAAS policy in a risk-based fashion. A phased approach is taken during implementation to measure results and adjust accordingly.",
        "outcomes": "1. SDS is integrated with DAAS policy functionality.\n2. All data in all applications are protected with attribute-based fine-grained DAAS policy.",
        "end_state": "100% fine-grained SDS protection across all enterprise application stores.",
        "predecessors": "Integrate DAAS Access w/SDS Policy Pt2", "successors": "", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.7.4", "name": "Integrate Solution(s) and Policy with Enterprise IDP Pt1", "pillar": "Data", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 13.9,
        "description": "DoD Components integrate attributes associated with access control and data location, and establishes a means for interoperability across DLP, DRM, and storage infrastructure solutions with Enterprise IdP.",
        "outcomes": "1. Component data security solutions are integrated with IdP (e.g. API, LDAP, SAML).",
        "end_state": "Integrating DLP, DRM, and SDS with the IdP solution to ensure data protection and access is granted to only authenticated and authorized users.",
        "predecessors": "Develop Software Defined Storage (SDS) Policy; Enterprise IDP Pt1", "successors": "Integrate Solution & Policy w/Enterprise IDP Pt2; Implement SDS Tool and/or integrate with DRM Tool Pt1", "sprint": "Sprint 5", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "4.7.5", "name": "Integrate Solution(s) and Policy with Enterprise IDP Pt2", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 9.2,
        "description": "Newly implemented SDS technology and/or functionalities are integrated with the Enterprise Identity Provider (IdP) following the integration plan. Identity attributes required to meet ZT Target Level functionalities are required for integration.",
        "outcomes": "1. Complete integration with Enterprise IdP and SDS tooling to support all attribute-based fine-grained DAAS access.",
        "end_state": "Unified fine-grained authorization joining Enterprise IdP attributes with SDS policy.",
        "predecessors": "Integrate Solution & Policy w/Enterprise IDP Pt1", "successors": "", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.7.6", "name": "Implement SDS Tool and/or integrate with DRM Tool Pt1", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 17.4,
        "description": "Depending on the need for a Software Defined Storage (SDS) tool, a new solution is implemented, or an existing solution is identified, meeting the functionality requirements to be integrated with DLP, DRM, and ML solutions.",
        "outcomes": "1. If tooling is needed, ensure there is supported integrations with DLP, DRM and ML tooling.",
        "end_state": "SDS tooling integrated with DRM and ML classifiers.",
        "predecessors": "Develop Software Defined Storage (SDS) Policy; Integrate Solution & Policy w/Enterprise IDP Pt1", "successors": "Integrate DAAS Access w/SDS Policy Pt2; Implement SDS Tool and/or Integrate w/DRM Tool Pt2", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },
    {
        "id": "4.7.7", "name": "Implement SDS Tool and/or integrate with DRM Tool Pt2", "pillar": "Data", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 15.3,
        "description": "DoD Components configure the SDS functionality and/or solution to be integrated with the underlying DLP and DRM infrastructure as appropriate. Lower-level integrations enable more effective protection and response.",
        "outcomes": "1. Integrate SDS infrastructure with existing DLP and DRM infrastructure.",
        "end_state": "Deep storage fabric integration with automated DLP block/encrypt hooks.",
        "predecessors": "Implement SDS Tool and/or Integrate w/DRM Tool Pt1", "successors": "", "sprint": "Sprint 6+", "team": "Data Governance", "priority": "Medium"
    },

    # --- PILLAR 5: NETWORK & ENVIRONMENT (13 activities) ---
    {
        "id": "5.1.1", "name": "Define Granular Control Access Rules & Policies Pt1", "pillar": "Network & Environment", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 10.3,
        "description": "The DoD Enterprise working with the Components creates granular network access rules and policies. Associated Concept of Operations (ConOps) are developed in alignment with access policies as well ensure future supportability. Once agreed upon, DoD Components will implement these access policies into existing network technologies (e.g., Next Generation Firewalls, Intrusion Prevention Systems, etc.) to improve initial risk levels and ensure future interoperability.",
        "outcomes": "1. Enterprise provides standardized policy for deployment.\n2. Identify Communities of Interest.\n3. Components implement access policies according to Enterprise standards and CONOPS.",
        "end_state": "Provide access control over multiple identities, applications, devices, and traffic levels, reducing the risk of unauthorized accessing and increasing visibility on monitoring for threat response.",
        "predecessors": "", "successors": "Define SDN APIs; Define Granular Control Access Rules & Policies Pt2", "sprint": "Sprint 5", "team": "NetSec Team", "priority": "High"
    },
    {
        "id": "5.1.2", "name": "Define Granular Control Access Rules & Policies Pt2", "pillar": "Network & Environment", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 8.0,
        "description": "DoD Components utilize data tagging and classification standards to develop data filters for API access to the SDN or alternative networking approach. API Decision Points are formalized within the SDN or alternative network architecture and implemented with non-mission/task critical applications and services.",
        "outcomes": "1. Define data tagging filters for API infrastructure to support interoperability.\n2. Enforce authentication for all APIs at the API layer.",
        "end_state": "Security is enforced at an API level to strengthen authorization and authentication, promote enabling encryption protocols, and support monitoring of malicious behavior at an API level to improve incident response.",
        "predecessors": "Define Granular Control Access Rules & Policies Pt1", "successors": "", "sprint": "Sprint 5", "team": "NetSec Team", "priority": "High"
    },
    {
        "id": "5.2.1", "name": "Define SDN APIs", "pillar": "Network & Environment", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 8.3,
        "description": "The DoD Enterprise works with Components to define the necessary APIs and other programmatic interfaces that enable Software Defined Networking (SDN) or alternative networking approach functionalities. These APIs will enable authentication decision point, application delivery control proxy and segmentation gateways automation.",
        "outcomes": "1. SDN or alternative networking approach APIs are developed using machine readable patterns and protocols and implemented (per 'Standardized API Calls & Schemas Pt1 and Pt2').",
        "end_state": "SDN or alternative networking approach APIs are standardized and implemented, enabling robust automation of authentication decision points, application delivery control proxies, and segmentation gateways. This standardization ensures consistent and secure SDN or alternative networking approache operations across the Enterprise, enhancing network flexibility, scalability, and security.",
        "predecessors": "Define Granular Control Access Rules & Policies Pt1", "successors": "Implement SDN Programable Infrastructure", "sprint": "Sprint 5", "team": "NetSec Team", "priority": "High"
    },
    {
        "id": "5.2.2", "name": "Implement SDN Programable Infrastructure", "pillar": "Network & Environment", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 32.0,
        "description": "Following the API standards, requirements, and SDN API functionalities, DoD Components will implement SoftwareDefined Networking (SDN) or alternative networking approach infrastructure to enable automation tasks. Segmentation gateways and authentication decision points are integrated into the SDN or alternative networking approach infrastructure along with output logging into a standardized repository (e.g., SIEM, Log Analytics) for monitoring and alerting.",
        "outcomes": "1. Components implement application delivery control proxy.\n2. Components integrate authentication decision points.\n3. Components implement segmentation gateways.",
        "end_state": "The SDN or alternative networking approach infrastructure is fully implemented across Components, with segmentation gateways and authentication decision points integrated and operational. Comprehensive logging and monitoring are established through SIEM and log analytics, ensuring continuous oversight and rapid response capabilities. The automation of these process enhances network security, efficiency, and compliance with ZT principles.",
        "predecessors": "Define SDN APIs; Standardized API Calls & Schemas Pt1", "successors": "", "sprint": "Sprint 5", "team": "NetSec Team", "priority": "Critical"
    },
    {
        "id": "5.2.3", "name": "Segment Flows into Control, Management, and Data Planes", "pillar": "Network & Environment", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 13.0,
        "description": "Network infrastructure and flows are segmented either physically or logically into separate and distinct control, management, and data planes. Segmentation using IPv6/VLAN approaches is implemented to better organize traffic across data planes. Analytics and NetFlow from the updated infrastructure is automatically fed into Operations Centers and analytics tools.",
        "outcomes": "1. Enterprise provides guidance/policy on segmentation.\n2. IPv6/VLAN segmentation is implemented.\n3. Enable automated NetOps information reporting.\n4. Ensure configuration control across enterprise.\n5. Integrated with SIEM/SOAR.",
        "end_state": "Enterprise provides policy and/or guidance on segmentation. Components further segment network traffic limiting the scope of attack, isolating incidents, and preventing malicious attempts from lateral movement across the network.",
        "predecessors": "", "successors": "B/C/P/S Macro segmentation; Application & Device Micro segmentation", "sprint": "Sprint 5", "team": "NetSec Team", "priority": "High"
    },
    {
        "id": "5.2.4", "name": "Network Asset Discovery & Optimization", "pillar": "Network & Environment", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 30.2,
        "description": "DoD Components automate network asset discovery through the SDN infrastructure, limiting access to devices based on risk-based methodical approaches. Optimization is conducted based on the SDN analytics to improve overall performance along with providing approved access to resources.",
        "outcomes": "1. Technical Refreshment/Technology Evolution.\n2. Provide Optimization/Performance Controls.",
        "end_state": "Automated discovery and dynamic route optimization via SDN controllers.",
        "predecessors": "", "successors": "", "sprint": "Sprint 6+", "team": "NetSec Team", "priority": "Medium"
    },
    {
        "id": "5.2.5", "name": "Real-Time Access Decisions", "pillar": "Network & Environment", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 15.6,
        "description": "SDN infrastructure utilizes cross pillar data sources such as User Activity Monitoring (UAM), Entity Activity Monitoring (EAM), Enterprise security profiles, and more, for real-time access decisions. Machine Learning (ML) is used to assist decision making based on advanced network analytics (i.e., full packet capture, etc.). Policies are consistently implemented across the Enterprise using unified access standards.",
        "outcomes": "1. Analyze SIEM logs with analytics engine to provide real-time policy access decisions.\n2. Support sending captured packets, data and network flows, and other specific logs for analytics.\n3. Segment end-to-end transport network flows; audit security policies for consistency across Enterprise.\n4. Protect data-in-transit during Coalition Information Sharing.",
        "end_state": "Autonomous real-time network access decisions integrating cross-pillar risk feeds.",
        "predecessors": "Continuous Authentication Pt2; User Activity Monitoring Pt2; Implement C2C/Compliance Based Network Authorization Pt2; Entity Activity Monitoring Pt2; AI-enabled Network Access; Enterprise Security Profile Pt2", "successors": "", "sprint": "Sprint 6+", "team": "NetSec Team", "priority": "Critical"
    },
    {
        "id": "5.3.1", "name": "Datacenter Macro segmentation", "pillar": "Network & Environment", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 17.6,
        "description": "DoD Components implement service-based architectures to restrict lateral movement between public and private components of a solutions architecture. Proxy and/or enforcement checks are integrated with the SDN or alternative networking approach solution(s) based on device attributes and behavior.",
        "outcomes": "1. Establish proxy/enforcement checks of attributes (device, location, data), access and flow (client, tenant, traffic patterns), and Component principles (asset life cycle, compliance, policy).",
        "end_state": "SDN or alternative networking approach solutions incorporate proxy and enforcement checks based on device attributes and behavior, ensuring robust security. Application delivery control proxies, SIEM logging, UAM, and authentication decision points are integrated and operational. Segmentation gateways are deployed to enhance network security and efficiency.",
        "predecessors": "", "successors": "Implement Micro segmentation; Resource Authorization Pt1; SDC Resource Authorization Pt1", "sprint": "Sprint 5", "team": "NetSec Team", "priority": "High"
    },
    {
        "id": "5.3.2", "name": "B/C/P/S Macro segmentation", "pillar": "Network & Environment", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 18.1,
        "description": "DoD Components implement mission/organization-based macro-segmentation using logical network zones that limit lateral movement. Proxy and/or enforcement checks are integrated with the SDN or alternative networking approach solution(s) based on device attributes and behavior.",
        "outcomes": "1. Establish proxy/enforcement checks of attributes (device, location, data), access and flow (client, tenant, traffic patterns), and Component principles (asset life cycle, compliance, policy).\n2. Analyze activities of application specific security stacks for firewall configuration and access policies.",
        "end_state": "SDN or alternative networking approach solutions incorporate proxy and enforcement checks based on device attributes and behavior, ensuring robust security. Application delivery control proxies, SIEM logging, UAM, and authentication decision points are integrated and operational. Segmentation gateways are deployed to enhance network security and efficiency.",
        "predecessors": "Segment Flows into Control, Management, and Data Planes", "successors": "", "sprint": "Sprint 5", "team": "NetSec Team", "priority": "High"
    },
    {
        "id": "5.4.1", "name": "Implement Micro segmentation", "pillar": "Network & Environment", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 17.3,
        "description": "DoD Components implement micro-segmentation infrastructure into SDN or alternative networking approach environment, enabling basic segmentation of service components (e.g., web, app, DB), ports, and protocols. Basic automation is accepted for policy changes, including API decision making. Virtual hosting environments implement micro-segmentation at the host/container-level.",
        "outcomes": "1. Accept automated policy changes.\n2. Implement API decision points.\n3. Implement distributed NGF/micro-FW/endpoint agent in virtual hosting environment.",
        "end_state": "Automated policy changes and API decision-making processes are established, enhancing the agility and security of the infrastructure. Virtual hosting environments employ micro-segmentation at the host/container level providing robust security controls and improving overall management efficiency. the infrastructure includes integrated application delivery control proxies, SIEM logging, UAM, authentication decision points, and segmentation gateways, ensuring comprehensive security and monitoring capabilities.",
        "predecessors": "Datacenter Macro segmentation", "successors": "Application & Device Micro segmentation", "sprint": "Sprint 5", "team": "NetSec Team", "priority": "High"
    },
    {
        "id": "5.4.2", "name": "Application & Device Micro segmentation", "pillar": "Network & Environment", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 17.9,
        "description": "DoD Components utilize Software Defined Networking (SDN) or alternative networking approach solution(s) to establish infrastructure meeting the ZT Target Level functionalities - i.e., logical network zones; Role, Attribute, and Condition-Based Access Control for Users and Devices, Privileged Access Management (PAM) services for network resources, and policy-based control on API access.",
        "outcomes": "1. Assign Role, Attribute, and Condition-Based Access Control to Users & Devices.\n2. Provide PAM services.\n3. Limit Access on a Per-Identity basis for users and devices.\n4. Create logical network zones.\n5. Support policy control via REST API.",
        "end_state": "SDN or alternative networking approach infrastructure is established across DoD Components, providing robust Role, Attribute, and Condition-Based Access Control for PEs and NPEs. PAM services are in place for network resources. Logical network zones are created, and policy-based controls are enforced on API access via REST APIs. This ensures secure and controlled access management, enhancing the overall security posture.",
        "predecessors": "Segment Flows into Control, Management, and Data Planes; Implement Micro segmentation", "successors": "Enrich Attributes for Resource Authorization Pt1", "sprint": "Sprint 5", "team": "NetSec Team", "priority": "High"
    },
    {
        "id": "5.4.3", "name": "Process Micro segmentation", "pillar": "Network & Environment", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 20.3,
        "description": "DoD Components utilize existing micro-segmentation and SDN automation infrastructure enabling process micro-segmentation. Host-level processes are segmented based on security policies and access is granted using real-time access decision making.",
        "outcomes": "1. Segment host-level processes for security policies.\n2. Support real-time access decisions and policy changes.\n3. Support offload of logs for analytics and automation.\n4. Support dynamic deployment of segmentation policy.",
        "end_state": "Host-level process micro-segmentation with dynamic policy push.",
        "predecessors": "Implement Enforcement Points", "successors": "", "sprint": "Sprint 6+", "team": "NetSec Team", "priority": "Medium"
    },
    {
        "id": "5.4.4", "name": "Protect Data In Transit", "pillar": "Network & Environment", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 9.1,
        "description": "Based on the data flow mappings and monitoring standards provided by DoD Enterprise, policies are enabled by DoD Components to mandate protection of data in transit. Common use cases, such as Coalition Information Sharing, sharing across system boundaries and protection across architectural components, are included in protection policies.",
        "outcomes": "1. Enterprise guidance is provided on protecting Data In Transit.\n2. Protect data in transit during Coalition Information Sharing.\n3. Protect data in transit across system high boundaries.\n4. Integrate data in transit protection across architecture components.",
        "end_state": "Policies are effectively implemented to protect data in transit during coalition information sharing across system high boundaries, and within various architectural components. Data in transit is securely encrypted and monitored ensuring ZT.",
        "predecessors": "", "successors": "", "sprint": "Sprint 5", "team": "NetSec Team", "priority": "High"
    },

    # --- PILLAR 6: AUTOMATION & ORCHESTRATION (23 activities) ---
    {
        "id": "6.1.1", "name": "Policy Inventory & Development", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 9.8,
        "description": "The DoD Enterprise works with Components to catalog and inventory existing cybersecurity policies and standards. Policies are updated and created in cross-pillar activities as needed to meet critical ZT Target Level functionality.",
        "outcomes": "1. Component policies have been collected in reference to applicable compliance and risk (e.g., RMF, NIST).\n2. Policies have been reviewed for missing Pillars and Capabilities by Enterprise per the ZTRA.\n3. Enterprise and Components make updates to missing areas of policies to meet the capabilities per the ZTRA.",
        "end_state": "Policies are aligned to support interoperability and enable ZT functionality.",
        "predecessors": "", "successors": "Continuous Authorization to Operate (cATO) Pt1", "sprint": "Sprint 2", "team": "Security Architecture", "priority": "High"
    },
    {
        "id": "6.1.2", "name": "Organization Access Profile", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 19.4,
        "description": "DoD Components develop access profile rules for mission/task and non-mission/task DAAS access using the data from the User, Data, Network & Environment, and Device pillars. The DoD Enterprise works with the Components to develop an Enterprise security profile rules using the existing Component security profiles to create a common access approach to DAAS. A phased approach can be used by Components to limit risk to mission/task critical DAAS access once the security profile(s) are created.",
        "outcomes": "1. Component scoped profile rules are created to determine access to DAAS using capabilities from User, Data, Network & Environment, and Device pillars.\n2. Initial Enterprise profile rules for access standard is developed for access to DAAS.\n3. When possible, Component profile(s) utilize Enterprise available services in the User, Data, Network & Environment, and Device pillars.\n4. Component mission/task critical profile rules are created.",
        "end_state": "The patterns of behavior are established for what outcomes are needed for access control at the Component level.",
        "predecessors": "", "successors": "Enterprise Security Profile Pt1", "sprint": "Sprint 2", "team": "IAM Team", "priority": "High"
    },
    {
        "id": "6.1.3", "name": "Enterprise Security Profile Pt1", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 16.0,
        "description": "Enterprise security profile rules covers the User, Data, Network & Environment, and Device pillars initially. Existing Component security profile rules are integrated for non-mission/task DAAS access following an iterative approach to tuning access.",
        "outcomes": "1. Enterprise profile rules are created to access DAAS using capabilities from User, Data, Network & Environment, and Device pillars.\n2. Component profile rules are integrated with the Enterprise profile rules using a standardized approach.\n3. Service catalog and/or CMDB exists with ZT components; at a minimum PDP(s), PEP(s), and PIP(s) details inventoried.",
        "end_state": "The patterns of behavior are established for necessary outcomes of access control at the Enterprise level.",
        "predecessors": "Organization Access Profile", "successors": "Enterprise Security Profile Pt2", "sprint": "Sprint 3", "team": "Security Architecture", "priority": "High"
    },
    {
        "id": "6.1.4", "name": "Enterprise Security Profile Pt2", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 12.5,
        "description": "The minimum number of Enterprise security profile(s) exist that grant access to the widest range of DAAS within the DoD Compontents. Mission/task Component profiles are integrated with the Enterprise security profile(s) and exceptions are managed in a risk-based methodical approach.",
        "outcomes": "1. Enterprise security profile(s) have been reduced and simplified to support widest array of access to DAAS.\n2. Mission/Task Critical profile(s) have been integrated and supported Component profiles are considered the exception.",
        "end_state": "Simplified unified enterprise security profile governing global resource access.",
        "predecessors": "Enterprise Security Profile Pt1", "successors": "Real-Time Access Decisions; AI-enabled Dynamic Access Control", "sprint": "Sprint 6+", "team": "Security Architecture", "priority": "Medium"
    },
    {
        "id": "6.2.1", "name": "Task Automation Analysis", "pillar": "Automation & Orchestration", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 6.3,
        "description": "DoD Components identify and enumerate all task activities that can be executed both manually and in an automated fashion. Task activities are organized into automated and manual categories. Manual activities are analyzed for retirement.",
        "outcomes": "1. Automatable tasks are identified.\n2. Tasks are enumerated.\n3. Components create process flow of all cybersecurity defense automations tasks developed with an independent audit process before operational implementation.",
        "end_state": "Components optimize mission-critical processes with automation, reducing the time and resources spent, increasing accuracy (limiting human error) when validated, and supporting incident response.",
        "predecessors": "", "successors": "", "sprint": "Sprint 2", "team": "SecOps Team", "priority": "Medium"
    },
    {
        "id": "6.2.2", "name": "Enterprise Integration & Workflow Provisioning Pt1", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 23.4,
        "description": "The DoD Enterprise establishes baseline integration and interoperability within the Security Orchestration, Automation, and Response (SOAR) solution required to enable ZTA Target Level functionality, where actionable and relevant information resides. DoD Components identify instrument, integration, and interoperability points and prioritization per the Enterprise baseline. The necessary integrations in User, Device, Application & Workload, Network & Environment, and Device pillars to automate IR functions are completed.",
        "outcomes": "1. DoD Enterprise establishes baseline integration and interoperability with SOAR to enable ZT Target Level functionality.\n2. Components identify key integrations.\n3. Components implement Enterprise integration and interoperability for critical services.\n4. Components identify recovery and protection requirements.",
        "end_state": "Critical integrations occur to meet key services and enable recovery and protection capabilities.",
        "predecessors": "", "successors": "Enterprise Integration & Workflow Provisioning Pt2", "sprint": "Sprint 3", "team": "SecOps Team", "priority": "High"
    },
    {
        "id": "6.2.3", "name": "Enterprise Integration & Workflow Provisioning Pt2", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 12.7,
        "description": "DoD Components integrate remaining services to meet baseline requirements and ZT Advanced Level functionality requirements. Service provisioning is integrated and automated into workflows, where required, meeting ZT Target Level functionalities.",
        "outcomes": "1. Services identified.\n2. Service provisioning is implemented.",
        "end_state": "Automated workflow provisioning across all cross-pillar services.",
        "predecessors": "Enterprise Integration & Workflow Provisioning Pt1", "successors": "Automated Workflow", "sprint": "Sprint 6+", "team": "SecOps Team", "priority": "Medium"
    },
    {
        "id": "6.3.1", "name": "Implement Data Tagging & Classification ML Tools", "pillar": "Automation & Orchestration", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 16.0,
        "description": "DoD Components utilize existing Data Tagging and Classification standards and requirements to integrate Machine Learning (ML) solution(s)/capability as needed. ML solution(s) is implemented by Components, and existing tagged and classified data repositories are used to establish baselines. ML solution(s) applies data tags in a supervised approach to continually improve analysis.",
        "outcomes": "1. Components implement ML capabilities with data tagging and classification.",
        "end_state": "Machine learning solution is acquired, trained, and implemented in accordance with DoD established Data Tagging and Classification tools. Machines are trained on a high-quality subset of data developed under activity 4.3.1 with human oversight and assessment.",
        "predecessors": "Define Data Tagging Standards", "successors": "Automated Data Tagging & Support Pt2", "sprint": "Sprint 4", "team": "Data Governance", "priority": "High"
    },
    {
        "id": "6.4.1", "name": "Implement AI automation tools", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 25.7,
        "description": "DoD Components identify areas of improvement based on existing Machine Learning (ML) techniques for Artificial Intelligence (AI). AI solutions are identified, procured, and implemented using the identified areas as requirements.",
        "outcomes": "1. Develop AI tool requirements.\n2. Procure and implement AI tools.",
        "end_state": "AI automation tooling procured and integrated into SecOps workflows.",
        "predecessors": "", "successors": "Automated Workflow", "sprint": "Sprint 6+", "team": "SecOps Team", "priority": "Medium"
    },
    {
        "id": "6.4.2", "name": "AI Driven by Analytics decides A&O modifications", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 42.0,
        "description": "DoD Components, utilizing existing Machine Learning (ML) functions, implement and use AI technology, such as neural networks, to drive automation and orchestration decisions. Decision making is moved to AI as much as possible, freeing up human staff for other efforts. Utilizing historical patterns, AI will make anticipatory changes in the environment to better reduce risk.",
        "outcomes": "1. AI is able to make changes to automated workflow activities.",
        "end_state": "Autonomous AI decision engine driving dynamic access and configuration adjustments.",
        "predecessors": "", "successors": "", "sprint": "Sprint 6+", "team": "SecOps Team", "priority": "Medium"
    },
    {
        "id": "6.5.1", "name": "Response Automation Analysis", "pillar": "Automation & Orchestration", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 9.0,
        "description": "DoD Components identify and enumerate all response activities that are executed both manually and in an automated fashion. Response activities are organized into automated and manual categories.",
        "outcomes": "1. Automatable response activities are identified.\n2. Response activities are enumerated.",
        "end_state": "Components optimize response processes with automation, improving the response time for true positives and supporting a better awareness and understanding of security incidents.",
        "predecessors": "", "successors": "", "sprint": "Sprint 3", "team": "Incident Response", "priority": "High"
    },
    {
        "id": "6.5.2", "name": "Implement SOAR Tools", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 14.9,
        "description": "DoD Enterprise, working with Components, develops a standard set of requirements for Security Orchestration, Automation, and Response (SOAR) tooling to enable ZT Target Level functionality. DoD Components use approved requirements to procure and implement a SOAR solutions. Infrastructure integrations for future SOAR functionality is completed.",
        "outcomes": "1. Enterprise develops requirements for SOAR tools.\n2. Components procure SOAR tools.\n3. Components develop Implementation Plan (e.g., Integration Points, Incident Response, Architecture, Interoperability, Scalability, etc.) for SOAR.\n4. Complete full implementation of SOAR.",
        "end_state": "Components conduct appropriate planning to ensure effective implementation of a SOAR tool with relevant connections and interoperability.",
        "predecessors": "Standardized API Calls & Schemas Pt1; Workflow Enrichment Pt1", "successors": "", "sprint": "Sprint 3", "team": "Incident Response", "priority": "Critical"
    },
    {
        "id": "6.5.3", "name": "Implement Playbooks", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 14.0,
        "description": "DoD Components review all existing playbooks to identify for future automation. Existing manual and automated processes missing playbooks have playbooks developed. Playbooks are prioritized for automation to be integrated with the 'Automated Workflows' activities covering critical processes. Manual processes without playbooks are authorized using a risk-based methodical approach.",
        "outcomes": "1. Automate playbooks based on automated workflows capability.\n2. Manual Playbooks are developed and implemented.",
        "end_state": "Automated incident response playbooks executed in production.",
        "predecessors": "", "successors": "", "sprint": "Sprint 6+", "team": "Incident Response", "priority": "Medium"
    },
    {
        "id": "6.6.1", "name": "Tool Compliance Analysis", "pillar": "Automation & Orchestration", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 7.3,
        "description": "Automation and Orchestration tooling and solutions are analyzed for compliance and capabilities based on the DoD Enterprise API machine-readable patterns and protocols.",
        "outcomes": "1. Components API status is determined to be compliant or non-compliant to Enterprise API standards.",
        "end_state": "Ensure tools includes standardized API security with the proper protocols and capabilities to monitor, control access, and interoperate with other pillars.",
        "predecessors": "", "successors": "", "sprint": "Sprint 2", "team": "Engineering", "priority": "Medium"
    },
    {
        "id": "6.6.2", "name": "Standardized API Calls & Schemas Pt1", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 13.6,
        "description": "The DoD Enterprise works with components to establish an API standard (or equivalent automated interchange mechanism), which at least outlines the approved patterns and protocols. DoD Components identify existing APIs and update to the standard.",
        "outcomes": "1. API Standard (or equivalent automated interchange mechanism) is established with Component commitment.\n2. Automated pattern and protocol services are implemented.",
        "end_state": "Existing APIs are assessed against automated pattern and protocol services.",
        "predecessors": "", "successors": "Implement SDN Programable Infrastructure; Implement SOAR Tools; Standardized API Calls & Schemas Pt2", "sprint": "Sprint 3", "team": "Engineering", "priority": "High"
    },
    {
        "id": "6.6.3", "name": "Standardized API Calls & Schemas Pt2", "pillar": "Automation & Orchestration", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 14.2,
        "description": "DoD Components will ensure that all ZT applications/services (i.e., PEP, PDP, PIP) adopt the API standard. Information Systems required to follow ZT Target or Advanced Levels prioritize integration with the API standard to simplify automation.",
        "outcomes": "1. Components implement API Standard for all ZT Applications/Services (i.e., PEP, PDP, PIP).",
        "end_state": "For each ZT service edge, Components will have an automated pattern and protocol service.",
        "predecessors": "Standardized API Calls & Schemas Pt1", "successors": "", "sprint": "Sprint 3", "team": "Engineering", "priority": "High"
    },
    {
        "id": "6.7.1", "name": "Workflow Enrichment Pt1", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 7.3,
        "description": "DoD Enterprise works with Components to establish cybersecurity incident response guidance using industry best practices, such as NIST and a list of approved threat data sources as specified in 'Cyber Threat Intelligence Program Pt 1'. DoD Components enable workflows for security events using internal context, past threat events, and other threat intelligence. Approved external sources of enrichment are identified for future integration. These workflows are used to determine incident response procedures.",
        "outcomes": "1. Threat events are identified utilizing DoD Enterprise guidance and best practice.\n2. Components establish workflows for threat events and include enrichment from approved sources and business/mission context.",
        "end_state": "Component workflows provide security teams with the intelligence needed to better detect, investigate, and respond to incidents more effectively.",
        "predecessors": "", "successors": "Implement SOAR Tools; Workflow Enrichment Pt2", "sprint": "Sprint 3", "team": "Threat Intel Team", "priority": "High"
    },
    {
        "id": "6.7.2", "name": "Workflow Enrichment Pt2", "pillar": "Automation & Orchestration", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 9.1,
        "description": "DoD Components identify and establish extended workflows for additional incident response types in alignment with the activity 'Threat Alerting Pt 2'. Initial enrichment data sources are used for existing workflows. Additional enrichment sources (e.g., UAM, UEBA, profiles, and baselines) are identified for future integrations.",
        "outcomes": "1. Workflows for advanced threat events are developed by Components.\n2. Advanced threat events are identified.",
        "end_state": "Component workflows provide security teams with the intelligence needed to better detect, investigate, and respond to incidents more effectively.",
        "predecessors": "Workflow Enrichment Pt1", "successors": "Workflow Enrichment Pt3", "sprint": "Sprint 4", "team": "Threat Intel Team", "priority": "High"
    },
    {
        "id": "6.7.3", "name": "Workflow Enrichment Pt3", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 12.4,
        "description": "DoD Components use enrichment data sources on basic and extended threat response workflows.",
        "outcomes": "1. Enrichment data has been identified.\n2. Enrichment data is integrated into workflows.",
        "end_state": "Cross-pillar behavioral threat intelligence enrichments stream into response pipelines.",
        "predecessors": "Workflow Enrichment Pt2", "successors": "Automated Workflow", "sprint": "Sprint 6+", "team": "Threat Intel Team", "priority": "Medium"
    },
    {
        "id": "6.7.4", "name": "Automated Workflow", "pillar": "Automation & Orchestration", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 14.4,
        "description": "DoD Components focus on automating Security Orchestration, Automation, and Response (SOAR) functions and playbooks. Manual processes within security operations are identified and fully automated as possible. Remaining manual processes are decommissioned when possible or marked for exception using a risk-based approach.",
        "outcomes": "1. Workflow processes are fully automated.\n2. Manual processes have been identified.\n3. Remaining processes are marked as exceptions and documented.",
        "end_state": "100% automated SOAR triage and mitigation workflows for known incident classes.",
        "predecessors": "Workflow Enrichment Pt3; Implement AI automation tools; Enterprise Integration & Workflow Provisioning Pt2", "successors": "Continuous Authorization to Operate (cATO) Pt2", "sprint": "Sprint 6+", "team": "SecOps Team", "priority": "Critical"
    },

    # --- PILLAR 7: VISIBILITY & ANALYTICS (28 activities) ---
    {
        "id": "7.1.1", "name": "Scale Considerations", "pillar": "Visibility & Analytics", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 11.6,
        "description": "DoD Components conduct analysis to determine current and future scaling needs for monitoring, detection, and response. This requires a prioritization plan aligned with Component business/mission considerations and associated risk alignment. Scaling is analyzed following common industry best practice and aligns with ZT Pillar requirements. The team works with existing Business Continuity Planning (BCP) and Disaster Recovery Planning (DRP) groups to determine distributed environment needs in emergencies and Component growth.",
        "outcomes": "1. Evaluate opportunities for scaling (e.g., infrastructure sizing, bandwidth capacity, distributed environments) across the different pillars as it applies to visibility and analytics outcomes.\n2. Create or utilize existing governance structure to operationalize the strategy.",
        "end_state": "Analyze scaling needs for monitoring, detection, and response, aligning with business considerations, risk, industry best practices, and ZT Pillar requirements, while collaborating with BCP and DRP groups for distributed environment needs during emergencies and growth.",
        "predecessors": "", "successors": "", "sprint": "Sprint 1", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "7.1.2", "name": "Log Parsing", "pillar": "Visibility & Analytics", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 6.3,
        "description": "DoD Components identify and prioritize log and flow sources (e.g., firewalls, Endpoint Detection & Response, Active Directory, switches, routers, etc.) and develop a plan for collection of high-priority logs first, then low-priority. An open industry-standard log format is agreed upon at the DoD Enterprise level with the Components, and implemented in future procurement requirements. Existing solutions and technologies are migrated to this format on a continual basis.",
        "outcomes": "1. Enterprise standardized log formats.\n2. Components implement rules developed for each log format.",
        "end_state": "Components filter and forward all applicable log events to the SIEM.",
        "predecessors": "", "successors": "Implement Analytics Tools; Asset ID & Alert Correlation", "sprint": "Sprint 1", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "7.1.3", "name": "Log Analysis", "pillar": "Visibility & Analytics", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 10.3,
        "description": "Enterprise develops common user and device activities. Components identify and prioritize activities based on risk. Events/flows deemed the most simplistic and risky have analytics created using different data sources, such as logs. Trends and patterns are developed over longer periods of time.",
        "outcomes": "1. Identify activities to analyze.\n2. Determine risk level per events/flows.",
        "end_state": "Components utilize logs to develop risk level for each user and device.",
        "predecessors": "", "successors": "Establish User Baseline Behavior; User/Device Baselines", "sprint": "Sprint 1", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "7.2.1", "name": "Threat Alerting Pt1", "pillar": "Visibility & Analytics", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 7.5,
        "description": "DoD Components utilize existing Security Information and Event Management (SIEM) solution to develop rules and alerts for common threat events (e.g., malware, phishing, etc.) Alerts and/or rule triggers are fed into the parallel 'Asset ID & Alert Correlation' activity to begin automation of responses.",
        "outcomes": "1. Rules developed for Component-derived threat correlation.\n2. Rules developed for asset ID-based responses.",
        "end_state": "Components augment SIEM with threat data developed from incident response analysis.",
        "predecessors": "", "successors": "Threat Alerting Pt2; Implement Extended Detection & Response (XDR) Tools and Integrate with C2C Pt1", "sprint": "Sprint 2", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "7.2.2", "name": "Threat Alerting Pt2", "pillar": "Visibility & Analytics", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 16.5,
        "description": "DoD Components expand threat alerting in the Security Information and Event Management (SIEM) solution to include Cyber Threat Intelligence (CTI) data feeds. Deviation and anomaly rules are developed in the SIEM to detect advanced threats.",
        "outcomes": "1. Rules developed for advanced threat correlation (e.g., behavioral, baseline deviation).",
        "end_state": "Components augment SIEM with threat data from CTI feeds.",
        "predecessors": "Threat Alerting Pt1; Cyber Threat Intelligence Program Pt1", "successors": "Threat Alerting Pt3", "sprint": "Sprint 3", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "7.2.3", "name": "Threat Alerting Pt3", "pillar": "Visibility & Analytics", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 12.9,
        "description": "Threat alerting is expanded to include advanced data sources, such as Extended Detection & Response (XDR), User & Entity Behavior Analytics (UEBA), and User Activity Monitoring (UAM). These advanced data sources are used to develop improved anomalous and pattern activity detections.",
        "outcomes": "1. Identify triggering anomalous events.\n2. Implement triggering policy.",
        "end_state": "Cross-domain alerting powered by XDR, UEBA, and UAM telemetry streams.",
        "predecessors": "Threat Alerting Pt2; Implement Extended Detection & Response (XDR) Tools and Integrate with C2C Pt2", "successors": "Continuous Authorization to Operate (cATO) Pt2", "sprint": "Sprint 6+", "team": "SOC Team", "priority": "Medium"
    },
    {
        "id": "7.2.4", "name": "Asset ID & Alert Correlation", "pillar": "Visibility & Analytics", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 10.2,
        "description": "All assets in SIEM are identified and correlated to alerts in order to provide security teams with accurate and detailed information. This information contributes to the incident response speed. Asset ID's also allow better visibility while preforming vulnerability assessments.",
        "outcomes": "1. Identify and provide as much detail as needed for identification of all assets in SIEM, including correlation to alerts in support of 'Threat Alerting Pt1'.",
        "end_state": "Security is able to quickly identify assets in relation to threat events in a way that betters supports incident response.",
        "predecessors": "Log Parsing", "successors": "", "sprint": "Sprint 2", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "7.2.5", "name": "User/Device Baselines", "pillar": "Visibility & Analytics", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 13.0,
        "description": "DoD Components develop a subject/attribute baseline approach based on typical pattern and behavior in activity 'Establish User Baseline Behavior'. This approach will serve as a benchmark for security when identifying and responding to abnormal or malicious activity.",
        "outcomes": "1. Components identify a subject/attribute baseline approach.",
        "end_state": "Components can utilize baseline approach to build profiles in activity 'Baseline and Profiling Pt 1'.",
        "predecessors": "Implement User & Entity Behavior Activity (UEBA) and User Activity Monitoring (UAM) Tooling; Log Analysis; Establish User Baseline Behavior Pattern", "successors": "User Activity Monitoring Pt1; Entity Activity Monitoring Pt1", "sprint": "Sprint 2", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "7.3.1", "name": "Implement Analytics Tools", "pillar": "Visibility & Analytics", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 12.1,
        "description": "The DOD Enterprise provides minimum requirements for analytics tool capabilities to analyze data across all ZT pillars. Components procure and implement an analytics tool in order to provide actionable insights and intelligence.",
        "outcomes": "1. Enterprise develops requirements for analytic environment.\n2. Components procure and implement analytic tools.",
        "end_state": "Analytics tools provide intelligence and guidance to security teams in order to make improvements on threat monitoring and response.",
        "predecessors": "Log Parsing", "successors": "", "sprint": "Sprint 2", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "7.3.2", "name": "Establish User Baseline Behavior", "pillar": "Visibility & Analytics", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 13.8,
        "description": "Utilizing the analytics tools implemented, subject behavior patterns are analyzed to identify patterns and deviations from normality. Techniques in analytics involve machine learning and UEBA.",
        "outcomes": "1. Establish subject behavior patterns in order to differentiate normality/abnormality.\n2. Identify opportunities for ML usage in analytics.",
        "end_state": "Patterns established will provide Components with decision making for user/device baselines.",
        "predecessors": "Implement User & Entity Behavior Activity (UEBA) and User Activity Monitoring (UAM) Tooling; Log Analysis", "successors": "User/Device Baselines; Baseline & Risk Profiling Pt1", "sprint": "Sprint 2", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "7.4.1", "name": "Baseline & Profiling Pt1", "pillar": "Visibility & Analytics", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 12.3,
        "description": "Utilizing the baselines developed in the 'User/Device Baselines' activity, threat profiles are created to assess the level of risk for individual subjects associated to the overall Component security. Profiles should be integrated into the 'Organization Access Profile' activity for decision making.",
        "outcomes": "1. Identify subject/attribute threat profiles.\n2. Develop analytics to detect changing threat conditions.",
        "end_state": "Components are able create risk profiles to mitigate compromised accounts, suspicious activity, and insider threats.",
        "predecessors": "Implement User & Entity Behavior Activity (UEBA) and User Activity Monitoring (UAM) Tooling; Log Analysis; Establish User Behavior Pattern", "successors": "Baseline & Profiling Pt2", "sprint": "Sprint 2", "team": "SOC Team", "priority": "High"
    },
    {
        "id": "7.4.2", "name": "Baseline & Profiling Pt2", "pillar": "Visibility & Analytics", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 22.7,
        "description": "DoD Components expand baselines and profiles to include unmanaged and non-standard device types, including Internet of Things (IoT) and Operational Technology (OT), through data output monitoring. These devices are again profiled based on standardized attributes and use cases. Analytics are updated to consider the new baselines and profiles, accordingly enabling further detections and response. Specific risky users and devices are automatically prioritized for increased monitoring based on risk. Detection and response are integrated with cross pillar functionalities.",
        "outcomes": "1. Add threat profiles for IoT and OT devices.\n2. Develop and extend analytics.\n3. Extend threat profiles to individual users and devices.",
        "end_state": "IoT and OT device baselines integrated into real-time threat scoring.",
        "predecessors": "Baseline & Profiling Pt1", "successors": "", "sprint": "Sprint 6+", "team": "SOC Team", "priority": "Medium"
    },
    {
        "id": "7.4.3", "name": "UEBA Baseline Support Pt 1", "pillar": "Visibility & Analytics", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 6.3,
        "description": "User & Entity Behavior Analytics (UEBA) within DoD Components expands monitoring to advanced analytics such as Machine Learning (ML). These results are in turn reviewed and provided back into ML algorithms to improve detection and response.",
        "outcomes": "1. Implement ML-based analytics to detect anomalies.",
        "end_state": "Supervised ML algorithms refine behavioral detection baselines.",
        "predecessors": "Baseline & Profiling Pt1", "successors": "AI-enabled Network Access; UEBA Baseline Support Pt2", "sprint": "Sprint 6+", "team": "SOC Team", "priority": "Medium"
    },
    {
        "id": "7.4.4", "name": "UEBA Baseline Support Pt 2", "pillar": "Visibility & Analytics", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 6.3,
        "description": "User & Entity Behavior Analytics (UEBA) within DoD Components completes it expansion by using traditional and Machine Learning (ML) based results to be provided to Artificial Intelligence (AI) algorithms. AI based detections are supervised, but ultimately, using advanced techniques such as neural networks, UEBA operators are not part of the learning process.",
        "outcomes": "1. Implement ML-based analytics to detect anomalies.",
        "end_state": "Autonomous neural network anomaly detection operating without manual intervention.",
        "predecessors": "UEBA Baseline Support Pt1", "successors": "", "sprint": "Sprint 6+", "team": "SOC Team", "priority": "Medium"
    },
    {
        "id": "7.5.1", "name": "Cyber Threat Intelligence Program Pt1", "pillar": "Visibility & Analytics", "responsibility": "Enterprise and Component",
        "type": "Target Level ZT", "duration": 9.9,
        "description": "The DoD Enterprise works with Components to develop a Cyber Threat Intelligence (CTI) program policy, standard, and process. Components utilize this documentation to develop organizational CTI teams with key mission/task stakeholders. CTI teams gather intelligence from common data feeds across ZT Pillars and aggregate all intelligence to a centralized repository (e.g. SIEM).",
        "outcomes": "1. DoD Enterprise develops a Cyber Threat Intelligence (CTI) program policy.\n2. Component CTI team is in place with critical stakeholders.\n3. Common CTI feeds are being utilized by SIEM for monitoring.\n4. Integration points exist with device and network PEP/PDP (e.g., NGAV, NGFW, NG-IPS) are built at appropriate integration points across each pillar.",
        "end_state": "Component CTI teams are established in accordance with Enterprise policy and have integrated CTI data feeds in their SEIM(s).",
        "predecessors": "", "successors": "Cyber Threat Intelligence Program Pt2; Threat Alerting Pt 2", "sprint": "Sprint 2", "team": "Threat Intel Team", "priority": "High"
    },
    {
        "id": "7.5.2", "name": "Cyber Threat Intelligence Program Pt2", "pillar": "Visibility & Analytics", "responsibility": "Component",
        "type": "Target Level ZT", "duration": 19.5,
        "description": "DoD Components expand their Cyber Threat Intelligence (CTI) teams to include new stakeholders as appropriate. Existing and authenticated, private and controlled threat intelligence is analyzed, and appropriate actions and controls are enforced across ZT Pillars. CTI Program adapts strategy over time with expansion of threat intelligence developed in solutions and program maturity.",
        "outcomes": "1. Component Cyber Threat Intelligence team is in place with extended stakeholders as appropriate.\n2. Integration is in place for extended enforcement points across ZT Pillars (e.g., UEBA,UAM).",
        "end_state": "Component CTI teams utilize threat intelligence data to support control enforcement to a greater extent throughout the organization via tooling.",
        "predecessors": "Cyber Threat Intelligence Program Pt1", "successors": "", "sprint": "Sprint 3", "team": "Threat Intel Team", "priority": "High"
    },
    {
        "id": "7.6.1", "name": "AI-enabled Network Access", "pillar": "Visibility & Analytics", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 27.8,
        "description": "DoD Components utilize SDN infrastructure and Enterprise security profiles to enable Artificial Intelligence (AI)/Machine Learning (ML) driven network access. Analytics from previous activities are used to teach the AI/ML algorithms; improving decision making.",
        "outcomes": "1. Network access is AI driven based on environment analytics.",
        "end_state": "AI/ML dynamic network access policies continuously calibrated by environment telemetry.",
        "predecessors": "UEBA Baseline Support Pt1; Periodic Authentication; Rule Based Dynamic Access Pt1", "successors": "Real-Time Access Decisions; AI-enabled Dynamic Access Control", "sprint": "Sprint 6+", "team": "SOC Team", "priority": "Critical"
    },
    {
        "id": "7.6.2", "name": "AI-enabled Dynamic Access Control", "pillar": "Visibility & Analytics", "responsibility": "Enterprise and Component",
        "type": "Advanced Level ZT", "duration": 24.4,
        "description": "DoD Components utilize previous rule-based dynamic access to teach Artificial Intelligence (AI)/Machine Learning (ML) algorithms to make access decisions to resources. The 'AI-enabled Network Access' activity algorithms are updated to enable broader decision making to all DAAS.",
        "outcomes": "1. JIT/JEA are integrated with AI; Access is AI driven based on environment analytics.",
        "end_state": "Autonomous AI-orchestrated JIT/JEA dynamic access for all enterprise DAAS.",
        "predecessors": "Continuous Authentication Pt2; AI-enabled Network Access", "successors": "", "sprint": "Sprint 6+", "team": "SOC Team", "priority": "Critical"
    }
]

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lookups_dir = os.path.join(base_dir, "lookups")
    os.makedirs(lookups_dir, exist_ok=True)

    roadmap_activities = [d for d in DATA if not d['id'].startswith('0.')]
    sprint_0_enablers = [d for d in DATA if d['id'].startswith('0.')]
    assert len(roadmap_activities) == 152, f"Expected 152 roadmap activities, got {len(roadmap_activities)}"
    assert len(sprint_0_enablers) == 8, f"Expected 8 Sprint 0 enablers, got {len(sprint_0_enablers)}"

    # 1. Generate lookups/zt_agile_stories.csv
    stories_path = os.path.join(lookups_dir, "zt_agile_stories.csv")
    with open(stories_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "story_id", "ref", "parent_wbs_code", "title", "description", "outcomes", "end_state",
            "pillar", "activity_type", "implementation_scope", "sprint", "status", "story_points", "assignee", "assigned_team",
            "priority_class", "predecessors", "successors", "acceptance_criteria", "predictive_risk_level",
            "blockers", "nist_plane", "nist_p_components", "dfd_tier", "is_deleted", "updated_by", "updated_at",
            "isso_signed_off", "isso_signoff_by", "isso_signoff_date"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()

        for item in DATA:
            ref = item["id"]
            wbs = f"WBS-{ref}"
            story_id = f"ZTA-{ref}"
            pillar = item["pillar"]
            
            # Initial status distribution based on sprint sequence
            sprint = item.get("sprint", "Sprint 1")
            status = "Backlog"
            completion = 0
            if sprint == "Sprint 0":
                status = "Done" if ref in ["0.1.1", "0.2.1", "0.3.1"] else "In Progress"
            elif sprint == "Sprint 1":
                status = "Done" if ref in ["1.1.1", "2.1.1", "3.1.1", "7.1.1", "7.1.2"] else "In Progress"
            elif sprint == "Sprint 2":
                status = "In Progress" if ref in ["1.7.1", "2.4.1", "1.8.1", "6.1.1"] else "To Do"
            elif sprint == "Sprint 3":
                status = "To Do"
            else:
                status = "Backlog"

            # NIST 800-207 Three-Plane and P* Component Heuristic Mapping
            if pillar in ["User", "Device"]:
                nist_plane = "Identity Plane"
                nist_p = "PIP;PEP"
                dfd_tier = "Web Tier"
            elif pillar in ["Automation & Orchestration", "Visibility & Analytics"]:
                nist_plane = "Control / Policy Plane"
                nist_p = "PDP;PE;PA;PAP"
                dfd_tier = "Management / Control Tier"
            elif pillar == "Data":
                nist_plane = "Infrastructure / Data Plane"
                nist_p = "PEP;Data Store"
                dfd_tier = "Data Store"
            elif pillar == "Network & Environment":
                nist_plane = "Infrastructure / Data Plane"
                nist_p = "PEP;PDP"
                dfd_tier = "Enclave Ingress"
            else: # Applications & Workloads
                nist_plane = "Infrastructure / Data Plane"
                nist_p = "PEP;PIP"
                dfd_tier = "Mid-Tier Application"

            # Points heuristic based on duration
            dur = float(item.get("duration", 10.0))
            if dur <= 8.0:
                pts = 3
            elif dur <= 14.0:
                pts = 5
            elif dur <= 20.0:
                pts = 8
            elif dur <= 28.0:
                pts = 13
            else:
                pts = 21

            assignee_map = {
                "IAM Team": "Alice Chen (IAM Lead)",
                "Endpoint Sec": "Bob Taylor (Endpoint Lead)",
                "DevSecOps": "Carol Davis (DevSecOps Lead)",
                "Data Governance": "David Kim (Data Architect)",
                "NetSec Team": "Frank Miller (NetSec Lead)",
                "Security Architecture": "Grace Hopper (SecArch)",
                "SecOps Team": "Hank Rearden (SecOps)",
                "Incident Response": "Irene Adler (IR Lead)",
                "Threat Intel Team": "Jack Ryan (CTI Lead)",
                "SOC Team": "Karen Page (SOC Manager)"
            }
            assignee = assignee_map.get(item["team"], "Unassigned")

            writer.writerow({
                "story_id": story_id,
                "ref": ref,
                "parent_wbs_code": wbs,
                "title": item["name"],
                "description": item["description"],
                "outcomes": item["outcomes"],
                "end_state": item["end_state"],
                "pillar": item["pillar"],
                "activity_type": item["type"],
                "implementation_scope": item["responsibility"],
                "sprint": sprint,
                "status": status,
                "story_points": pts,
                "assignee": assignee,
                "assigned_team": item["team"],
                "priority_class": item["priority"],
                "predecessors": item["predecessors"],
                "successors": item["successors"],
                "acceptance_criteria": item["end_state"],
                "predictive_risk_level": "High" if item["priority"] == "Critical" else ("Medium" if item["priority"] == "High" else "Low"),
                "blockers": "None",
                "nist_plane": nist_plane,
                "nist_p_components": nist_p,
                "dfd_tier": dfd_tier,
                "is_deleted": "false",
                "updated_by": "system_init",
                "updated_at": 1770984000,
                "isso_signed_off": "true" if status == "Done" else "false",
                "isso_signoff_by": "ISSO Major Vance" if status == "Done" else "",
                "isso_signoff_date": "2026-02-01" if status == "Done" else ""
            })

    # 2. Generate lookups/zt_baseline_requirements.csv
    baseline_path = os.path.join(lookups_dir, "zt_baseline_requirements.csv")
    with open(baseline_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "ref", "capability", "requirement", "pillar", "phase", "status", "tool",
            "activity_type", "implementation_scope", "assigned_team", "wbs_code",
            "milestone_id", "disruption_score", "completion_pct", "remediation_notes",
            "blockers", "nist_plane", "nist_p_components", "dfd_tier", "is_deleted"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()

        for item in DATA:
            ref = item["id"]
            pillar = item["pillar"]
            m_id = f"M-{ref.replace('.', '')}"
            sprint = item.get("sprint", "Sprint 1")
            
            if sprint == "Sprint 0":
                status = "Compliant" if ref in ["0.1.1", "0.2.1", "0.3.1"] else "Working"
                completion = 100 if status == "Compliant" else 50
            elif sprint == "Sprint 1":
                status = "Compliant" if ref in ["1.1.1", "2.1.1", "3.1.1", "7.1.1", "7.1.2"] else "Working"
                completion = 100 if status == "Compliant" else 50
            elif sprint == "Sprint 2":
                status = "Working" if ref in ["1.7.1", "2.4.1", "1.8.1", "6.1.1"] else "Pending"
                completion = 40 if status == "Working" else 10
            else:
                status = "Pending"
                completion = 0

            # NIST 800-207 mapping
            if pillar in ["User", "Device"]:
                nist_plane = "Identity Plane"
                nist_p = "PIP;PEP"
                dfd_tier = "Web Tier"
            elif pillar in ["Automation & Orchestration", "Visibility & Analytics"]:
                nist_plane = "Control / Policy Plane"
                nist_p = "PDP;PE;PA;PAP"
                dfd_tier = "Management / Control Tier"
            elif pillar == "Data":
                nist_plane = "Infrastructure / Data Plane"
                nist_p = "PEP;Data Store"
                dfd_tier = "Data Store"
            elif pillar == "Network & Environment":
                nist_plane = "Infrastructure / Data Plane"
                nist_p = "PEP;PDP"
                dfd_tier = "Enclave Ingress"
            else:
                nist_plane = "Infrastructure / Data Plane"
                nist_p = "PEP;PIP"
                dfd_tier = "Mid-Tier Application"

            writer.writerow({
                "ref": ref,
                "capability": item["name"],
                "requirement": item["description"][:120] + "...",
                "pillar": item["pillar"],
                "phase": "Phase 1" if "Target" in item["type"] else "Phase 2",
                "status": status,
                "tool": f"{item['pillar']} Security Stack",
                "activity_type": "Target" if "Target" in item["type"] else "Advanced",
                "implementation_scope": item["responsibility"],
                "assigned_team": item["team"],
                "wbs_code": f"WBS-{ref}",
                "milestone_id": m_id,
                "disruption_score": 4 if item["priority"] in ["Critical", "High"] else 2,
                "completion_pct": completion,
                "remediation_notes": item["end_state"][:100] + "...",
                "blockers": "None",
                "nist_plane": nist_plane,
                "nist_p_components": nist_p,
                "dfd_tier": dfd_tier,
                "is_deleted": "false"
            })

    # 3. Generate lookups/zt_milestones_ims.csv
    ims_path = os.path.join(lookups_dir, "zt_milestones_ims.csv")
    with open(ims_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "milestone_id", "wbs_code", "title", "phase", "predecessor_ids",
            "planned_start_date", "planned_end_date", "actual_start_date", "actual_end_date",
            "duration_days", "completion_pct", "status", "deliverable_summary", "is_deleted"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()

        for item in DATA:
            ref = item["id"]
            m_id = f"M-{ref.replace('.', '')}"
            sprint = item.get("sprint", "Sprint 1")
            dur_days = int(float(item.get("duration", 10.0)) * 7) # convert weeks to days
            
            if sprint == "Sprint 0":
                status = "Completed" if ref in ["0.1.1", "0.2.1", "0.3.1"] else "In Progress"
                completion = 100 if status == "Completed" else 50
            elif sprint == "Sprint 1":
                status = "Completed" if ref in ["1.1.1", "2.1.1", "3.1.1", "7.1.1", "7.1.2"] else "In Progress"
                completion = 100 if status == "Completed" else 50
            elif sprint == "Sprint 2":
                status = "In Progress" if ref in ["1.7.1", "2.4.1", "1.8.1", "6.1.1"] else "Pending"
                completion = 40 if status == "In Progress" else 10
            else:
                status = "Pending"
                completion = 0

            writer.writerow({
                "milestone_id": m_id,
                "wbs_code": f"WBS-{ref}",
                "title": item["name"],
                "phase": "Phase 1" if "Target" in item["type"] else "Phase 2",
                "predecessor_ids": item["predecessors"],
                "planned_start_date": "2026-01-05",
                "planned_end_date": "2027-09-30",
                "actual_start_date": "2026-01-05" if status in ["Completed", "In Progress"] else "",
                "actual_end_date": "2026-01-20" if status == "Completed" else "",
                "duration_days": dur_days,
                "completion_pct": completion,
                "status": status,
                "deliverable_summary": item["end_state"][:100] + "...",
                "is_deleted": "false"
            })

    print(f"Successfully generated all 3 lookups with {len(DATA)} activities (152 Roadmap Activities + 8 Sprint 0 Enablers)!")

if __name__ == "__main__":
    main()
