**About Us:**
CyberCX is Australia's greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX McAfee Products Extensions looks to provide a single field extraction bundle for McAfee Products logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for McAfee Products.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

CCX McAfee Products Extensions currently supports the following products:

- McAfee EPO (mcafee:epo, mcafee:epo:syslog)
- McAfee MVISION Cloud (mcafee:mvisioncloud:syslog)

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Change, Data Loss Prevention (DLP), Intrusion Detection (IDS), Inventory, Malware, and Web.

**Compatibility:**

| Splunk Enterprise versions | 10,9.4,9.3,9.2,9.1   |
| -------------------------- | -------------------- |
| CIM                        | 6.x, 5.x             |
| Platforms                  | Platform independent |
| Vendor Products            | McAfee EPO Syslog    |
| Service Provider           | CyberCX              |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads as an extension to where McAfee EPO Syslog Add-on for Splunk is installed.

**Installation**

- This Add-on is intended to be installed on Splunk Search Heads as an extension to where McAfee EPO Syslog Add-on for Splunk is installed.
- McAfee link https://www.mcafee.com/enterprise/en-ca/products/mvision-cloud.html (McAfee MVISION Cloud (formerly known as Skyhigh Networks Cloud Security Platform))
- SIEM integration CEF format link - https://success.myshn.net/Skyhigh_CASB/Skyhigh_Cloud_Connector/Cloud_Connector_Integrations/Cloud_Connector_SIEM_Integration/Cloud_Connector_SIEM_Integration_Formats#CEF_Format

Fields to be replaced from McAfee EPO Syslog Add-on for Splunk with CCX McAfee Products Extensions fields:

- Field aliases: 'dest_ip', 'signature', 'vendor_product'
- Calculated fields: 'dest', 'file_hash', 'file_path', 'file_name', 'ids_type', 'src', 'user'

- **Release updates:**
  Additional support for HEC CIM field and value compliance, and eventtype coverage.

**Known issues:**

- none
