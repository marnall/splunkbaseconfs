# UniFi Network Add-on for Splunk (TA_unifi_ng)

Polls a UniFi Network controller via the **Integration API v1**
(`/proxy/network/integration/v1`) and indexes the results into Splunk.
Read-only. Credentials are stored encrypted via the Configuration → Accounts page.

## Setup

1. **Configuration → Account**: add your controller (`controller_url`, `api_key`,
   `verify_ssl`). Create the API key in the UniFi controller under
   **Settings → Control Plane → Integrations**.
2. **Settings → Data inputs**: create one or more inputs (see below).
3. Send **all** inputs to the **same index** (recommended).

## Inputs (grouped by cadence)

| Input | Default interval | Purpose |
|-------|------------------|---------|
| **UniFi Inventory** (`unifi_inventory`) | **180 s** | Configuration/inventory lists. Toggle individual lists; each toggle shows its sourcetype. |
| **UniFi Telemetry** (`unifi_telemetry`) | **60 s** | Per-device performance stats + full device detail. One API call per device per collector — raise the interval on large fleets. |
| **UniFi Reference** (`unifi_reference`) | **86400 s** | Large near-static reference data: countries, DPI applications/categories. |
| `unifi_ingest` (legacy) | 300 s | Original input (sites/devices/clients/networks). Kept for backward compatibility — prefer **UniFi Inventory** for new setups. |

Each input auto-discovers all sites (or set a `Site Filter`), paginates at
`page_size` (max 200), and shares the per-input interval across its lists.

## Sourcetypes (v3.0.0 — Inventory input)

| Toggle | Sourcetype(s) | Scope | Docs |
|--------|---------------|-------|------|
| collect_devices | `unifi:device` | per-site | getadopteddeviceoverviewpage |
| collect_clients | `unifi:client` | per-site | getconnectedclientoverviewpage |
| collect_networks | `unifi:network` | per-site | getnetworksoverviewpage |
| collect_device_tags | `unifi:device_tag` | per-site | getdevicetagpage |
| collect_firewall | `unifi:firewall:zone`, `unifi:firewall:policy`, `unifi:acl_rule` | per-site | getfirewallpolicies |
| collect_wifi | `unifi:wifi:broadcast` | per-site | getwifibroadcastpage |
| collect_wan | `unifi:wan` | per-site | getwansoverviewpage |
| collect_vpn | `unifi:vpn:server`, `unifi:vpn:tunnel` | per-site | getvpnserverpage |
| collect_switching | `unifi:switching:lag`, `unifi:switching:mc_lag_domain`, `unifi:switching:switch_stack` | per-site | getlagpage |
| collect_dns | `unifi:dns:policy` | per-site | getdnspolicypage |
| collect_traffic_lists | `unifi:traffic_matching_list` | per-site | gettrafficmatchinglists |
| collect_radius | `unifi:radius:profile` | per-site | getradiusprofileoverviewpage |
| collect_vouchers | `unifi:hotspot:voucher` | per-site | getvouchers |
| collect_pending_devices | `unifi:device:pending` | controller | getpendingdevicepage |
| collect_info | `unifi:info` | controller | getinfo |
| collect_network_detail | `unifi:network:detail`, `unifi:network:reference` | per-network | getnetworkdetails |
| (always) | `unifi:site` | per-site | getsiteoverviewpage |

`collect_network_detail` makes 1–2 extra API calls per network and carries
`unifi_network_id`.

## Sourcetypes (v3.1.0 — Telemetry input)

| Toggle | Sourcetype | Scope | Docs |
|--------|-----------|-------|------|
| collect_device_stats | `unifi:device:stats` | per-device | getadopteddevicelateststatistics |
| collect_device_detail | `unifi:device:detail` | per-device | getadopteddevicedetails |

Telemetry events also carry `unifi_device_id` and `unifi_device_mac` to join
back to `unifi:device`. `unifi:device:stats` sets `_time` from the device
`lastHeartbeatAt`.

## Sourcetypes (v3.2.0 — Reference input)

| Toggle | Sourcetype | Scope | Docs |
|--------|-----------|-------|------|
| collect_countries | `unifi:ref:country` | controller | getcountries |
| collect_dpi_applications | `unifi:ref:dpi_application` | controller | getdpiapplications |
| collect_dpi_categories | `unifi:ref:dpi_category` | controller | getdpiapplicationcategories |

Docs base URL: `https://developer.ui.com/network/<version>/<anchor>`

Controller-wide objects use `unifi_site_id = _global`.

## Common fields on every event

`unifi_host`, `unifi_site_id`, `unifi_site_name`, `unifi_object_type`,
`unifi_collection_time` (pull time), plus `unifi_api_<field>` for API
timestamps and the full object JSON in `_raw`.

## Example searches

```spl
index=<your_index> sourcetype=unifi:device
| table unifi_site_name name model ipAddress macAddress state firmwareVersion

index=<your_index> sourcetype=unifi:firewall:policy enabled=true
| table unifi_site_name name action_type index

index=<your_index> sourcetype="unifi:*" | stats count by sourcetype
```

Device `state` values: `ONLINE`, `OFFLINE`, `PENDING_ADOPTION`, `UPDATING`,
`GETTING_READY`, `ADOPTING`.

## CIM compliance (v3.3.0)

Field aliases, calculated fields and CIM tags map UniFi data onto Splunk
Common Information Model data models for use with Enterprise Security, ITSI
and CIM-based apps:

| Sourcetype(s) | CIM data model | Key fields |
|---|---|---|
| `unifi:device`, `unifi:device:detail` | Inventory / Network | `mac`, `ip`, `dest`, `family`, `version`, `status`, `dvc`, `vendor_product` |
| `unifi:network`, `unifi:network:detail` | Inventory / Network | `vlan`, `vendor_product` |
| `unifi:client` | Network Sessions | `src_mac`, `src_ip`, `src`, `user`, `action`, `connection_type` |
| `unifi:device:stats` | Performance | `cpu_load_percent`, `mem_used_percent`, `uptime`, `dvc`, `mac` |
| `unifi:firewall:policy` | (rules) | `rule`, `action`, `src_zone`, `dest_zone` |

To accelerate CIM data models against this data, ensure the CIM app's data
models include your UniFi index.

## Dashboards (v3.3.0)

Three sample dashboards ship under the app's **Dashboards** menu:

| Dashboard | Shows |
|---|---|
| **UniFi - Overview** | Sites/devices/clients/networks counts, events by sourcetype, devices by model, clients by type |
| **UniFi - Device Health** | Avg CPU/memory, CPU over time per device, top devices by CPU, inventory + state (needs Telemetry input) |
| **UniFi - Clients &amp; Network** | Clients over time, clients per uplink, firewall policies by action, SSIDs, recent clients |

Each dashboard has an **Index** input (default `*`) — set it to your UniFi
index for best performance.
