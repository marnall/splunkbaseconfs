**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Rapid7 Products Extensions looks to provide additional field extraction and CIM compliance for Rapid7 log sources captured via the Add-on Rapid7 InsightVM Technology Add-On for Splunk or Rapid7 Nexpose Technology Add-On for Splunk.

This Technical Add-on does not replace the public Splunk Add-on for Rapid7 InsightVM (https://splunkbase.splunk.com/app/5097) or Rapid7 Nexpose (https://splunkbase.splunk.com/app/3457) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance for sourcetypes:  

- rapid7:nexpose:vuln
- rapid7:insightvm:asset
- rapid7:insightvm:asset:vulnerability_finding
- rapid7:insightvm:vulnerability_definition


Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Inventory, and Vulnerabilities.

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Rapid7 |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed following the installation guidance.
- Install Add-on Rapid7 InsightVM Technology Add-On for Splunk (https://splunkbase.splunk.com/app/5097) version 1.5.1 or higher
- Install Add-on Rapid7 Nexpose Technology Add-On for Splunk (https://splunkbase.splunk.com/app/3457) version 1.4.2 or higher (on-prem Splunk Forwarder)

**Installation:**
This Add-on is intended to be installed as follows:
- Splunk Cloud Victoria or Classic STACKs: Installed on Search Heads
- Splunk Enterprise: Installed on Search Heads
- Update the macro ccx_rapid7_insightvm_index with respective index name
- Enable both searches "Search - Rapid7 CVE Multivalue - Lookup Gen" and "Search - Rapid7 Vulnerability ID - Lookup Gen" to populate vulnerability (log event enrich)

This Add-on is intended to be installed as a companion for the following add-ons:
- Install Add-on Rapid7 InsightVM Technology Add-On for Splunk (https://splunkbase.splunk.com/app/5097) version 1.5.1 or higher
- Install Add-on Rapid7 Nexpose Technology Add-On for Splunk (https://splunkbase.splunk.com/app/3457) version 1.4.2 or higher (on-prem Splunk Forwarder)

**Addressed Issues:**
- Fixes severity CIM values based on cvss3_score

**Known issues:**
- Disable tags for eventtype "Rapid7:InsightVM:Vulnerability_Definition"

