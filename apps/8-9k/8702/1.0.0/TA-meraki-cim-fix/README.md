# Meraki CIM Compliance Add-on for Splunk

## Overview

This add-on provides CIM (Common Information Model) field mappings and tags for Cisco Meraki data collected by the official [Cisco Meraki Add-on for Splunk](https://splunkbase.splunk.com/app/5580) (v3.x). It enables Meraki wireless security and access point events to populate Splunk Enterprise Security data models for correlation, alerting, and dashboarding.

## Problem

The official Cisco Meraki Add-on for Splunk collects data from the Meraki Dashboard API but provides incomplete CIM compliance for two key sourcetypes:

- **`meraki:airmarshal`** — Air Marshal wireless threat detection events are collected but lack the `tag=ids tag=attack` tags and CIM field mappings required by the **Intrusion_Detection** data model. These events do not appear in Splunk ES security dashboards.

- **`meraki:accesspoints`** — Client association, disassociation, and fast roaming events are collected but lack the `tag=network tag=session` tags and CIM field mappings required by the **Network_Sessions** data model. These events are invisible to session-based correlation in Splunk ES.

## Solution

This add-on supplements the official Meraki TA by adding:

1. **Event type definitions** that identify Air Marshal and Access Point session events
2. **CIM tags** that map these event types to the correct data models
3. **Field extractions** (EVAL-based) that map raw Meraki API fields to CIM-compliant field names

## CIM Data Model Coverage

| Data Model | Sourcetype | CIM Fields Mapped |
|---|---|---|
| Intrusion_Detection (IDS_Attacks) | `meraki:airmarshal` | `ids_type`, `signature`, `category`, `severity`, `action`, `src`, `dvc` |
| Network_Sessions | `meraki:accesspoints` | `dest`, `ssid`, `session_action`, `duration` |

The official Meraki TA already provides CIM compliance for:
- **Authentication** — 802.1X events from `meraki:accesspoints`
- **Change** — Configuration changes from `meraki:accesspoints` and device availability events

## Prerequisites

- Splunk Enterprise 9.0 or later
- [Cisco Meraki Add-on for Splunk](https://splunkbase.splunk.com/app/5580) v3.0.0 or later
- [Splunk Common Information Model](https://splunkbase.splunk.com/app/1621) v4.0.0 or later
- Splunk Enterprise Security (recommended, but not required for CIM mapping)

## Installation

### From Splunkbase
1. In Splunk Web, go to **Apps → Find More Apps**
2. Search for **Meraki CIM Compliance Add-on**
3. Click **Install**
4. Restart Splunk if prompted

### Manual Installation
1. Download the `.tar.gz` package
2. Extract to `$SPLUNK_HOME/etc/apps/`:
   ```bash
   tar -xzf TA-meraki-cim-fix.tar.gz -C $SPLUNK_HOME/etc/apps/
   ```
3. Restart Splunk:
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

## Post-Installation Configuration

### 1. Verify CIM Index Macros
Ensure your Meraki index is included in the CIM index constraint macros. Go to **Settings → Advanced Search → Search macros** and verify that the following macros include your Meraki index (e.g., `OR index=meraki`):

- `cim_Intrusion_Detection_indexes`
- `cim_Network_Sessions_indexes`

### 2. Rebuild Data Model Accelerations
Go to **Settings → Data Models** and rebuild accelerations for:
- **Intrusion_Detection**
- **Network_Sessions**

### 3. Verify
After rebuilding, run these searches to confirm data is flowing into the data models:

```spl
| tstats count from datamodel=Intrusion_Detection where sourcetype="meraki:airmarshal" by sourcetype
```

```spl
| tstats count from datamodel=Network_Sessions where sourcetype="meraki:accesspoints" by sourcetype
```

## Field Mapping Details

### Air Marshal → Intrusion_Detection

| CIM Field | Source | Mapping Logic |
|---|---|---|
| `ids_type` | Static | Always `"wireless"` |
| `signature` | `ssid` | `"Rogue/Neighbor AP: <ssid>"` or `"Unknown Wireless Device"` |
| `category` | Static | Always `"wireless"` |
| `severity` | Static | Default `"medium"` |
| `action` | `bssids{}.contained` | `"blocked"` if contained, `"allowed"` otherwise |
| `src` | `bssids{}.bssid` | First detected BSSID |
| `dvc` | `bssids{}.detectedBy{}.device` | First detecting AP serial |

### Access Points → Network_Sessions

| CIM Field | Source | Mapping Logic |
|---|---|---|
| `dest` | `deviceName` | AP device name |
| `ssid` | `ssidName` | SSID name |
| `session_action` | `meraki_event_type` | `"allowed"` for association/roam, `"closed"` for disassociation |
| `duration` | `eventData.duration` | Session duration in seconds |

## Compatibility

- Tested with Cisco Meraki Add-on for Splunk v3.0.0 – v3.3.0
- Tested with Splunk Enterprise 9.2, 9.3
- Tested with CIM 4.x, 5.x, 6.x
- Compatible with Splunk Cloud Platform

## Removal

If a future version of the Cisco Meraki Add-on adds native CIM compliance for these sourcetypes, you can safely remove this add-on:

```bash
rm -rf $SPLUNK_HOME/etc/apps/TA-meraki-cim-fix
$SPLUNK_HOME/bin/splunk restart
```

## Support

For issues, questions, or feature requests, please open an issue on the Splunkbase app page.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

## Release Notes

### v1.0.0 (2026-04-22)
- Initial release
- Air Marshal CIM mapping for Intrusion_Detection data model
- Access Point session CIM mapping for Network_Sessions data model
