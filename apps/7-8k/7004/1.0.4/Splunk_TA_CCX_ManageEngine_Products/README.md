**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for ManageEngine Products looks to provide field extraction and CIM compliance for ManageEngine Products log sources captured via Syslog.

This Technical Add-on does not rely on any other Apps. Please use the link provided to configure Splunk forwarder to ingest the start ingesting ManageEngine logs:

https://www.manageengine.com/products/active-directory-audit/help/getting-started/siem-integration.html (sourcetype to be selected during ingestion: "ccx:adaudit:syslog")

Currently this add-on provides extraction and CIM compliance for products:  

- ADAudit Plus


Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, Endpoint, and Event Signatures.

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | ManageEngine |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads and on Splunk Forwarders where ManageEngine logs arriving.

**Installation**
- This Add-on is intended to be installed on Splunk Search Heads and on Splunk Forwarders where ManageEngine logs arriving.
- Main sourcetype: "ccx:adaudit:syslog"

**Known issues:**
- none
