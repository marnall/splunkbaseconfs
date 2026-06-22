# MITRE ATLAS AI Threat Detection for Splunk

**10 detection rules for AI/LLM threats mapped to the MITRE ATLAS framework. Free. Apache 2.0 License.**

[![Splunkbase](https://img.shields.io/badge/Splunkbase-Available-green)](https://splunkbase.splunk.com)
[![MITRE ATLAS](https://img.shields.io/badge/MITRE%20ATLAS-v2.1%20%7C%20Oct%202025-blue)](https://atlas.mitre.org)
[![Splunk Version](https://img.shields.io/badge/Splunk-8.x%20%2F%209.x%20%2F%2010.x-black)](https://splunk.com)

---

## What This Is

MITRE ATLAS is the adversarial threat matrix for AI/ML systems — the AI equivalent of MITRE ATT&CK. As organizations deploy LLMs, RAG pipelines, and ML APIs into production, they create an attack surface that most Splunk deployments have zero detection coverage for.

This app gives you a starting point. Ten detection rules. Real SPL. Mapped to specific ATLAS technique IDs.

---

## Detection Coverage

| Rule | ATLAS Technique | Tactic | Severity | Data Tier |
|------|----------------|--------|----------|-----------|
| Direct Prompt Injection Detected | AML.T0051.000 | Execution | High | Tier 2 |
| Indirect Prompt Injection via Retrieved Content | AML.T0051.001 | Execution | High | Tier 2 |
| LLM Jailbreak Attempt Detected | AML.T0054 | Defense Evasion | High | Tier 2 |
| Exfiltration via ML Inference API (High Volume) | AML.T0024 | Exfiltration | Critical | Tier 1 |
| Training Data Poisoning via Pipeline Upload | AML.T0020 | Impact | Critical | Tier 1 |
| AI-Enabled Abuse: Bulk Content Generation | AML.T0047 | Impact | Medium | Tier 1 |
| External Harms via AI Output: Safety Flag | AML.T0048 | Impact | Medium | Tier 1 |
| Valid Account Abuse on AI Platform | AML.T0012 | Initial Access | High | Tier 1 |
| AI Model Reconnaissance: Systematic Probing | AML.T0014 | Reconnaissance | Medium | Tier 2 |
| AI Artifact Discovery: Exposed ML Assets | AML.T0007 | Reconnaissance | Medium | Tier 1 |

**Tier 1 — Operational:** Works with standard telemetry (token counts, API call volumes, storage access logs). Available from most LLM platforms with default logging.

**Tier 2 — Content Inspection:** Requires actual prompt/response text in the log events. Requires explicit opt-in on all major platforms (see Configuration Guide in the app).

---

## Requirements

- Splunk Enterprise 8.x / 9.x / 10.x or Splunk Cloud
- AI/LLM telemetry flowing into a Splunk index (see supported platforms below)
- `lookup`, `savedsearches`, and `macros` write permissions for the installing user

### Supported Platforms

The in-app Configuration Guide provides platform-specific setup instructions for:

- LiteLLM (open-source LLM gateway)
- Azure OpenAI (via Diagnostic Settings and APIM)
- AWS Bedrock (via CloudWatch and model invocation logging)
- OpenAI direct API (via application-level logging or OpenTelemetry)
- GCP Vertex AI (via Cloud Audit Logs)
- Kong AI Gateway
- Portkey
- Helicone
- Cloudflare AI Gateway
- Anthropic (Claude API) direct
- Self-hosted models (Ollama, vLLM, TGI, llama.cpp)
- Custom API gateways / reverse proxies

---


> **Note:** If you also use the Supply Chain & AI Threat Intelligence Platform (SCIP), the field alias TA is included there — no separate configuration needed.

## Installation

Install from [Splunkbase](https://splunkbase.splunk.com) via Apps → Manage Apps → Install from file, or search for "MITRE ATLAS" on Splunkbase.

---

## Getting Started

After installation, the app provides a guided setup experience:

### 1. Open the Setup tab

The **Setup** dashboard scans your environment for existing AI/LLM data and validates which detection rules your data supports.

### 2. Review the Configuration Guide

If you don't have AI/LLM data in Splunk yet, the **Configuration Guide** tab provides step-by-step instructions for each supported platform — what to enable, which fields to expect, and how to route to Splunk.

### 3. Configure the atlas_index macro

All 10 detection rules reference the `atlas_index` macro. Update it to point to your AI/LLM log index:

**Settings → Advanced Search → Search Macros → atlas_index**

Default value: `index=main`. Change to match your environment (e.g., `index=ai_logs`).

### 4. Enable detection rules

All rules ship **disabled by default**. Enable them in:

**Settings → Searches, Reports, and Alerts → App: MITRE ATLAS AI Threat Detection → Owner: All**

Enable Tier 1 rules immediately if you have operational telemetry. Enable Tier 2 rules after confirming prompt text is available in your data (the Setup dashboard validates this).

### 5. View detections

Enabled rules run on schedule (every 15–30 minutes) and write results to the `summary` index. The **MITRE ATLAS Detections** dashboard reads from the summary index and displays detection results.

---

## Architecture

- All rules reference a single `atlas_index` macro — configure once, all rules inherit
- Detection results are written to `index=summary` via Splunk's summary indexing action
- The dashboard reads pre-computed results from the summary index for fast rendering
- Rules ship disabled to prevent false positives before configuration
- No Python scripts, no external dependencies — pure SPL and CSV lookups

---

## Extending the Rules

Each rule is a standard Splunk saved search. Common extensions:

**Add SOAR response actions:**
```
action.notable = 1
action.risk = 1
action.risk.param._risk_score = 75
action.risk.param._risk_object = user
action.risk.param._risk_object_type = user
```

**Custom suppression:**
```
alert.suppress = 1
alert.suppress.fields = user, src_ip
alert.suppress.period = 2h
```

---

## About GIC Engineering

GIC Engineering Consultants builds security content and Splunk apps focused on emerging threat categories.

This app is a standalone community release and a preview of the detection logic being built into the full **Supply Chain & AI Threat Intelligence Platform (SCIP)** — which adds SBOM ingestion, NVD/CVE correlation, PCI DSS 4.0 and NIST CSF 2.0 compliance reporting, and risk scoring across supply chain and AI threat dimensions.

**Related apps on Splunkbase:**
[View all GIC Engineering apps on Splunkbase](https://splunkbase.splunk.com/apps?page=1&author=mhouse3)
- GIC STIG Compliance for Splunk
- GIC Compliance Posture for Splunk
- GIC Supply Chain & AI Threat Intelligence Platform *(coming 2026)*

---

## Support

Questions, bug reports, and configuration help: [contact@gicengineeringconsultants.com](mailto:contact@gicengineeringconsultants.com)

---

## License

Apache License 2.0 — free for commercial and personal use.
