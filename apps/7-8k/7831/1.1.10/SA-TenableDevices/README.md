# SA-TenableDevices

A Splunk Supporting Add-on that populates Splunk Enterprise Security (ES) Asset & Identity framework with Tenable.io asset data.

## Overview

This add-on builds on [ZachTheSplunker's SA-CrowdstrikeDevices](https://github.com/ZachTheSplunker/SA-CrowdstrikeDevices) work, adapting the approach for Tenable.io assets. It provides the KVStore collections, lookups, and scheduled searches required to automatically populate ES Assets with your Tenable vulnerability management data.

## Requirements

- Splunk Enterprise Security 6.x or later
- [Tenable Add-on for Splunk](https://splunkbase.splunk.com/app/4060/) configured and ingesting `tenable:io:assets` data

## Installation

1. Install this add-on on your Splunk Search Head(s)
2. Update the `sa_tenable_index` macro to point to the index containing your Tenable data
3. (Optional) Customize the saved search priority logic for your environment

## Configuration

### Index Macro

Edit the macro in **Settings > Advanced Search > Search Macros** or modify `default/macros.conf`:

```ini
[sa_tenable_index]
definition = index=your_tenable_index
```

### Priority Customization

The default priority logic in the saved search uses:

| Priority | Criteria |
|----------|----------|
| Critical | Firewalls, Load Balancers |
| High | AWS EC2 instances, General-purpose systems |
| Medium | Everything else |

Modify the `priority=case(...)` statement in the saved search to match your environment's asset classification needs.

## What Gets Populated

The add-on extracts and normalizes the following asset fields for ES:

| Field | Source |
|-------|--------|
| `ip` | IPv4 addresses |
| `mac` | MAC addresses |
| `nt_host` | NetBIOS names |
| `dns` | FQDNs |
| `bunit` | Master Domain or Region |
| `priority` | Calculated from system type |
| `lat`, `long`, `city`, `country` | GeoIP lookup from IP |
| `category` | System types, scan timestamps, OS, agent status, AWS metadata |

## Scheduled Searches

| Search | Schedule | Description |
|--------|----------|-------------|
| Tenable Devices Lookup - Gen | Hourly (minute 19) | Populates `tenable_devices` KVStore collection |
| Tenable ES Devices Lookup - Gen | Triggered by above | Exports KVStore to `tenable_devices_es.csv` for ES compatibility |

## Important Notes

- **Every environment is different.** This add-on provides a starting point but may require customization for your specific asset data and classification requirements.
- The saved search runs hourly by default. Adjust the `cron_schedule` if needed.
- The search looks back 61 minutes to ensure no data gaps.

## Support

This is a community add-on provided as-is. Please open an issue on GitHub for bugs or feature requests.

## License

See [LICENSES/LICENSE.txt](LICENSES/LICENSE.txt)
