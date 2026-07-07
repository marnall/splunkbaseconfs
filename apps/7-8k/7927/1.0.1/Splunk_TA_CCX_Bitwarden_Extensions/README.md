**About Us:**
CyberCX is Australia's greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Extensions for Bitwarden Add-on looks to provide field extraction and CIM compliance for Bitwarden log sources captured via the Add-on Bitwarden Event Logs.

This Technical Add-on does not replace the public Bitwarden Event Logs Add-on for Splunk (https://splunkbase.splunk.com/app/6592) but works as an additional extension to be deployed on Search Heads (only).

Currently this add-on provides field extraction and CIM compliance for sourcetypes "bitwarden:events".


Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Authentication, Change, Alert

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Bitwarden |
| Service Provider | CyberCX |

**Requirements:**
- Install Splunk Add-on "Bitwarden Event Logs" (https://splunkbase.splunk.com/app/6592) version 1.3.1 or higher where the API inputs is configured.

**Installation**
The Add-on "CCX Extensions for Bitwarden" is intended to be installed on Search Heads to facilitate CIM field compliance.


**Known issues:**
- none