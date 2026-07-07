**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Extensions for NetDocuments Add-on looks to provide field extraction and CIM compliance for NetDocuments log sources captured via the NetDocuments Add-on for Splunk.

This Technical Add-on does not replace the public NetDocuments Add-on for Splunk (https://splunkbase.splunk.com/app/7197) but works as an additional extension to be deployed on Search Heads (only).

Currently this add-on provides field extraction and CIM compliance for sourcetypes:
- "netdocuments:repository:admin:logs"
- "netdocuments:repository:user:logs"

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Change, and Data Access.

**Compatibility:**

| Splunk Enterprise versions | 10.0, 9.4, 9.3, 9.2     |
| -------------------------- | ----------------------- |
| CIM                        | 6.x, 5.x                |
| Platforms                  | Platform independent    |
| Vendor Products            | NetDocuments            |
| Service Provider           | CyberCX                 |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads as an extension to NetDocuments Add-on for Splunk.

To install NetDocuments Add-on for Splunk follow the link:
https://splunkbase.splunk.com/app/7197

**Installation**

- This Add-on is intended to be installed on Splunk Search Heads as an extension to NetDocuments Add-on for Splunk.

**Known issues:**

- none
