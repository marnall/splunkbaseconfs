# Changelog — UniFi Network Add-on for Splunk (TA_unifi_ng)

## 3.4.0
- Splunkbase/SLIM-compatible `app.manifest` (removed UCC-only fields `info.port`
  and `info.tags`; aligned remaining keys with the Packaging Toolkit schema).
- Ship Apache-2.0 `LICENSE` inside the app package.
- Declare `python.required = 3.13` on modular inputs and REST handlers.

## 3.3.1
- App icons and packaging/CI for public GitHub releases.

## 3.3.0
- CIM compliance: field aliases / calculated fields for the Inventory,
  Network Sessions and Performance data models; `eventtypes.conf` + `tags.conf`.
- Three sample dashboards (Overview, Device Health, Clients & Network) + nav menu.
- Consolidated `props.conf` to one stanza per sourcetype.

## 3.2.0
- Phase C: `collect_network_detail` toggle on the UniFi Inventory input adds
  `unifi:network:detail` and `unifi:network:reference`.
- Phase D: new **UniFi Reference** input (default daily) adds
  `unifi:ref:country`, `unifi:ref:dpi_application`, `unifi:ref:dpi_category`.

## 3.1.1
- Timestamp hardening: snapshot sourcetypes set `_time` from
  `unifi_collection_time` (emitted first; lookahead 256); `unifi:device:stats`
  uses `lastHeartbeatAt`. Fixes stale client/voucher event times.

## 3.1.0
- Phase B: new **UniFi Telemetry** input (default 60 s) adds
  `unifi:device:stats` and `unifi:device:detail` with per-device error isolation
  and `unifi_device_id` / `unifi_device_mac` join keys.

## 3.0.0
- Phase A: new **UniFi Inventory** input (default 180 s) with 15 per-list
  toggles (each labelled with its sourcetype + Ubiquiti docs link). Adds 16
  inventory/config sourcetypes. Legacy `unifi_ingest` input retained.

## 2.0.1
- Fixed the UCC persistent REST handler (missing `__main__` entrypoint) that
  caused the Configuration page error "Unable to xml-parse the following data: %s".

## 1.x – 2.0.0
- Initial UCC add-on: sites, devices, clients, networks via a single input.
