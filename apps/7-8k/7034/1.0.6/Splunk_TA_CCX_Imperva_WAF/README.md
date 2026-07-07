**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Imperva WAF looks to provide a single field extraction bundle for Imperva WAF logs ingested via syslog in CEF format.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Imperva WAF.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Intrusion Detection (IDS), Network Traffic, and Web.

**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Imperva WAF |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads and Splunk Forwarders for logs ingested via syslog.

**Installation:**
- This Add-on is intended to be installed on Splunk Search Heads and Splunk Forwarders for logs ingested via syslog.
- Input sourcetype: "imperva:waf"

**Addressed Issues:**
- Fix issues parsing CEF header fields
- Additional capture for kv pair extractions
- Address CEF cs/cn "Label" field value coverage
- Lookup updates
- Fix to eventtypes and tags


**Known issues:**
- This add-on should not be deployed toguether with any other Imperva Add-on on Search Heads.
