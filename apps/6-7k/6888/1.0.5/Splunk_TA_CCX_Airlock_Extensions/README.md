**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Extensions for Airlock Digital Add-on looks to provide field extraction and CIM compliance for Airlock Digital log sources captured via the Add-on Airlock Digital or via HTTP Event Collector (HEC).

This Technical Add-on does not replace the public Splunk Airlock Digital Add-On (https://splunkbase.splunk.com/app/5674) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides field extraction and CIM compliance for sourcetypes "airlock:svractivities" and "airlock:exechistories".


Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, and Endpoint.

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Airlock Digital |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed following the installation guidance.
- Install Splunk Add-on "Airlock Digital Add-On" (https://splunkbase.splunk.com/app/5674) version 5.3.6 or higher where the API inputs or HEC is configured.
- Or configure Airlog Digital log forwarding to Splunk HTPP Event Collector (HEC)

**Installation**
This Add-on is intended to be installed on Search Heads.

- Main sourcetype for HTTP Event Collector (HEC): "airlock:hec"

Post steps installation to be performed:
- Update the default App sourcetype "airlock:exechistories" fields: process_path, process, action

**Known issues:**
- none

**Addressed Issues**

- Additional and revised CIM fields src, src_ip, user_agent, and authentication_method.
