**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Extensions for Palo Alto Firewall Add-on looks to provide additional field extraction and CIM compliance for Palo Alto Firewall log sources parsed via the Add-on Palo Alto Networks Add-on for Splunk and Splunk Add-on for Palo Alto Networks.

This Technical Add-on does not replace the public Splunk Add-on for Palo Alto Networks Add-on for Splunk (https://classic.splunkbase.splunk.com/app/2757) or Splunk Add-on for Palo Alto Networks (https://splunkbase.splunk.com/app/7523) but works as an additional extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance for sourcetypes:  

- pan:globalprotect
- pan_globalprotect
- pan:iot_alert
- pan:iot_vulnerability
- pan:iot_device
- pan:firewall_cloud

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, Endpoint, Inventory, Intrusion Detection (IDS), Network Sessions, Network Traffic, and Vulnerabilities.

   
**Compatibility:** 
| Splunk Enterprise versions | 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Palo Alto |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Search Heads along with Splunk Add-on for Palo Alto Networks Add-on for Splunk (https://classic.splunkbase.splunk.com/app/2757) or Splunk Add-on for Palo Alto Networks (https://splunkbase.splunk.com/app/7523)

**Installation:**
- Splunk Cloud or Splunk Enterprise - Installed on Search Heads

This Add-on is intended to be installed as a companion for the following add-on:
- Install Palo Alto Networks Add-on for Splunk (https://classic.splunkbase.splunk.com/app/2757) or Splunk Add-on for Palo Alto Networks (https://splunkbase.splunk.com/app/7523)

**Known issues:**
- Disable tag authentication from eventtype "pan_globalprotect"
- Modify Field alias from sourcetype "pan:iot_alert"  iot_alert_user to "deviceid AS dvc_id"
- Modify Field user from sourcetype "pan:firewall_cloud"
