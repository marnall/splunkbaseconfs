# Speculus Threat Intelligence for Splunk

Enrich IP addresses in your Splunk searches with the Speculus combined threat
intelligence database, and scan whole indexes for risky IPs from prebuilt
dashboards. All lookups run locally against an MMDB file kept fresh by a
built-in updater — no per-event API calls, no data leaves your Splunk
deployment.

## What's included

- **`| speculus` search command** — streams events through the local threat
  database and appends `speculus_*` fields:
  - `speculus_score` (0–100), `speculus_risk` (low / medium / high / very high)
  - `speculus_asn`, `speculus_isp`, `speculus_org`, `speculus_connection_type`
  - geo: `speculus_country`, `speculus_country_code`, `speculus_city`,
    `speculus_lat`, `speculus_lon`
  - flags: `speculus_is_tor`, `speculus_is_vpn`, `speculus_is_proxy`,
    `speculus_is_datacenter`, `speculus_is_blacklisted`
  - proxy overlay: `speculus_proxy_type`, `speculus_proxy_provider`,
    `speculus_proxy_first_seen`, `speculus_proxy_last_seen`,
    `speculus_proxy_days_seen`, `speculus_proxy_score`
  - threat overlay: `speculus_threat_activity`, `speculus_threat_malware`,
    `speculus_threat_first_seen`, `speculus_threat_last_seen`,
    `speculus_threat_compromised`, `speculus_threat_corroboration`
  - `speculus_matched` — "true" when the IP is in the database
- **Speculus MMDB Updater** data input — downloads database updates on a
  schedule (conditional GET; unchanged database costs one 304 round-trip).
- **Dashboards** — *Index Risk Scan* (scan any index/field for risky IPs) and
  *IP Investigate* (single-address lookup).

## Requirements

- Splunk Enterprise 9.x or later (Splunk Cloud Platform compatible), Python 3.
- A Speculus API key and MMDB endpoint URL.
- The command runs on the search head (`distributed = false`); indexers do not
  need the app or the database file.

## Setup

1. Install the app on your search head.
2. Open the app and follow the **Setup** page in the app navigation, or go to
   **Settings > Data inputs > Speculus MMDB Updater** directly: set
   **Endpoint URL** and **API key** (provided with your Speculus
   subscription), then enable the input. The key is moved into Splunk secure
   storage and masked after the first run.
3. Wait for the first download (within one interval, or restart Splunk to
   trigger it immediately), then run:

   ```
   | makeresults | eval ip="203.0.113.7" | speculus field=ip
   ```

IPv4 and IPv6 are both supported.

## Usage examples

```
index=firewall | speculus field=src_ip | where speculus_score >= 75
sourcetype=access_combined | speculus field=clientip | stats count by speculus_risk
index=proxy | speculus | where speculus_is_tor="true"
```

If `field=` is omitted the command uses the first present field among:
`src_ip, dest_ip, src, dest, clientip, client_ip, remote_addr, remote_ip, ip`.

## Support

Developed by Speculus. Contact: support@speculus.co
