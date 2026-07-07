**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Splunk Add-on for Keeper Security Products looks to provide a single field extraction bundle for Keeper Security logs ingested via HTTP Event Collector (HEC).

To configure Keeper Security to logpush to Splunk follow the link:
https://docs.keeper.io/enterprise-guide/event-reporting/splunk

Currently this add-on provides extraction and CIM compliance for Keeper Security products:

- Keeper Password Manager - "ccx:keeper:password_manager"


Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Authentication, Change, and DLP.

**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Keeper Security |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads and where HEC for Cloudflare is configured.


**Installation**
- This Add-on is intended to be installed on Splunk Search Heads and where HEC for Cloudflare is configured.


**Known issues:**
- none