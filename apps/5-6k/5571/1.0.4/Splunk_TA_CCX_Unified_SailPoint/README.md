**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

CCX Security Operations has taken it upon ourselves to update and improve the existing SailPoint IdentityNow AuditEvent Add-on for Splunk as to ensure it is as CIM compliant as possible.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for SailPoint Audit Events.
The Technical Addon CCX Unified Add-On for SailPoint does not replace the public Splunk Add-on SailPoint IdentityNow AuditEvent Add-on (https://splunkbase.splunk.com/app/4088) but works to enhance CIM field value compliance and tagging, and it is be deployed on Search Heads (only).

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Change and Authentication.

   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | SailPoint |
| Service Provider | CyberCX |

**Requirements:**

- This Add-on is intended to be installed on Search Heads.
- Require Add-on "SailPoint IdentityNow AuditEvent Add-on" (https://splunkbase.splunk.com/app/4088/)

**Installation:**

Splunk Cloud Victoria
- This Add-On is intended to be installed together with Splunk Add-on "SailPoint IdentityNow AuditEvent Add-on" (https://splunkbase.splunk.com/app/4088/) that provides the log ingestion configuration inputs.

Splunk Cloud Classic and Enterprise
- This Add-on is intended to be installed on Search Heads and does not rely on any other Add-on to parse SailPoint logs.
- Require Add-on "SailPoint IdentityNow AuditEvent Add-on" (https://splunkbase.splunk.com/app/4088/) to be installed on Splunk Cloud IDM or Splunk Forwarder where the configuration inputs will be configured.
- Is recommended to use separate index.

**Release Notes:**
- Additional eventtype coverage
- Update lookups and definitions
 

**Known issues:**
- (none)
