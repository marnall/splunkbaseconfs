**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Splunk Add-on for Auth0 looks to provide a single field extraction bundle for Auth0 logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA avaliable for:
- Auth0 - HTTP Event Collector (JSON)

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, and Intrusion Detection (IDS).

   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Auth0 |
| Service Provider | CyberCX |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads and also where HTTP Event Collector is configured.

**Installation:**

This Add-on is intended to be installed as follows:

- Splunk Cloud Victoria or Classic STACKs: Installed on Search Heads

- Splunk Enterprise: Installed on Search Heads and also where HTTP Event Collector is configured (HF)

Auth0 - Configuring export logs to Splunk via HTTP Event Collector

https://auth0.com/docs/customize/extensions/export-log-events-with-extensions/export-logs-to-splunk

- Main sourcetype to be selected as part of inputs configuration: "auth0"


**Known issues:**

- (none)

