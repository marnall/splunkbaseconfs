**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Keepit Products looks to provide a single field extraction bundle for Keepit Products.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Keepit logs ingested logs via HEC (JSON) using Keepit SIEM integration to Splunk following the link: https://help.keepit.com/support/solutions/articles/6000266324-set-up-a-siem-integration.

Currently, this add-on provides additional extraction and CIM compliance support for the following sourcetypes:

- jobs-monitor (ccx:keepit:jobs-monitor)
- audit-logs (ccx:keepit:audit-logs)

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, and Data Access.

   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Keepit |
| Service Provider | CyberCX |

**Requirements:**
- Set up Keepit SIEM integration fpr Spluhnk HEC use link below:
https://help.keepit.com/support/solutions/articles/6000266324-set-up-a-siem-integration

**Installation**
The CCX Add-on for Keepit Products should be installed on Search Heads and where HTTP Event Collector for Keepit is configured.

**Known issues:**
- (none)
