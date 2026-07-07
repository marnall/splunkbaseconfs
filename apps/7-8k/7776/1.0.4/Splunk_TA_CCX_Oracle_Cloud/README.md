**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Oracle Cloud looks to provide a single field extraction bundle for Oracle Cloud Audit and WAF (LB) logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Oracle Cloud ingested logs via Log Push HEC JSON format (Oracle documentation).

Supported main sourcetype:
- oracle:cloud

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Authentication, Change, Data Access, and Web.

**Compatibility:**

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2    |
| -------------------------- | -------------------- |
| CIM                        | 5.x 6.x              |
| Platforms                  | Platform independent |
| Vendor Products            | Oracle Cloud         |
| Service Provider           | CyberCX              |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads and Forwarders where HEC token is configured.
Main sourcetype - oracle:cloud

**Installation**
- This Add-on is intended to be installed on Splunk Search Heads and Forwarders where HEC token is configured.
Main sourcetype - oracle:cloud

**Known issues:**
- none

**Addressed Issues:**
- Calculated field "action" triggering unwanted non-CIM prescribed values.
