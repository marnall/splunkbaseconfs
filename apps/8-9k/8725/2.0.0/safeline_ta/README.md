# SafeLine WAF — Splunk App (`safeline_TA`)

Complete Splunk app for **Chaitin SafeLine WAF**: parsing, CIM mapping, dashboards, alerts and threat-hunting tooling — all in one bundle.

> Drop-in install. No editing required to get the dashboards working.

---

## Features

### Parsing
- **Sourcetype**: `safeline:waf`
- Auto-extracts **all** top-level JSON fields from SafeLine syslog output (~70 fields per event)
- Possessive-quantifier regex — fast even on multi-KB events with heavily escaped bodies
- Parses HTTP request/response header blobs into individual headers (`req_header_*`, `rsp_header_*`)
- Calculated fields: `severity`, `severity_id`, `is_attack`, `blocked`, `is_https`, `src_is_private`, `bytes`, `duration`, `site_host`, `site_name`, …

### CIM compliance
Mapped to **Web**, **Network_Traffic**, **Intrusion_Detection** and **Alerts** data models out of the box.

### Dashboards (9)

| Dashboard | What it's for |
|-----------|---------------|
| **Overview** | High-level KPIs, top-N, traffic over time |
| **Real-Time Monitor** | Auto-refreshing live view (5-60 min window) |
| **Site Compare** | Cross-vhost scorecard with conditional colouring |
| **Site Detail** | One-vhost deep dive — KPIs, latency, attackers, paths |
| **Attacks** | Severity drill-down, top rules, top targeted endpoints |
| **IP Reputation** | Risk-scored attacker scoreboard, repeat offenders, multi-site attackers, single-IP profile |
| **Bot & JA4 Analysis** | TLS fingerprint distribution, suspicious JA4, UA/JA4 mismatch, bot detection |
| **Traffic** | Request volume, latency percentiles, status codes, top hosts |
| **Geo** | Cluster map, country/city breakdown, public vs private |
| **Compliance & Audit** | SOC-friendly summary with HTTPS coverage, mitigation rate, heatmap, top threat actors |

### Alerts (5, disabled by default)
- Critical attack detected (5-min cron)
- High-volume attacker (50+ attacks in 15 min from one IP)
- Multi-site attacker (≥3 distinct vhosts)
- WAF mitigation rate dropped below 70%
- Sudden traffic spike on a site

Enable in **Settings → Searches, reports, and alerts** after configuring your delivery channel (email / webhook / Slack / PagerDuty).

### Workflow actions (right-click menus)
- "SafeLine: this IP — last 24h" — jumps to IP Reputation dashboard
- "SafeLine: drill-down this site" — jumps to Site Detail
- "SafeLine: events for this rule" / "this attack type"
- OSINT links to **VirusTotal**, **AbuseIPDB**, **Shodan** (disabled — enable via `local/workflow_actions.conf`)

### Lookups
- `safeline_action.csv` — Allow/Deny/Block label normalisation
- `safeline_attack_type.csv` — 27 attack types categorised (Injection / Path Traversal / Auth / Recon / Protocol / Availability / Policy)

### Saved macros
- `safeline_waf` — base search
- `safeline_attacks` — `is_attack=1`
- `safeline_blocked` — blocked
- `safeline_spath` — re-parses captured `json_payload` if you need nested JSON

---

## Install (Splunk Web)

1. **Apps → Manage Apps → Install app from file**
2. Upload `safeline_TA-2.0.0.tar.gz`
3. **Restart Splunk** (full restart — needed for `transforms.conf`)
4. Open **Apps → SafeLine WAF**

### Install (CLI)

```bash
$SPLUNK_HOME/bin/splunk install app safeline_TA-2.0.0.tar.gz
$SPLUNK_HOME/bin/splunk restart
```

### Install (manual copy)

```bash
tar -xzf safeline_TA-2.0.0.tar.gz -C $SPLUNK_HOME/etc/apps/
chown -R splunk:splunk $SPLUNK_HOME/etc/apps/safeline_TA
$SPLUNK_HOME/bin/splunk restart
```

### Where to install

| Tier | Install? |
|------|----------|
| Search Head | ✅ required (search-time extractions, dashboards) |
| Indexer / HF (whichever does parsing) | ✅ required |
| Universal Forwarder | only if it's also receiving syslog |

---

## Configure inputs

