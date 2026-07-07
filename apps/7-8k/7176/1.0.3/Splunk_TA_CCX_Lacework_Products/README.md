**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Lacework looks to provide a single field extraction bundle for Lacework logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA avaliable for:
- Lacework - HTTP Event Collector (JSON)

CIM field compliance, event types and tagging coverage for the following alert categories:
- Anomaly
- Policy
- Composite

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Intrusion Detection (IDS), and Network Traffic.

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Lacework |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads and also where HTTP Event Collector is configured.

**Installation:**

This Add-on is intended to be installed as follows:

- Splunk Cloud Victoria or Classic STACKs: Installed on Search Heads

- Splunk Enterprise: Installed on Search Heads and also where HTTP Event Collector is configured (HF)

Lacework - Configuring export logs to Splunk via HTTP Event Collector

https://docs.lacework.net/onboarding/splunk#:~:text=You%20can%20configure%20Lacework%20to,must%20set%20up%20port%20forwarding.

- Main default sourcetype to be selected as part of inputs configuration: "lacework:alerts"

- The eventtype "ccx_lacework_file_hash_tracking_malware_operations" is enabled for "malware and operations" tagging to track file_hashes as part of malware datamodels, however, tags can be disabled if datamodel Malware Operations not in use.


**Known issues:**
- (none)

