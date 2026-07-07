**About Us:**

CyberCX is the Australia’s greatest force of cyber security. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Unified Splunk Add-On for Barracuda looks to provide a single field extraction bundle for Barracuda Systems.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA avaliable for;

- Baracuda WAF

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Intrusion Detection and Web.

**Compatibility:**

| Splunk Enterprise versions | 10,9.4,9.3,9.2,9.1   |
| -------------------------- | -------------------- |
| CIM                        | 6.x, 5.x             |
| Platforms                  | Platform independent |
| Service Provider           | CyberCX              |
| Vendor Products            | Barracuda Systems    |

**Requirements:**
- This Add-on requires additional 'Barracuda Web Application Firewall CIM' version 1.0.11 (https://splunkbase.splunk.com/app/5592/) installed on a Heavy Forwarder to facilitate Barracuda WAF log ingestion.

**Installation:**
- The CCX Unified Splunk Add-on for Barracuda should be installed on Search Heads.
- Add-on Barracuda Web Application Firewall CIM version 1.0.11 (https://splunkbase.splunk.com/app/5592/) installed on a Heavy Forwarder.
- Edit eventtype "barracuda_waf" search to match assigned Barracuda indexes.

**Known issues:**
- (none)
