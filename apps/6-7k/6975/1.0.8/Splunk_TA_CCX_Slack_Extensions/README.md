
**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Extensions for Slack looks to provide a single field extraction bundle for Slack logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Slack.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Authentication, Change, Data Access, IDS, and Malware.

**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Slack |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads as an extension to where Slack Add-on for Splunk is installed.

To install Slack Add-on for Splunk follow the link:
https://splunkbase.splunk.com/app/4986

**Installation**
- This Add-on is intended to be installed on Splunk Search Heads as an extension to where Slack Add-on for Splunk is installed.

- Modify manually "Calculated Field": copy "Calculated Fields" "app", and "vendor_product" from CCX Extensions Add-on into the default configuration (Slack Add-on for Splunk)

**Known issues:**
- none