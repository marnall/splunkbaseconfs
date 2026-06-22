# Whisper Security Add-on for Splunk

## Overview

TA-whisper-security connects Splunk to the Whisper Security Knowledge Graph API for IOC enrichment, threat intelligence, attack surface monitoring, and compliance reporting. The graph covers DNS, BGP, WHOIS, GeoIP, SPF, and threat intel data.

## Compatibility, prerequisites, and requirements

| Requirement | Details |
|:---|:---|
| Splunk Enterprise | 9.0+ |
| Splunk Cloud Platform | 9.0+ |
| Python | 3.9+ (ships with Splunk 9.x+) |
| API key | Obtain from [whisper.security](https://console.whisper.security) |
| Network access | HTTPS to `graph.whisper.security` on port 443 |
| ES integration (optional) | Splunk Enterprise Security 7.0+ |

## Installation

1. Download the `TA-whisper-security-*.spl` package.
2. In Splunk Web, go to **Apps > Manage Apps > Install app from file**.
3. Upload the `.spl` file and restart Splunk when prompted.
4. Verify the add-on appears under **Apps**.

For Splunk Cloud, submit the `.spl` through self-service app installation or contact your Splunk Cloud admin. The add-on passes AppInspect precert and cloud vetting.

CLI alternative:

```
$SPLUNK_HOME/bin/splunk install app TA-whisper-security-*.spl
```

## Configuration

1. Navigate to **Apps > Whisper Security Add-on for Splunk > Configuration > Account**.
2. Click **Add**, enter a name, the base URL (`https://graph.whisper.security`), and your API key.
3. Click **Test Connectivity** to verify. The button shows your plan tier.
4. Click **Save**. The API key is stored in Splunk's encrypted `storage/passwords`.
5. Go to **Inputs** to enable data collection (health checks, threat intel, baselines).

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
| `whisper_compliance_summary` | Compliance posture mapped to NIS2, NIST SP 800-81, DMARC |
| `whisper_spf_compliance` | SPF record status and RFC 7208 10-lookup limit compliance |
| `whisper_dnssec_compliance` | DNSSEC adoption, algorithm distribution, signing status |
| `whisper_mail_config` | Mail server (MX) configuration and change detection |
| `whisper_executive_risk` | Executive risk summary with DNS, email, infrastructure grades |
| `whisper_risk_overview` | ES risk score distribution, trends, and top risky indicators |
| `whisper_geographic_threats` | GeoIP-based threat visualization by country and city |
| `whisper_whois_intelligence` | WHOIS registrar, organization, and contact correlation |
| `whisper_web_link_trust` | Inbound/outbound link profiles and suspicious link detection |
| `whisper_mitre_coverage` | MITRE ATT&CK technique coverage from infrastructure detections |
| `whisper_health_operations` | API health, graph stats, enrichment timeline, input status |
| `whisper_attack_surface_timeline` | DNS infrastructure change timeline and baseline diffs |

### Modular inputs

| Input | Sourcetype | Description |
|:---|:---|:---|
| Whisper Health | `whisper:health` | API health checks and graph statistics |
| Whisper Threat Intel | `whisper:threat_intel` | Threat indicator collection for ES threat intel framework |
| Whisper Baseline | `whisper:attack_surface` | DNS baseline collection for change detection |
| Whisper Watchlist | `whisper:watchlist` | Domain watchlist enrichment |
| Whisper Multitenant | `whisper:attack_surface_summary` | Multi-tenant attack surface monitoring |

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

### Saved searches and correlation searches

The add-on includes 30 saved searches. Correlation searches are disabled by default. Enable them under **Settings > Searches, Reports, and Alerts** or in ES Content Management.

Notable correlation searches:

| Search | MITRE ATT&CK |
|:---|:---|
| Bulletproof ASN Communication Detection | T1583 |
| Shared Nameserver with Threat Infrastructure | T1584 |
| DNS Infrastructure Change Detection | T1584 |
| Low Co-Hosting Density Anomaly | T1583 |
| BGP Prefix Conflict Detection | T1599 |

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

Logs are written to `$SPLUNK_HOME/var/log/splunk/ta_whisper_security.log`. Collect diagnostics with:

```
$SPLUNK_HOME/bin/splunk diag --collect app:TA-whisper-security
```

## Support

- Documentation: https://www.whisper.security/docs/integrations/splunk
- Issues: https://console.whisper.security/support
- Email: support@whisper.security

## License

Copyright (c) 2024-2026 Whisper Security. All rights reserved.
