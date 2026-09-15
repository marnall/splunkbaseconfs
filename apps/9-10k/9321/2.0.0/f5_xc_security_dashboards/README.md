# F5 Distributed Cloud (XC) — Visualization App

Dark-themed dashboard app for **F5 Distributed Cloud (XC)** security & traffic telemetry.
Companion to the **TA-f5-xc** add-on (which does the CIM field mapping). This app is
visualization-only — no inputs, no index-time config.

## Dashboards

| View | Focus |
|------|-------|
| **Executive Overview** | KPIs, event/severity/action trends, live attacker geomap + country choropleth, top talkers, signatures, response codes |
| **Application Security (WAF)** | App-firewall signatures, attack categories, severity mix, targeted apps/URLs, attacker attribution, recent high-severity attacks |
| **Bot Defense** | Malicious vs good bots, classification trend, top bot identities & sources, bot geomap, bot user agents |
| **Service Policy & Geo** | L7 policy enforcement (geofencing/IP-rep), blocked-origin choropleth + marker map, connection-level L4 + TLS detail, response time |
| **Traffic & Performance** | Status-class trends, response codes, methods, top domains/URLs, payload sizes, client bandwidth |

## Requirements

- **TA-f5-xc** installed (provides `src`, `dest`, `action`, `signature`, `severity`,
  `category`, `http_*`, `tls_*`, `response_time`, etc.). Without it most panels are empty.
- Splunk **8.1+** (uses the SimpleXML `theme="dark"` attribute and built-in `geom`/`geostats`).
- Geospatial panels use the bundled `geo_countries` geom lookup + `iplocation` (no extra add-on).

## Base search

All panels start from the `f5xc` macro, which keys off the TA-f5-xc vendor sourcetype:

```
[f5_xc_index]
definition = index=*

[f5xc]
definition = `f5_xc_index` sourcetype=f5:xc
```

By default this matches `sourcetype=f5:xc` across every index. To scope to a specific
index, edit the `f5_xc_index` macro in `default/macros.conf` (e.g. `index=f5_xc`), or
override either macro in `local/`.

## Data-shape notes

- The dashboards assume F5 XC **security events** (WAF, Bot Defense, service-policy). Where
  a feed is security-events only (no plain access logs), "Traffic & Performance" is derived
  from the security events, which are still full HTTP transactions.
- `tls_version`, `ssl_cipher`, `response_time`, `dest_port` typically exist only on
  service-policy (`svc_policy_sec_event`) records — those panels live on the Service Policy
  dashboard and are labeled accordingly.
- If Bot Defense runs in **alert mode** (`action=allowed` even for `MALICIOUS`), the bot
  dashboards key off `category`, not `action`.
- Events without real client lat/long (internal / `PRIVATE`) are excluded from maps.

## Filters

Each dashboard has a time picker plus contextual dropdowns (event class / action / severity /
classification) and, where useful, a wildcard **Domain** text filter. "All" choices use an
always-true sentinel so panels never break on an unset token.
