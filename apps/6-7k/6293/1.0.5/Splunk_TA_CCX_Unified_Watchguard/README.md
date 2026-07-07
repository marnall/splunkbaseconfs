**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Unified Splunk Add-on for Watchguard looks to provide a single field extraction bundle for Watchguard products.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Watchguard ingested logs via SYSLOG.

Below some of the listed products supported:  
- Firewall Firebox


Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Network Traffic, Network Sessions, Web, and Intrusion Detection (IDS).

   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Watchguard |
| Service Provider | CyberCX |

**Requirements:**

- This Add-On is intended to be installed on Heavy Forwarders and Search Heads.

**Installation**

- This Add-On is intended to be installed on Heavy Forwarders and Search Heads.
- Is recommended to use separate index.

**Known issues:**

- On Splunk Forwarder select the right "TIME_PREFIX" configuration to match timestamp capturing.

**Addressed Issues:**

- Additional coverage for https-proxy log events.
