## SafeLine WAF Splunk App — v2.0.0

Complete Splunk app for [Chaitin SafeLine WAF](https://github.com/chaitin/SafeLine).
Drop-in: install the `.tar.gz`, restart Splunk, configure a syslog input, you're done.

### Install

Splunk Web → **Apps → Manage Apps → Install app from file** → upload `safeline_TA-2.0.0.tar.gz` → **Restart Splunk**.

Or via CLI:
```bash
$SPLUNK_HOME/bin/splunk install app safeline_TA-2.0.0.tar.gz
$SPLUNK_HOME/bin/splunk restart
```

### What's in the box

**Parsing**
- Sourcetype `safeline:waf` with auto-extraction of all top-level JSON fields (~70)
- Possessive-quantifier regex — safe on multi-KB events with heavily escaped bodies
- HTTP request/response header blob parsing (`req_header_*`, `rsp_header_*`, `request_method`, `response_status_code`, …)
- 25+ EVAL calculated fields: `severity`, `severity_id`, `is_attack`, `blocked`, `is_https`, `bytes`, `duration`, `site_host`, `site_name`
- 30 FIELDALIAS for CIM (Web / Network_Traffic / IDS / Alerts / Auth)

**10 Dashboards**

| Dashboard | What it's for |
|-----------|---------------|
| **Overview** | KPIs, top-N, traffic over time |
| **Real-Time Monitor** | Auto-refreshing 30-sec live view |
| **Site Compare** | Cross-vhost scorecard with conditional colouring |
| **Site Detail** | One-vhost deep dive |
| **Attacks** | Severity drill-down, top rules, top targets |
| **IP Reputation & Hunt** | Risk-scored attacker scoreboard, repeat offenders, single-IP profile |
| **Bot & JA4 Analysis** | TLS fingerprint distribution, bot detection, UA/JA4 mismatch |
| **Traffic** | Latency p50/p90/p95/p99, error rate |
| **Geo** | Cluster map, country/city breakdown |
| **Compliance & Audit** | Audit-ready summary, attack heatmap, coverage report |

**5 Alerts** (disabled by default — enable in Settings → Searches)
- Critical attack detected
- High-volume attacker (50+ in 15 min)
- Multi-site attacker (≥3 vhosts)
- WAF mitigation rate dropped <70%
- Sudden traffic spike on a site

**Workflow actions** (right-click any field)
- Jump to IP Reputation / Site Detail / rule / attack-type drill-downs
- OSINT links: VirusTotal, AbuseIPDB, Shodan (disabled)

**Lookups**
- `safeline_action.csv` — action label normalisation
- `safeline_attack_type.csv` — 27 attack types categorised

### Quick start

```spl
index=safeline sourcetype="safeline:waf" | head 5
```

You should see ~70 fields including `src_ip`, `attack_type`, `severity`, `action`, `site_name`, `site_uuid`, `rule_id`, `ja4_fingerprint`, country/city, latency.

### CIM compatibility

Tagged for `Web`, `Network_Traffic`, `Intrusion_Detection`, `Alerts` data models.

### Author

**Hadi Tayanloo** &lt;htayanloo@gmail.com&gt;
