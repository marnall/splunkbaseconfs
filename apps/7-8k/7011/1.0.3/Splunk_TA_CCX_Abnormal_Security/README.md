**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Splunk Add-on for Abnormal Security Email looks to provide a single field extraction bundle for Abnormal Security logs and does nont rely on any other Splunk Add-ons.
This TA was built using a large dataset and endeavours to be the first and most CIM compliant comprehensive field extraction TA avaliable for:
- Abnormal Security - HTTP Event Collector (JSON) - source abnormal-security

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, Email, and Intrusion Detection (IDS).

   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Abnormal Security |
| Service Provider | CyberCX |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads only.

**Installation:**

This Add-on is intended to be installed as follows:

- Splunk Cloud Victoria or Classic STACKs: Installed on Search Heads

- Splunk Enterprise: Installed on Search Heads

Abnormal Security - Configuring export logs to Splunk via HTTP Event Collector

- customers should request Abnormal for a pdf file "Splunk Integration Guide"

- No sourcetype selection required, however, Splunk Integration Guide suggests HTTP Event Collector "Source name override" to abnormal-security

- The macro "ccx_abnormal_security_index" should be updated with respective abornal-security index to enable eventtypes and tags.

