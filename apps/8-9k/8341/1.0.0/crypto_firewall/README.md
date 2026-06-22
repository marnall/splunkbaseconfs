# Crypto Firewall for Splunk

Crypto Firewall for Splunk provides a CSV-based threat intelligence lookup containing known malicious cryptocurrency-related IP addresses.

The lookup can be used to enrich events, detect suspicious activity, and support investigations involving crypto scams, malware infrastructure, illicit mining, and command-and-control traffic.

## Contents

- CSV lookup file located in `default/data/lookups/`
- Fields:
  - `ip` – Malicious IP address
  - `message` – Detection description
  - `updated` – Last update timestamp (UTC)

## Installation

### Install from Splunkbase

1. Download the app package
2. In Splunk Web, go to **Apps → Manage Apps**
3. Click **Install app from file**
4. Upload the `.spl` package
5. Restart Splunk if prompted

## Using the Lookup

Example SPL:

```spl
index=network_logs
| lookup crypto_firewall ip AS src_ip OUTPUT message updated
| where isnotnull(message)
````

## Data Source

The threat intelligence data is maintained as part of the open-source Crypto Firewall project:

[https://github.com/chartingshow/crypto-firewall](https://github.com/chartingshow/crypto-firewall)

## Support

* Bug reports and feature requests:
  [https://github.com/chartingshow/crypto-firewall/issues](https://github.com/chartingshow/crypto-firewall/issues)

## License

This app is distributed under the Splunk End User License for Third Party Content.
