
**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Netskope Extensions looks to provide additional field extraction and CIM compliance for Netskope log sources captured via the Add-on Netskope Add-on For Splunk.

This Technical Add-on does not replace the public Splunk Add-on for Netskope (https://splunkbase.splunk.com/app/3808/) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance for sourcetypes:  

- netskope:alert
- netskope:application
- netskope:connection
- netskope:incident
- netskope:audit
- netskope:cloud_exchange

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, Inventory, Data Loss Prevention (DLP), Malware, Network Traffic, Network Session, and Web.

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Netskope |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed following the installation guidance.
- Install Add-on Netskope Add-on For Splunk (https://splunkbase.splunk.com/app/3808/) version 4.2.0 or higher


**Installation**
This Add-on is intended to be installed as follows:
- Splunk Cloud Victoria STACKs: Installed on Search Head (it is replicated automatically on Premium ES stacks)
- Splunk Cloud Classic STACKs: Installed on Search Heads
- Splunk Enterprise: Installed on Search Heads

This Add-on is intended to be installed as a companion for the following add-on:
- Install Add-on Netskope Add-on For Splunk (https://splunkbase.splunk.com/app/3808/) version 4.2.0 or higher

Post steps installation to be performed:
- Update the default App eventtype "netskope_idx" with expected index (required)
- Update the default App sourcetype "netskope:application" fields: file_hash
- Update the default App sourcetype "netskope:alert" fields: file_hash and severity
- Update the default App sourcetype "netskope:audit" fields: action

- Update the default App eventtype search string: "netskope_cim_malware", "netskope_cim_alert", "netskope_cim_application", and "netskope_audit"
- Replace the tags for the eventtype "netskope_cim_alert" with the alert tag
- Remove all tags for the eventtype "netskope_cim_application"

**Known issues:**
- The CCX Add-on for Netskope Extensions if installed along deprecated Netskope Add-on For Splunk (https://splunkbase.splunk.com/app/3808/) may experience lower accuracy on CIM fields and tagging match, however, no compatibility issues detected.
- The macro "netskope_idx" if not updated no eventtype or tagging will be populated.
