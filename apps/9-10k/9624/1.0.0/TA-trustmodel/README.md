# TA-trustmodel — TrustModel AI Assurance Add-on for Splunk

**Version:** 0.1.0-alpha (pre-Splunkbase)
**Status:** EPIC TRUS-783 (Cisco-driven). Tickets TRUS-784 + TRUS-786.
**Schema source-of-truth:** TRUS-785 v1.0 (Confluence).

This Technology Add-on receives TrustModel events via HTTP Event Collector and maps them to Splunk Common Information Model so they appear natively in:

- **Splunk Enterprise Security** — Risk-Based Alerting, Notable Events, Exposure Analytics
- **Splunk SOAR** — playbook triggers via Notable Events
- **Splunk Observability Cloud** — AI Agent Monitoring (via OTLP, separate path)

## Sourcetypes

Two sourcetypes only. Eval flavor (LLM, COTS, agentic_trace, DataScan) is carried in the `eval_source` field on every event — search filter, not separate sourcetype.

| Sourcetype | Description | CIM Datamodel |
|---|---|---|
| `trustmodel:eval` | Evaluation lifecycle event (one per terminal-state run, all flavors) | _none_ |
| `trustmodel:finding` | Detected risk / issue within an evaluation (PII, bias, proxy, hallucination, etc.) | `Alerts` (strict) |

The `eval_source` field discriminates — possible values: `llm`, `cots`, `agentic_trace`, `datascan`. See TRUS-785 Confluence doc for full envelope, per-flavor `eval_meta` shapes, and per-dimension `evidence` shapes.

## Install

### 1. Mint an HEC token

In Splunk Web → **Settings → Data Inputs → HTTP Event Collector**:

1. **New Token** with name `trustmodel`
2. Allowed sourcetypes: select `trustmodel:eval`, `trustmodel:finding` (or "All")
3. Default index: `trustmodel` (create the index first if needed: Settings → Indexes)
4. Save and copy the token UUID

### 2. Install the add-on

```bash
# From Splunk web: Apps → Manage Apps → Install app from file
# Upload the TA-trustmodel-0.1.0.tgz package built from this repo.
```

Or, for development:

```bash
cp -r TA-trustmodel $SPLUNK_HOME/etc/apps/
$SPLUNK_HOME/bin/splunk restart
```

### 3. Configure the TrustModel sender

In TrustModel Console: **Settings → Integrations → Splunk → Connect**.

Paste your HEC URL and token. The connection is org-level (one Splunk per TrustModel organization). Once configured, all completed evaluations and detected findings forward automatically. No SDK or app-side changes required.

### 4. Verify

In Splunk:

```spl
index=trustmodel sourcetype=trustmodel:* | head 20
```

Expected: events with `event_type`, `eval_source`, `eval_meta.*`, `severity`, `signature` populated.

## CIM Compliance

`default/props.conf` declares the two sourcetypes with `KV_MODE=json`, so every JSON field — including nested `eval_meta.*` and `evidence.*` — is auto-extracted and searchable directly (e.g. `eval_meta.model=gpt-4o`, `evidence.column=notes`).

CIM field aliases on `trustmodel:finding` (CIM Alerts data model):

| Splunk CIM field | TrustModel field |
|---|---|
| `Alerts.signature` | `signature` |
| `Alerts.severity` | `severity` |
| `Alerts.action` | `action` |
| `Alerts.src_user` | `src_user` |
| `Authentication.user` | `user` |

`trustmodel:eval` is intentionally not mapped to a CIM datamodel. Its events carry
TrustModel-private tags (`trustmodel`, `ai_eval`) only, so they never enter a shared
CIM dataset they don't fit.

Full schema: see TRUS-785 Confluence doc.

## Search examples

```spl
# All LLM evals scoring below 60 in last 24h
sourcetype="trustmodel:eval" eval_source=llm overall_score<60 earliest=-24h

# All findings on COTS fair-lending evals, last 7d
sourcetype="trustmodel:finding" eval_source=cots eval_meta.eval_subtype=fair_lending earliest=-7d

# All BYOK LLM evals (customer used their own API key)
sourcetype="trustmodel:eval" eval_source=llm eval_meta.byok=true

# DataScan PII findings on a specific table
sourcetype="trustmodel:finding" eval_source=datascan dimension=pii eval_meta.table=applicants

# All-flavor: every critical finding, grouped by source
sourcetype="trustmodel:finding" severity=critical
| stats count by eval_source, signature
```

## ES Content Pack

This add-on ships the parsing layer only. Correlation searches, notable events, and dashboards are in the companion ES content pack `DA-ESS-TrustModel` — track under `TRUS-787` (follow-on).

## Cisco AI Defense + Splunk

This add-on is the trust-scoring tap inside the existing Cisco AI Defense → Splunk pipeline. See `TRUS-794` for the joint architecture.

## Support

- Docs: https://trustmodel.ai/splunk
- Issues: https://github.com/pdxlab/trustmodel-splunk-ta/issues
- Email: support@predixtions.com

## License

Copyright (c) 2026 Predixtions / TrustModel. Proprietary.

## Roadmap

- v0.1.0-alpha (this) — TA package aligned with TRUS-785 v1.0 schema
- v0.2.0 — AppInspect-clean, dashboards XML+JSON
- v0.3.0 — Splunkbase Vetted (Cloud), ES content pack auto-bundled
- v1.0.0 — GA on Splunkbase, full Cisco AI Defense partner content pack
