# Whisper Security Add-on for Splunk

## Overview

TA-whisper-graph connects Splunk to the Whisper Security Knowledge Graph (3.67B nodes, 30.8B edges) for three core capabilities:

1. **Enrichment** -- enrich any Splunk event with infrastructure context, threat intel, and risk scores via `whisperlookup`
2. **Graph Query** -- query the Knowledge Graph directly from SPL with Cypher via `whisperquery`
3. **Owned-Asset Monitoring** -- attack surface change detection and compliance posture for your domains

The graph covers DNS, BGP, WHOIS, GeoIP, SPF, and threat intel data.

## Compatibility, prerequisites, and requirements

| Requirement | Details |
|:---|:---|
| Splunk Enterprise | 10.2+ |
| Splunk Cloud Platform | 10.2+ |
| Python | 3.13 (ships with Splunk 10.2+; selected via `python.required`) |
| API key | Obtain from [whisper.security](https://console.whisper.security) |
| Network access | HTTPS to `graph.whisper.security` on port 443 |
| ES integration (optional) | Splunk Enterprise Security 7.0+ |

## Installation

1. Download the `TA-whisper-graph-*.spl` package.
2. In Splunk Web, go to **Apps > Manage Apps > Install app from file**.
3. Upload the `.spl` file and restart Splunk when prompted.
4. Verify the add-on appears under **Apps**.

For Splunk Cloud, submit the `.spl` through self-service app installation or contact your Splunk Cloud admin. The add-on passes AppInspect precert and cloud vetting.

CLI alternative:

```
$SPLUNK_HOME/bin/splunk install app TA-whisper-graph-*.spl
```

## Configuration

1. Navigate to **Apps > Whisper Security Add-on for Splunk > Configuration > Account**.
2. Click **Add**, enter a name, the base URL (`https://graph.whisper.security`), and your API key.
3. Click **Test Connectivity** to verify. The button shows your plan tier.
4. Click **Save**. The API key is stored in Splunk's encrypted `storage/passwords`.
5. Go to **Inputs** to enable data collection (threat intel, baselines, watchlist).

Create a `whisper` index before enabling inputs, or override the `whisper_index` macro to use an existing index.

## App components

### Search commands

| Command | Type | Description |
|:---|:---|:---|
| `whisperlookup` | Streaming | Enriches events with infrastructure context, threat intel, and risk scores |
| `whisperquery` | Generating | Runs raw Cypher queries against the Knowledge Graph |
| `whisperschema` | Generating | Explores graph schema (node labels, relationship types, properties) |
| `whisperflush` | Generating | Flushes the KV Store enrichment cache |
| `whisperevict` | Generating | Evicts expired entries from the enrichment cache |

### Dashboards (views)

| View | Description |
|:---|:---|
| `whisper_attack_surface_timeline` | DNS infrastructure change timeline with risk scoring and high-priority alerts |
| `whisper_compliance_summary` | Compliance posture mapped to NIS2, NIST SP 800-177, DMARC |
| `whisper_investigation` | Ad hoc domain/IP investigation with Whisper enrichment and graph query |
| `whisper_spf_compliance` | SPF record status and RFC 7208 10-lookup limit compliance |
| `whisper_mail_config` | Mail server (MX) configuration and change detection |

### Modular inputs

| Input | Sourcetype | Description |
|:---|:---|:---|
| Whisper Threat Intel | `whisper:threat_intel` | Threat indicator collection for ES threat intel framework |
| Whisper Baseline | `whisper:attack_surface` | DNS baseline collection for change detection |
| Whisper Watchlist | `whisper:watchlist` | Domain watchlist enrichment |

### KV Store collections

| Collection | Description |
|:---|:---|
| `whisper_enrichment_cache` | Cached enrichment results with configurable TTL |
| `whisper_precomputed_enrichment` | Precomputed enrichment for watchlist domains |
| `whisper_ip_intel` | ES-compatible IP threat intel indicators |
| `whisper_domain_intel` | ES-compatible domain threat intel indicators |
| `whisper_watchlist` | Domain watchlist for continuous monitoring |
| `whisper_dns_baseline` | DNS baseline snapshots for change detection |

### Lookup files

| Lookup | Description |
|:---|:---|
| `whisper_risk_factors.csv` | Risk factor definitions with point values |
| `whisper_high_risk_asns.csv` | Known bulletproof/high-risk ASNs |
| `whisper_cdn_asns.csv` | CDN provider ASNs (for filtering) |
| `whisper_dns_providers.csv` | Public DNS provider identification |
| `whisper_org_asns.csv` | Organization-owned ASN mappings |

### Macros

| Macro | Description |
|:---|:---|
| `whisper_index` | Index reference used by all dashboards (default: `index=whisper`) |
| `whisper_shared_nameservers(1)` | Find domains sharing nameservers with a given domain |
| `whisper_asn_infrastructure(1)` | List prefixes routed by an ASN |
| `whisper_cname_chain(1)` | Trace CNAME resolution chain for a hostname |
| `whisper_spf_chain(1)` | Trace SPF include chain for a domain |
| `whisper_bgp_peers(1)` | Find BGP peers of an ASN |
| `whisper_cohosted_domains(1)` | Find domains co-hosted on the same IP |
| `whisper_full_investigation(1)` | Full infrastructure pivot for a domain |
| `whisper_explain(1)` | Threat intelligence explanation for an indicator |

### Saved searches

The add-on ships only a small set of disabled saved searches focused on three
workflows: enrichment pipelines (see example templates), attack-surface
monitoring (the owned-domain modular input), and indicator investigation (the
Investigation dashboard, not a scheduled search). There is no broad pre-built
detection pack; customers who want detections clone the example enrichment
templates and tailor them to their data.

| Search | Purpose |
|:---|:---|
| Whisper - Evict Expired Cache Entries | Remove expired entries from the enrichment cache KV Store |
| Whisper - Populate IP Threat Intel KV Store | Optional ES Threat Intel populator |
| Whisper - Populate Domain Threat Intel KV Store | Optional ES Threat Intel populator |
| Whisper - Populate Precomputed Enrichment KV Store | Optional utility that pre-warms the enrichment cache for frequently used indicators |
| Example - Whisper - Enrich DNS Domains | Template for enriching DNS query domains |
| Example - Whisper - Enrich Destination IPs | Template for enriching destination IPs |
| Example - Whisper - Enrich Proxy Hostnames | Template for enriching proxy/web hostnames |
| Example - Whisper - Custom Graph Query Enrichment | Template for enriching via a custom Cypher query |

### Roles

| Role | Description |
|:---|:---|
| `whisper_user` | Grants access to search commands, dashboards, and KV Store collections |

Assign `whisper_user` to users who need access. Admin and sc_admin roles have access by default.

### CIM compliance

Events use FIELDALIAS definitions in `props.conf` to map to CIM data models:

| CIM Data Model | Mapped fields |
|:---|:---|
| Network Resolution | `dest_ip`, `dest_country`, `dest_asn` |
| Threat Intelligence | `threat_score`, `threat_level`, `risk_score`, `risk_level`, `is_threat`, `is_c2`, `is_tor`, `is_malware`, `is_phishing`, and 8 more boolean indicators |

Sourcetype tags: `whisper:enrichment` is tagged `network`, `resolution`, `dns`.

### Index

The add-on writes to the `whisper` index by default. Create this index before enabling inputs. To use a different index, override the `whisper_index` macro in `local/macros.conf`.

## Troubleshooting

| Issue | Solution |
|:---|:---|
| "No API key configured" | Add or re-enter your API key under Configuration > Account |
| Connection timeout | Verify HTTPS access to `graph.whisper.security:443`. Check proxy settings |
| Empty enrichment results | The indicator may not exist in the graph, or your plan's depth limit was reached |
| Correlation searches not firing | They're disabled by default. Enable them in Saved Searches or ES Content Management |
| Permission denied on search commands | Assign the `whisper_user` role to the user |

Logs are written to `$SPLUNK_HOME/var/log/splunk/TA-whisper-graph/ta_whisper_graph.log` (app-namespaced for Splunk Cloud Victoria). On older deployments, the TA falls back to `$SPLUNK_HOME/var/log/splunk/ta_whisper_graph.log`. Collect diagnostics with:

```
$SPLUNK_HOME/bin/splunk diag --collect app:TA-whisper-graph
```

## Support

- Documentation: https://www.whisper.security/docs/integrations/splunk
- Issues: https://console.whisper.security/support
- Email: support@whisper.security

## License

Copyright (c) 2024-2026 Whisper Security. All rights reserved.