Inputs are **disabled by default**. Enable one of these in `local/inputs.conf` (don't edit `default/inputs.conf`):

### UDP (most common)
```ini
[udp://514]
disabled    = false
sourcetype  = safeline:waf
index       = safeline
no_appending_timestamp = true
connection_host = ip
```

### TCP
```ini
[tcp://1514]
disabled    = false
sourcetype  = safeline:waf
index       = safeline
```

### File (rsyslog → file)
```ini
[monitor:///var/log/safeline/*.log]
disabled    = false
sourcetype  = safeline:waf
index       = safeline
```

> **Index name**: app uses `safeline` (or `waf`) — change `index =` to whatever exists in your environment.

---

## Verify

```spl
index=safeline sourcetype="safeline:waf" | head 5
```

You should see ~70 fields including:
`src_ip, dest_ip, scheme, protocol, host, http_host, method, http_method, urlpath, url_path,`
`status_code, status, attack_type, signature, severity, severity_id, action, action_cim, blocked, is_attack,`
`site_url, site_name, site_uuid, country, src_country, src_city, lat, lng,`
`ja4_fingerprint, tls_ja4_family, user_agent, http_user_agent, referer, cookie,`
`req_start_time, total_duration_ms, duration, bytes, bytes_in, bytes_out, …`

Plus parsed individual HTTP headers from `req_header_raw` / `resp_header_raw`:
`req_header_Host, req_header_Content-Type, req_header_X-Request-Id, request_method, request_uri, response_status_code, …`

---

## Troubleshooting

### Fields missing after install
1. Did you **restart** Splunk? `transforms.conf` doesn't reload via `debug/refresh`.
2. Is the TA on the **Search Head**? REPORT- runs at search time on the SH.
3. Verify configs loaded:
   ```bash
   $SPLUNK_HOME/bin/splunk btool props list safeline:waf | grep REPORT
   $SPLUNK_HOME/bin/splunk btool transforms list safeline_json_kv_strings
   ```

### `src_ip=*` makes search hang
This was a v1.1.1 bug — fixed in v1.1.2 by switching to possessive-quantifier regex. Make sure you're on v2.0.0+.

### Geo map empty
Source IPs are private — SafeLine only enriches public IPs. Filter by `src_is_private=0` or check the **Public sources** KPI on the Geo dashboard.

### Index not found
Either create one (`Settings → Indexes → New Index → safeline`) or change the index in your `local/inputs.conf`.

---

## Customising

Override anything in `local/`:
- `local/inputs.conf` — your syslog ports / file paths
- `local/savedsearches.conf` — enable alerts, set notification channels
- `local/workflow_actions.conf` — enable OSINT links (VirusTotal / AbuseIPDB / Shodan)
- `local/props.conf` — extra `EVAL-`, `FIELDALIAS-`, `LOOKUP-`

Example — enable critical-attack email alert in `local/savedsearches.conf`:
```ini
[SafeLine - Critical attack detected]
disabled = 0
actions = email
action.email.to = security@example.com
action.email.subject = SafeLine: critical attack on $name$
```

---

## File layout

```
safeline_TA/
├── README.md
├── install.sh
├── default/
│   ├── app.conf
│   ├── props.conf              ← sourcetype + 30 aliases + 25 EVALs + 2 lookups
│   ├── transforms.conf         ← header / JSON KV / HTTP-header regex transforms
│   ├── fields.conf             ← 100+ field declarations for the UI sidebar
│   ├── eventtypes.conf
│   ├── tags.conf               ← CIM mapping
│   ├── macros.conf             ← `safeline_waf`, `safeline_attacks`, `safeline_blocked`, `safeline_spath`
│   ├── savedsearches.conf      ← 5 alerts + 2 reports (disabled)
│   ├── workflow_actions.conf   ← right-click menus + OSINT
│   ├── inputs.conf             ← UDP/TCP/file (disabled examples)
│   ├── indexes.conf.example
│   └── data/ui/
│       ├── nav/default.xml
│       └── views/
│           ├── safeline_overview.xml
│           ├── safeline_realtime.xml
│           ├── safeline_site_compare.xml
│           ├── safeline_site_detail.xml
│           ├── safeline_attacks.xml
│           ├── safeline_ip_reputation.xml
│           ├── safeline_bot_analysis.xml
│           ├── safeline_traffic.xml
│           ├── safeline_geo.xml
│           └── safeline_compliance.xml
├── lookups/
│   ├── safeline_action.csv
│   └── safeline_attack_type.csv
├── metadata/default.meta           ← global export
├── samples/inputs.conf.example     ← inputs to deploy on a Heavy Forwarder
└── local/                          ← your overrides
```

---

## Changelog

### 2.0.0
- 4 new dashboards: **Real-Time Monitor**, **Bot & JA4 Analysis**, **IP Reputation & Hunt**, **Compliance & Audit**
- 5 saved alerts (critical attack / volume / multi-site / mitigation drop / spike)
- Workflow actions (right-click): jump to IP, site, rule, attack-type drill-downs + OSINT (VT/AbuseIPDB/Shodan)
- Reorganised navigation with grouped collections (Sites, Threat Hunting)
- Polished README with full troubleshooting

### 1.3.0
- Site Compare scorecard, Site Detail deep-dive
- Cross-site comparison (bubble chart, conditional colouring)

### 1.2.0
- Switched site filter from `http_host` (spoofable) to `site_url` (SafeLine-configured vhost)
- New fields: `site_host`, `site_name`, `site` (CIM)

### 1.1.2
- Fixed `src_ip=*` hanging — possessive-quantifier regex prevents catastrophic backtracking on `body`

### 1.1.1
- Split JSON KV regex into separate string + primitive transforms (fixes empty-overwrite bug)

### 1.1.0
- 4 base dashboards (Overview, Attacks, Traffic, Geo)
- Comprehensive field aliases + 100+ field declarations + HTTP header parsing

### 1.0.0
- Initial release: sourcetype, basic extractions, CIM tags

---

## Author

**Hadi Tayanloo** &lt;htayanloo@gmail.com&gt;

## License

Internal / custom add-on.
